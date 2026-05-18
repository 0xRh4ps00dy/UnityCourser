from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse


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


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "asset-host"


def looks_like_downloadable_asset(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False

    path = parsed.path.lower()
    if any(path.endswith(extension) for extension in DOWNLOADABLE_EXTENSIONS):
        return True

    return path.startswith("/_next/static/")


def collect_urls_from_json(value: object, found_urls: set[str]) -> None:
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

    return sorted(url for url in found_urls if looks_like_downloadable_asset(url))


def build_asset_relpath(asset_url: str) -> str:
    parsed = urlparse(asset_url)
    host = slugify(parsed.netloc)
    relative_path = parsed.path.lstrip("/")
    if not relative_path or relative_path.endswith("/"):
        relative_path = f"{relative_path}index"
    safe_parts = [part for part in relative_path.split("/") if part not in {"", ".", ".."}]
    return str(Path("assets") / host / Path(*safe_parts))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresca el bloque assets de manifest.json usando solo archivos ya descargados."
    )
    parser.add_argument(
        "--manifest",
        default="downloads/unity_essentials/manifest.json",
        help="Ruta al manifest.json.",
    )
    parser.add_argument(
        "--base-dir",
        default="downloads/unity_essentials",
        help="Carpeta base donde estan los html y assets.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    base_dir = Path(args.base_dir).resolve()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = data.get("items", [])

    items_with_assets = 0
    total_assets = 0
    missing_assets = 0

    for item in items:
        output_file = item.get("output_file", "")
        page_url = item.get("url", "")
        if not output_file or not page_url:
            item["assets"] = []
            continue

        html_path = base_dir / output_file
        if not html_path.exists():
            item["assets"] = []
            continue

        html = html_path.read_text(encoding="utf-8", errors="replace")
        asset_urls = extract_asset_urls(html, page_url)
        assets = []

        for asset_url in asset_urls:
            relpath = build_asset_relpath(asset_url)
            local_path = base_dir / relpath
            exists = local_path.exists()
            if not exists:
                missing_assets += 1

            assets.append(
                {
                    "url": asset_url,
                    "local_file": relpath.replace("/", "\\"),
                    "status": "present" if exists else "missing",
                    "http_status": None,
                    "error": "" if exists else "Not found on disk",
                }
            )

        item["assets"] = assets
        if assets:
            items_with_assets += 1
            total_assets += len(assets)

    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Items totales: {len(items)}")
    print(f"Items con assets: {items_with_assets}")
    print(f"Assets totales referenciados: {total_assets}")
    print(f"Assets faltantes en disco: {missing_assets}")
    print(f"Manifest actualizado: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
