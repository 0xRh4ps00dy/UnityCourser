from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UnityCourser/1.0"
TAG_URL_PATTERN = re.compile(r"(?:src|href|poster)=['\"]([^'\"]+)['\"]", re.IGNORECASE)
NEXT_DATA_PATTERN = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)
RAW_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
DOWNLOADABLE_EXTENSIONS = {
    ".avif",
    ".css",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".m4a",
    ".mp3",
    ".mp4",
    ".ogg",
    ".otf",
    ".pdf",
    ".png",
    ".srt",
    ".svg",
    ".ttf",
    ".txt",
    ".vtt",
    ".wav",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".xml",
}
SKIPPED_SCHEMES = ("mailto:", "javascript:", "tel:", "data:", "blob:")


@dataclass
class CourseItem:
    mission: str
    mission_slug: str
    title: str
    url: str
    item_type: str
    duration: str
    summary: str
    sequence: int
    output_file: str = ""
    status: str = "pending"
    error: str = ""
    http_status: int | None = None
    assets: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class CourseData:
    metadata: dict[str, str] = field(default_factory=dict)
    items: list[CourseItem] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Descarga las paginas HTML listadas en un CSV de Unity Learn."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default="UL_Unity_Essentials_6_0.csv",
        help="Ruta al CSV exportado con la estructura del curso.",
    )
    parser.add_argument(
        "--output-dir",
        default="downloads/unity_essentials",
        help="Directorio donde se guardaran las paginas y el manifiesto.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Numero maximo de paginas a descargar. 0 significa sin limite.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Pausa en segundos entre descargas.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout por peticion HTTP en segundos.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribe archivos HTML ya existentes.",
    )
    parser.add_argument(
        "--download-assets",
        action="store_true",
        help="Descarga recursos asociados, como imagenes, videos, subtitulos y assets estaticos.",
    )
    return parser.parse_args()


def slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "item"


def parse_course_csv(csv_path: Path) -> CourseData:
    course = CourseData()
    current_mission = "general"
    current_mission_slug = "general"
    item_sequence = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))

    mode = "metadata"
    for row in rows:
        if not any(cell.strip() for cell in row):
            continue

        first_cell = row[0].strip()

        if mode == "metadata":
            if first_cell == "Title" and len(row) > 1 and row[1].strip() == "URL":
                mode = "items"
                continue

            if len(row) >= 2:
                course.metadata[first_cell] = row[1].strip()
            continue

        padded = list(row) + [""] * (5 - len(row))
        title, url, item_type, duration, summary = (cell.strip() for cell in padded[:5])

        if not title:
            continue

        if not url and not item_type:
            current_mission = title
            current_mission_slug = slugify(title)
            continue

        item_sequence += 1
        course.items.append(
            CourseItem(
                mission=current_mission,
                mission_slug=current_mission_slug,
                title=title,
                url=url,
                item_type=item_type,
                duration=duration,
                summary=summary,
                sequence=item_sequence,
            )
        )

    return course


def fetch_html(url: str, timeout: int) -> tuple[int, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        charset = response.headers.get_content_charset() or "utf-8"
        content = response.read().decode(charset, errors="replace")
    return status, content


def fetch_bytes(url: str, timeout: int) -> tuple[int, bytes]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        content = response.read()
    return status, content


def build_output_path(base_dir: Path, item: CourseItem) -> Path:
    item_slug = slugify(item.title)
    filename = f"{item.sequence:02d}-{item_slug}.html"
    return base_dir / item.mission_slug / filename


def build_asset_path(base_dir: Path, asset_url: str) -> Path:
    parsed = urlparse(asset_url)
    host = slugify(parsed.netloc) or "asset-host"
    relative_path = parsed.path.lstrip("/")
    if not relative_path or relative_path.endswith("/"):
        relative_path = f"{relative_path}index"
    safe_parts = [part for part in relative_path.split("/") if part not in {"", ".", ".."}]
    return base_dir / "assets" / host / Path(*safe_parts)


def looks_like_downloadable_asset(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False

    path = parsed.path.lower()
    if any(path.endswith(extension) for extension in DOWNLOADABLE_EXTENSIONS):
        return True

    return path.startswith("/_next/static/")


def collect_urls_from_json(value: Any, found_urls: set[str]) -> None:
    if isinstance(value, dict):
        for nested_value in value.values():
            collect_urls_from_json(nested_value, found_urls)
        return

    if isinstance(value, list):
        for nested_value in value:
            collect_urls_from_json(nested_value, found_urls)
        return

    if isinstance(value, str):
        for match in RAW_URL_PATTERN.findall(value):
            found_urls.add(match)


def extract_asset_urls(html: str, page_url: str) -> list[str]:
    found_urls: set[str] = set()

    for candidate in TAG_URL_PATTERN.findall(html):
        if candidate.startswith(SKIPPED_SCHEMES):
            continue
        found_urls.add(urljoin(page_url, candidate))

    next_data_match = NEXT_DATA_PATTERN.search(html)
    if next_data_match:
        try:
            next_data = json.loads(next_data_match.group(1))
            collect_urls_from_json(next_data, found_urls)
        except json.JSONDecodeError:
            pass

    for candidate in RAW_URL_PATTERN.findall(html):
        found_urls.add(candidate)

    filtered_urls = sorted(
        url
        for url in found_urls
        if looks_like_downloadable_asset(url)
    )
    return filtered_urls


def download_assets_for_item(item: CourseItem, html: str, page_url: str, output_dir: Path, timeout: int) -> dict[str, int]:
    counters = {"assets_downloaded": 0, "assets_skipped": 0, "assets_failed": 0}
    item.assets = []

    for asset_url in extract_asset_urls(html, page_url):
        asset_target = build_asset_path(output_dir, asset_url)
        asset_target.parent.mkdir(parents=True, exist_ok=True)

        asset_info: dict[str, Any] = {
            "url": asset_url,
            "local_file": str(asset_target.relative_to(output_dir)),
            "status": "pending",
            "http_status": None,
            "error": "",
        }

        if asset_target.exists():
            asset_info["status"] = "skipped"
            counters["assets_skipped"] += 1
            item.assets.append(asset_info)
            continue

        try:
            status, content = fetch_bytes(asset_url, timeout=timeout)
            asset_target.write_bytes(content)
            asset_info["status"] = "downloaded"
            asset_info["http_status"] = status
            counters["assets_downloaded"] += 1
        except HTTPError as exc:
            asset_info["status"] = "failed"
            asset_info["http_status"] = exc.code
            asset_info["error"] = f"HTTP {exc.code}: {exc.reason}"
            counters["assets_failed"] += 1
        except URLError as exc:
            asset_info["status"] = "failed"
            asset_info["error"] = str(exc.reason)
            counters["assets_failed"] += 1
        except Exception as exc:  # noqa: BLE001
            asset_info["status"] = "failed"
            asset_info["error"] = str(exc)
            counters["assets_failed"] += 1

        item.assets.append(asset_info)

    return counters


def write_manifest(output_dir: Path, course: CourseData) -> None:
    manifest = {
        "metadata": course.metadata,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "items": [
            {
                "sequence": item.sequence,
                "mission": item.mission,
                "title": item.title,
                "url": item.url,
                "type": item.item_type,
                "duration": item.duration,
                "summary": item.summary,
                "output_file": item.output_file,
                "status": item.status,
                "http_status": item.http_status,
                "error": item.error,
                "assets": item.assets,
            }
            for item in course.items
        ],
    }

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def download_course(
    course: CourseData,
    output_dir: Path,
    timeout: int,
    delay: float,
    overwrite: bool,
    limit: int,
    download_assets: bool,
) -> dict[str, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    counters = {
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "assets_downloaded": 0,
        "assets_skipped": 0,
        "assets_failed": 0,
    }

    items = course.items[:limit] if limit > 0 else course.items
    for index, item in enumerate(items, start=1):
        target_path = build_output_path(output_dir, item)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        item.output_file = str(target_path.relative_to(output_dir))
        html = ""

        if target_path.exists() and not overwrite:
            item.status = "skipped"
            counters["skipped"] += 1
            print(f"[{index}/{len(items)}] skip {item.title}")
            html = target_path.read_text(encoding="utf-8", errors="replace")

        else:
            try:
                status, html = fetch_html(item.url, timeout=timeout)
                target_path.write_text(html, encoding="utf-8")
                item.status = "downloaded"
                item.http_status = status
                counters["downloaded"] += 1
                print(f"[{index}/{len(items)}] ok   {item.title}")
            except HTTPError as exc:
                item.status = "failed"
                item.http_status = exc.code
                item.error = f"HTTP {exc.code}: {exc.reason}"
                counters["failed"] += 1
                print(f"[{index}/{len(items)}] fail {item.title} -> {item.error}", file=sys.stderr)
            except URLError as exc:
                item.status = "failed"
                item.error = str(exc.reason)
                counters["failed"] += 1
                print(f"[{index}/{len(items)}] fail {item.title} -> {item.error}", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001
                item.status = "failed"
                item.error = str(exc)
                counters["failed"] += 1
                print(f"[{index}/{len(items)}] fail {item.title} -> {item.error}", file=sys.stderr)

        if html and item.status != "failed" and download_assets:
            asset_counters = download_assets_for_item(
                item=item,
                html=html,
                page_url=item.url,
                output_dir=output_dir,
                timeout=timeout,
            )
            counters["assets_downloaded"] += asset_counters["assets_downloaded"]
            counters["assets_skipped"] += asset_counters["assets_skipped"]
            counters["assets_failed"] += asset_counters["assets_failed"]
            print(
                f"         assets ok={asset_counters['assets_downloaded']} "
                f"skip={asset_counters['assets_skipped']} fail={asset_counters['assets_failed']}"
            )

        # Persistimos progreso en cada item para poder reanudar sin perder estado.
        write_manifest(output_dir, course)

        if delay > 0 and index < len(items):
            time.sleep(delay)

    for item in course.items[len(items):]:
        item.status = "not-requested"

    write_manifest(output_dir, course)
    return counters


def main() -> int:
    args = parse_args()
    csv_path = Path(args.csv_path).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not csv_path.exists():
        print(f"No existe el CSV: {csv_path}", file=sys.stderr)
        return 1

    course = parse_course_csv(csv_path)
    if not course.items:
        print("No se encontraron items descargables en el CSV.", file=sys.stderr)
        return 1

    counters = download_course(
        course=course,
        output_dir=output_dir,
        timeout=args.timeout,
        delay=args.delay,
        overwrite=args.overwrite,
        limit=args.limit,
        download_assets=args.download_assets,
    )

    print()
    print(f"Curso: {course.metadata.get('Title', 'Sin titulo')}")
    print(f"Items totales en CSV: {len(course.items)}")
    print(f"Descargados: {counters['downloaded']}")
    print(f"Omitidos: {counters['skipped']}")
    print(f"Fallidos: {counters['failed']}")
    if args.download_assets:
        print(f"Recursos descargados: {counters['assets_downloaded']}")
        print(f"Recursos omitidos: {counters['assets_skipped']}")
        print(f"Recursos fallidos: {counters['assets_failed']}")
    print(f"Salida: {output_dir}")
    return 0 if counters["failed"] == 0 and counters["assets_failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())