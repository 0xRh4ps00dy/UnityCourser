from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timezone
import shutil
import uuid
from pathlib import Path

UTC = timezone.utc


DEFAULT_LICENSE = "Creative Commons: Reconocimiento - compartir igual 4.0"
DEFAULT_LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"


ODE_DTD_CONTENT = """<!ELEMENT ode (userPreferences?, odeResources?, odeProperties?, odeNavStructures)>
<!ATTLIST ode
    xmlns CDATA #FIXED \"http://www.intef.es/xsd/ode\"
    version CDATA #IMPLIED>

<!ELEMENT userPreferences (userPreference*)>
<!ELEMENT userPreference (key, value)>

<!ELEMENT odeResources (odeResource*)>
<!ELEMENT odeResource (key, value)>

<!ELEMENT odeProperties (odeProperty*)>
<!ELEMENT odeProperty (key, value)>

<!ELEMENT key (#PCDATA)>
<!ELEMENT value (#PCDATA)>

<!ELEMENT odeNavStructures (odeNavStructure*)>
<!ELEMENT odeNavStructure (odePageId, odeParentPageId, pageName, odeNavStructureOrder, odeNavStructureProperties?, odePagStructures?)>

<!ELEMENT odePageId (#PCDATA)>
<!ELEMENT odeParentPageId (#PCDATA)>
<!ELEMENT pageName (#PCDATA)>
<!ELEMENT odeNavStructureOrder (#PCDATA)>

<!ELEMENT odeNavStructureProperties (odeNavStructureProperty*)>
<!ELEMENT odeNavStructureProperty (key, value)>

<!ELEMENT odePagStructures (odePagStructure*)>
<!ELEMENT odePagStructure (odePageId, odeBlockId, blockName, iconName?, odePagStructureOrder, odePagStructureProperties?, odeComponents?)>

<!ELEMENT odeBlockId (#PCDATA)>
<!ELEMENT blockName (#PCDATA)>
<!ELEMENT iconName (#PCDATA)>
<!ELEMENT odePagStructureOrder (#PCDATA)>

<!ELEMENT odePagStructureProperties (odePagStructureProperty*)>
<!ELEMENT odePagStructureProperty (key, value)>

<!ELEMENT odeComponents (odeComponent*)>
<!ELEMENT odeComponent (odePageId, odeBlockId, odeIdeviceId, odeIdeviceTypeName, htmlView?, jsonProperties?, odeComponentsOrder, odeComponentsProperties?)>

<!ELEMENT odeIdeviceId (#PCDATA)>
<!ELEMENT odeIdeviceTypeName (#PCDATA)>
<!ELEMENT htmlView (#PCDATA)>
<!ELEMENT jsonProperties (#PCDATA)>
<!ELEMENT odeComponentsOrder (#PCDATA)>

<!ELEMENT odeComponentsProperties (odeComponentsProperty*)>
<!ELEMENT odeComponentsProperty (key, value)>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera un paquete web estilo eXe a partir del manifest del curso."
    )
    parser.add_argument(
        "--manifest",
        default="downloads/unity_essentials/manifest.json",
        help="Ruta al manifest.json de UnityCourser.",
    )
    parser.add_argument(
        "--template-dir",
        default="",
        help="Directorio plantilla con estructura base de eXe (libs, theme, css).",
    )
    parser.add_argument(
        "--output-dir",
        default="exe_unity_web",
        help="Directorio destino del paquete web generado.",
    )
    parser.add_argument(
        "--copy-assets",
        action="store_true",
        help="Copia tambien downloads/unity_essentials/assets dentro del paquete.",
    )
    parser.add_argument(
        "--bold-mode",
        choices=["strip", "keep"],
        default="strip",
        help=(
            "Gestion de negritas en el contenido generado: "
            "strip (por defecto, elimina), keep (mantiene)."
        ),
    )
    parser.add_argument(
        "--keep-bold",
        action="store_const",
        const="keep",
        dest="bold_mode",
        help="Atajo para --bold-mode keep.",
    )
    parser.add_argument(
        "--strip-bold",
        action="store_const",
        const="strip",
        dest="bold_mode",
        help="Atajo para --bold-mode strip.",
    )
    return parser.parse_args()


def page_filename(index: int) -> str:
    return f"unidad-{index:02d}.html"


def exe_page_id(index: int) -> str:
    if index == 0:
        return str(uuid.uuid4())
    stamp = int(datetime.now(UTC).timestamp() * 1000) + index
    return f"page-{stamp}-{uuid.uuid4().hex[:9]}"


def ode_id(prefix: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"{stamp}{prefix}{suffix}"


def escape_cdata(text: str) -> str:
    return text.replace("]]>", "]]]]><![CDATA[>")


def text_idevice_html(inner_html: str) -> str:
    return (
        '<div class="exe-text-template"><div class="textIdeviceContent">'
        '<div class="exe-text-activity"><div><div class="exe-text">'
        + inner_html
        + '</div></div></div></div></div>'
    )


def text_idevice_props(idevice_id: str, inner_html: str) -> dict:
    return {
        "ideviceId": idevice_id,
        "textTextarea": inner_html,
        "textFeedbackInput": "",
        "textFeedbackTextarea": "",
        "textInfoDurationInput": "",
        "textInfoDurationTextInput": "Duracion",
        "textInfoParticipantsInput": "",
        "textInfoParticipantsTextInput": "Agrupamiento",
    }


def nav_html(items: list[dict], active_index: int) -> str:
    lines = ["<ul>"]
    current_mission = None

    for i, item in enumerate(items, start=1):
        mission = html.escape(item.get("mission", "Sin mision"))
        if mission != current_mission:
            if current_mission is not None:
                lines.append("</ul>")
                lines.append("</li>")
            lines.append(
                '<li class="mission-group">'
                f'<a href="#" class="mission-heading no-ch" onclick="return false;">{mission}</a>'
            )
            lines.append("<ul>")
            current_mission = mission

        file_name = page_filename(i)
        title = html.escape(item.get("title", f"Unidad {i}"))
        href = f"../html/{file_name}"
        if active_index == i:
            lines.append(f'<li class="active"> <a href="{href}" class="active no-ch">{title}</a>')
        else:
            lines.append(f'<li> <a href="{href}" class="no-ch">{title}</a>')
        lines.append("</li>")

    if current_mission is not None:
        lines.append("</ul>")
        lines.append("</li>")

    lines.append("</ul>")
    return "\n".join(lines)


def nav_html_for_index(items: list[dict]) -> str:
    lines = ["<ul>"]
    lines.append('<li class="active"> <a href="index.html" class="active main-node no-ch">Inicio</a>')
    lines.append("</li>")

    current_mission = None
    for i, item in enumerate(items, start=1):
        mission = html.escape(item.get("mission", "Sin mision"))
        if mission != current_mission:
            if current_mission is not None:
                lines.append("</ul>")
                lines.append("</li>")
            lines.append(
                '<li class="mission-group">'
                f'<a href="#" class="mission-heading no-ch" onclick="return false;">{mission}</a>'
            )
            lines.append("<ul>")
            current_mission = mission

        file_name = page_filename(i)
        title = html.escape(item.get("title", f"Unidad {i}"))
        lines.append(f'<li> <a href="html/{file_name}" class="no-ch">{title}</a>')
        lines.append("</li>")

    if current_mission is not None:
        lines.append("</ul>")
        lines.append("</li>")

    lines.append("</ul>")
    return "\n".join(lines)


def heading_level_from_style(style: str | None) -> int | None:
    if not style:
        return None

    normalized = style.strip().lower()
    if len(normalized) == 2 and normalized.startswith("h") and normalized[1].isdigit():
        level = int(normalized[1])
        if 1 <= level <= 6:
            return level
    return None


def build_index_sections(source_base: Path, total_items: int) -> str:
    return "\n".join(
        [
            '<section class="exe-text mb-4">',
            '<h2>Contenido importado</h2>',
            f'<p>Ruta base: {html.escape(str(source_base))}</p>',
            f'<p>Items totales: {total_items}</p>',
            '</section>',
        ]
    )


def absolutize_source_html_links(source_html: str) -> str:
    # Convert root-relative URLs from downloaded Unity Learn pages into absolute URLs.
    # This avoids file:///C:/_next/... resolution when loaded inside the package iframe.
    out = source_html
    for attr in ("href", "src", "poster", "action"):
        out = re.sub(rf'({attr}=["\"])\/(?!\/)', rf'\1https://learn.unity.com/', out)
    out = re.sub(r'url\((["\"]?)\/(?!\/)', r'url(\1https://learn.unity.com/', out)
    return out


def process_bold_markup(html_text: str, mode: str) -> str:
    # Control bold tags for translation quality.
    if mode == "keep":
        return html_text
    # Default: strip bold tags
    return re.sub(r"</?(?:strong|b)\b[^>]*>", "", html_text, flags=re.IGNORECASE)


def render_portable_children(children: list[dict], mark_defs: dict[str, dict]) -> str:
    rendered: list[str] = []
    for child in children:
        text = html.escape(child.get("text", ""))
        marks = child.get("marks", [])
        for mark in marks:
            if mark == "strong":
                text = f"<strong>{text}</strong>"
            elif mark == "em":
                text = f"<em>{text}</em>"
            elif mark == "underline":
                text = f"<u>{text}</u>"
            elif mark in mark_defs:
                href = mark_defs[mark].get("href", "")
                if href:
                    if mark_defs[mark].get("blank"):
                        text = f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{text}</a>'
                    else:
                        text = f'<a href="{html.escape(href)}" target="_self">{text}</a>'
        rendered.append(text)
    return "".join(rendered)


def extract_next_data_payload(source_html: str) -> dict | None:
    # More robust than regex for very large one-line HTML files.
    marker_index = source_html.find("__NEXT_DATA__")
    if marker_index < 0:
        return None

    script_start = source_html.rfind("<script", 0, marker_index)
    if script_start < 0:
        return None

    json_start = source_html.find(">", script_start)
    if json_start < 0:
        return None
    json_start += 1

    json_end = source_html.find("</script>", json_start)
    if json_end < 0:
        return None

    try:
        return json.loads(source_html[json_start:json_end])
    except json.JSONDecodeError:
        return None


def render_portable_blocks(blocks: list[dict]) -> list[str]:
    rendered: list[str] = []
    list_type: str | None = None

    for block in blocks:
        block_type = block.get("_type")

        if block_type == "block":
            mark_defs = {d.get("_key", ""): d for d in block.get("markDefs", [])}
            content = render_portable_children(block.get("children", []), mark_defs).strip()
            if not content:
                continue
            heading_level = heading_level_from_style(block.get("style"))

            block_list = block.get("listItem")
            if block_list == "bullet":
                if list_type != "ul":
                    if list_type == "ol":
                        rendered.append("</ol>")
                    rendered.append("<ul>")
                    list_type = "ul"
                rendered.append(f"<li>{content}</li>")
            elif block_list == "number":
                if list_type != "ol":
                    if list_type == "ul":
                        rendered.append("</ul>")
                    rendered.append("<ol>")
                    list_type = "ol"
                rendered.append(f"<li>{content}</li>")
            else:
                if list_type == "ul":
                    rendered.append("</ul>")
                    list_type = None
                elif list_type == "ol":
                    rendered.append("</ol>")
                    list_type = None
                if heading_level is not None:
                    rendered.append(f"<h{heading_level}>{content}</h{heading_level}>")
                else:
                    rendered.append(f"<p>{content}</p>")

        elif block_type == "learn-gcpImageBlock":
            if list_type == "ul":
                rendered.append("</ul>")
                list_type = None
            elif list_type == "ol":
                rendered.append("</ol>")
                list_type = None
            image_url = block.get("image", {}).get("url", "")
            alt_text = html.escape(block.get("altText", "Imagen"))
            if image_url:
                rendered.append(
                    '<div class="mb-3"><img src="'
                    + html.escape(image_url)
                    + '" alt="'
                    + alt_text
                    + '" style="max-width:100%;height:auto;border-radius:8px;" loading="lazy"></div>'
                )

        elif block_type == "learn-gcpVideoBlock":
            if list_type == "ul":
                rendered.append("</ul>")
                list_type = None
            elif list_type == "ol":
                rendered.append("</ol>")
                list_type = None
            video_url = block.get("overviewVideo", {}).get("url", "")
            if video_url:
                rendered.append(
                    '<p><a href="'
                    + html.escape(video_url)
                    + '" target="_blank" rel="noopener">Ver video del paso</a></p>'
                )

    if list_type == "ul":
        rendered.append("</ul>")
    elif list_type == "ol":
        rendered.append("</ol>")

    return rendered


def render_tutorial_sections(next_data: dict) -> str | None:
    tutorial = next_data.get("props", {}).get("pageProps", {}).get("tutorial", {})
    sections = tutorial.get("sections", [])

    if not sections:
        return None

    rendered_sections: list[str] = ['<div class="unity-embedded-content">']
    for sec_index, section in enumerate(sections, start=1):
        section_title = str(section.get("title", f"Seccion {sec_index}"))
        if section_title.strip().lower() == "instructions":
            continue

        sec_title = html.escape(section_title)
        rendered_sections.append(f'<section class="exe-text mb-4"><h2>{sec_index}. {sec_title}</h2>')

        rendered_sections.extend(render_portable_blocks(section.get("body", [])))

        rendered_sections.append("</section>")

    rendered_sections.append("</div>")
    return "\n".join(rendered_sections)


def render_quiz_sections(next_data: dict) -> str | None:
    quiz = next_data.get("props", {}).get("pageProps", {}).get("quiz", {})
    questions = quiz.get("questions", [])
    if not questions:
        return None

    rendered: list[str] = ['<div class="unity-embedded-content">']

    description = quiz.get("description", [])
    if description:
        rendered.append('<section class="exe-text mb-4"><h2>Descripcion del quiz</h2>')
        rendered.extend(render_portable_blocks(description))
        rendered.append("</section>")

    for q_index, question in enumerate(questions, start=1):
        rendered.append(f'<section class="exe-text mb-4"><h2>Pregunta {q_index}</h2>')
        rendered.extend(render_portable_blocks(question.get("title", [])))
        rendered.extend(render_portable_blocks(question.get("body", [])))

        options = question.get("options", [])
        if options:
            rendered.append("<ol>")
            for option in options:
                rendered.append("<li>")
                rendered.extend(render_portable_blocks(option.get("body", [])))
                rendered.append("</li>")
            rendered.append("</ol>")

        rendered.append("</section>")

    rendered.append("</div>")
    return "\n".join(rendered)


def render_ld_json_fallback(source_html: str) -> str | None:
    scripts: list[str] = []
    cursor = 0
    marker = '<script type="application/ld+json"'
    while True:
        start = source_html.find(marker, cursor)
        if start < 0:
            break
        start_data = source_html.find(">", start)
        if start_data < 0:
            break
        start_data += 1
        end_data = source_html.find("</script>", start_data)
        if end_data < 0:
            break
        scripts.append(source_html[start_data:end_data])
        cursor = end_data + 9

    for script_data in scripts:
        try:
            data = json.loads(script_data)
        except json.JSONDecodeError:
            continue

        content_type = str(data.get("contentType", "")).lower()
        name = html.escape(str(data.get("name", "Contenido")))
        description = html.escape(str(data.get("description", "")))
        content = data.get("content", [])

        if not description and not content:
            continue

        out: list[str] = ['<div class="unity-embedded-content">']
        out.append(f'<section class="exe-text mb-4"><h3>{name}</h3>')
        if description:
            out.append(f"<p>{description}</p>")

        if isinstance(content, list) and content:
            if content_type == "quiz":
                for i, q in enumerate(content, start=1):
                    q_name = q.get("name", "")
                    if isinstance(q_name, list):
                        q_name = " ".join(
                            str(x.get("text", "")) if isinstance(x, dict) else str(x) for x in q_name
                        )
                    q_name = html.escape(str(q_name))
                    if q_name:
                        out.append(f"<p><strong>Pregunta {i}:</strong> {q_name}</p>")
            else:
                out.append("<ol>")
                for i, entry in enumerate(content, start=1):
                    title = html.escape(str(entry.get("name", f"Paso {i}")))
                    out.append(f"<li>{title}</li>")
                out.append("</ol>")

        out.append("</section>")
        out.append("</div>")
        return "\n".join(out)

    return None


def render_tutorial_sections_from_source(source_html: str) -> str | None:
    next_data = extract_next_data_payload(source_html)
    if next_data:
        tutorial_html = render_tutorial_sections(next_data)
        if tutorial_html:
            return tutorial_html

        quiz_html = render_quiz_sections(next_data)
        if quiz_html:
            return quiz_html

    return render_ld_json_fallback(source_html)


def build_item_sections(item: dict, index: int, source_name: str | None, embedded_html: str | None = None) -> str:
    sections = []

    if embedded_html:
        sections.extend(
            [
                '<section class="exe-text mb-4">',
                embedded_html,
                '</section>',
            ]
        )

    return "\n".join(sections)


def page_template(
    *,
    package_title: str,
    package_subtitle: str,
    package_description: str,
    package_license: str,
    package_license_url: str,
    page_title: str,
    nav_block: str,
    content_html: str,
    prev_href: str | None,
    next_href: str | None,
    page_anchor: str,
    html_id: str,
    base_prefix: str,
) -> str:
    prev_button = (
        '<span class="nav-button nav-button-left" aria-hidden="true"><span>Anterior</span></span>'
        if prev_href is None
        else f'<a href="{prev_href}" title="Anterior" class="nav-button nav-button-left"><span>Anterior</span></a>'
    )
    next_button = (
        '<span class="nav-button nav-button-right" aria-hidden="true"><span>Siguiente</span></span>'
        if next_href is None
        else f'<a href="{next_href}" title="Siguiente" class="nav-button nav-button-right"><span>Siguiente</span></a>'
    )

    return f"""<!DOCTYPE html>
<html lang=\"en\" id=\"{html_id}\"> 
<head>
<meta charset=\"utf-8\">
<meta name=\"generator\" content=\"eXeLearning v4.0.0\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<link rel=\"license\" type=\"text/html\" href=\"{html.escape(package_license_url)}\"> 
<title>{html.escape(page_title)}</title>
<link rel=\"icon\" type=\"image/x-icon\" href=\"{base_prefix}libs/favicon.ico\">
<meta name=\"description\" content=\"{html.escape(package_description)}\"> 
<script>document.querySelector(\"html\").classList.add(\"js\");</script><script src=\"{base_prefix}libs/jquery/jquery.min.js\"> </script><script src=\"{base_prefix}libs/common_i18n.js\"> </script><script src=\"{base_prefix}libs/common.js\"> </script><script src=\"{base_prefix}libs/exe_export.js\"> </script><script src=\"{base_prefix}libs/bootstrap/bootstrap.bundle.min.js\"> </script><link rel=\"stylesheet\" href=\"{base_prefix}libs/bootstrap/bootstrap.min.css\">
<link rel=\"stylesheet\" href=\"{base_prefix}content/css/base.css\"><script src=\"{base_prefix}theme/style.js\"> </script><link rel=\"stylesheet\" href=\"{base_prefix}theme/style.css\">
</head>
<body class=\"exe-export exe-web-site\">
<script>document.body.className+=\" js\"</script>
<div class=\"exe-content exe-export pre-js siteNav-hidden\"><a href=\"#{page_anchor}\" id=\"skipNav\">Skip to content</a> <nav id=\"siteNav\">{nav_block}</nav><main id=\"{page_anchor}\" class=\"page\"> 
<header class=\"main-header\">
<div class=\"package-header\"><p class=\"package-title\">{html.escape(package_title)}</p>
<p class=\"package-subtitle\">{html.escape(package_subtitle)}</p></div>
<div class=\"page-header\"><h1 class=\"page-title\">{html.escape(page_title)}</h1></div> 
</header><div id=\"page-content-{page_anchor}\" class=\"page-content\">{content_html}</div></main><div class=\"nav-buttons\">{prev_button}{next_button}</div>
<footer id=\"siteFooter\"><div id=\"siteFooterContent\"> <div id=\"packageLicense\" class=\"cc cc-by-sa\"> <p> <span class=\"license-label\">Licencia: </span><a href=\"{html.escape(package_license_url)}\" class=\"license\">{html.escape(package_license)}</a></p>
</div>
</div></footer>
</div>
<p id=\"made-with-eXe\"> <a href=\"https://exelearning.net/\" target=\"_blank\" rel=\"noopener\"> <span>Creado con eXeLearning <span>(nueva ventana)</span></span></a></p>
</body>
</html>
"""


def build_content_xml(
    items: list[dict],
    embedded_sections: list[str | None],
    package_title: str,
    package_subtitle: str,
    package_description: str,
    package_author: str,
    package_license: str,
    package_license_url: str,
    item_page_ids: list[str],
    modified_ms: int,
    bold_mode: str,
) -> str:
    ode_project_id = ode_id("PRJ")
    ode_version_id = ode_id("VER")
    item_block_ids = [ode_id("BLK") for _ in items]
    item_component_ids = [ode_id("IDEV") for _ in items]
    mission_page_ids: dict[str, str] = {}
    mission_orders: dict[str, int] = {}
    mission_child_orders: dict[str, int] = {}

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE ode SYSTEM "content.dtd">',
        '<ode xmlns="http://www.intef.es/xsd/ode" version="2.0">',
        '<userPreferences>',
        '  <userPreference><key>theme</key><value>base</value></userPreference>',
        '</userPreferences>',
        '<odeResources>',
        f'  <odeResource><key>odeId</key><value>{ode_project_id}</value></odeResource>',
        f'  <odeResource><key>odeVersionId</key><value>{ode_version_id}</value></odeResource>',
        '  <odeResource><key>exe_version</key><value>4.0.0</value></odeResource>',
        '</odeResources>',
        '<odeProperties>',
        '  <odeProperty><key>pp_title</key><value>' + html.escape(package_title) + '</value></odeProperty>',
        '  <odeProperty><key>pp_subtitle</key><value>' + html.escape(package_subtitle) + '</value></odeProperty>',
        '  <odeProperty><key>pp_author</key><value>' + html.escape(package_author) + '</value></odeProperty>',
        '  <odeProperty><key>pp_description</key><value>' + html.escape(package_description) + '</value></odeProperty>',
        '  <odeProperty><key>pp_lang</key><value>en</value></odeProperty>',
        '  <odeProperty><key>pp_license</key><value>' + html.escape(package_license.lower()) + '</value></odeProperty>',
        '  <odeProperty><key>pp_licenseUrl</key><value>' + html.escape(package_license_url) + '</value></odeProperty>',
        '  <odeProperty><key>pp_theme</key><value>base</value></odeProperty>',
        '  <odeProperty><key>pp_exelearning_version</key><value>v4.0.0</value></odeProperty>',
        f'  <odeProperty><key>pp_modified</key><value>{modified_ms}</value></odeProperty>',
        '  <odeProperty><key>pp_addExeLink</key><value>true</value></odeProperty>',
        '  <odeProperty><key>pp_addPagination</key><value>false</value></odeProperty>',
        '  <odeProperty><key>pp_addSearchBox</key><value>false</value></odeProperty>',
        '  <odeProperty><key>pp_addAccessibilityToolbar</key><value>false</value></odeProperty>',
        '  <odeProperty><key>pp_addMathJax</key><value>false</value></odeProperty>',
        '  <odeProperty><key>exportSource</key><value>true</value></odeProperty>',
        '  <odeProperty><key>pp_globalFont</key><value>default</value></odeProperty>',
        '</odeProperties>',
        '<odeNavStructures>',
    ]

    for i, item in enumerate(items, start=1):
        page_id_value = item_page_ids[i - 1]
        block_id_value = item_block_ids[i - 1]
        component_id = item_component_ids[i - 1]
        source_name = f"source-{i:02d}.html"
        component_inner_html = build_item_sections(item, i, source_name, embedded_sections[i - 1])
        component_inner_html = process_bold_markup(component_inner_html, bold_mode)
        component_html = text_idevice_html(component_inner_html)
        json_props = text_idevice_props(component_id, component_inner_html)
        title = html.escape(item.get("title", f"Unidad {i}"))
        mission_raw = item.get("mission", "Sin mision")
        mission_title = html.escape(mission_raw)

        if mission_raw not in mission_page_ids:
            mission_page_ids[mission_raw] = ode_id("MNS")
            mission_orders[mission_raw] = len(mission_orders)
            mission_child_orders[mission_raw] = 0
            mission_page_id = mission_page_ids[mission_raw]
            mission_order = mission_orders[mission_raw]
            lines.extend(
                [
                    '  <odeNavStructure>',
                    f'    <odePageId>{mission_page_id}</odePageId>',
                    '    <odeParentPageId></odeParentPageId>',
                    f'    <pageName>{mission_title}</pageName>',
                    f'    <odeNavStructureOrder>{mission_order}</odeNavStructureOrder>',
                    '    <odeNavStructureProperties>',
                    f'      <odeNavStructureProperty><key>titlePage</key><value>{mission_title}</value></odeNavStructureProperty>',
                    '    </odeNavStructureProperties>',
                    '    <odePagStructures>',
                    '    </odePagStructures>',
                    '  </odeNavStructure>',
                ]
            )

        mission_page_id = mission_page_ids[mission_raw]
        mission_child_order = mission_child_orders[mission_raw]
        mission_child_orders[mission_raw] += 1

        lines.extend(
            [
                '  <odeNavStructure>',
                f'    <odePageId>{page_id_value}</odePageId>',
                f'    <odeParentPageId>{mission_page_id}</odeParentPageId>',
                f'    <pageName>{title}</pageName>',
                f'    <odeNavStructureOrder>{mission_child_order}</odeNavStructureOrder>',
                '    <odeNavStructureProperties>',
                f'      <odeNavStructureProperty><key>titlePage</key><value>{title}</value></odeNavStructureProperty>',
                '    </odeNavStructureProperties>',
                '    <odePagStructures>',
                '      <odePagStructure>',
                f'        <odePageId>{page_id_value}</odePageId>',
                f'        <odeBlockId>{block_id_value}</odeBlockId>',
                '        <blockName>Contenido</blockName>',
                '        <iconName></iconName>',
                '        <odePagStructureOrder>0</odePagStructureOrder>',
                '        <odePagStructureProperties>',
                '          <odePagStructureProperty><key>visibility</key><value>true</value></odePagStructureProperty>',
                '          <odePagStructureProperty><key>teacherOnly</key><value>false</value></odePagStructureProperty>',
                '          <odePagStructureProperty><key>allowToggle</key><value>true</value></odePagStructureProperty>',
                '          <odePagStructureProperty><key>minimized</key><value>false</value></odePagStructureProperty>',
                '        </odePagStructureProperties>',
                '        <odeComponents>',
                '          <odeComponent>',
                f'            <odePageId>{page_id_value}</odePageId>',
                f'            <odeBlockId>{block_id_value}</odeBlockId>',
                f'            <odeIdeviceId>{component_id}</odeIdeviceId>',
                '            <odeIdeviceTypeName>FreeTextIdevice</odeIdeviceTypeName>',
                f'            <htmlView><![CDATA[{escape_cdata(component_html)}]]></htmlView>',
                f'            <jsonProperties><![CDATA[{escape_cdata(json.dumps(json_props, ensure_ascii=False))}]]></jsonProperties>',
                '            <odeComponentsOrder>0</odeComponentsOrder>',
                '            <odeComponentsProperties>',
                '              <odeComponentsProperty><key>visibility</key><value>true</value></odeComponentsProperty>',
                '            </odeComponentsProperties>',
                '          </odeComponent>',
                '        </odeComponents>',
                '      </odePagStructure>',
                '    </odePagStructures>',
                '  </odeNavStructure>',
            ]
        )

    lines.extend(['</odeNavStructures>', '</ode>'])
    return "\n".join(lines)


def ensure_template(template_dir: Path) -> None:
    """Crea la estructura mínima de template si no existe."""
    
    # Crear directorio base si no existe
    template_dir.mkdir(parents=True, exist_ok=True)
    
    # libs/common.js
    (template_dir / "libs").mkdir(exist_ok=True)
    (template_dir / "libs" / "common.js").write_text(
        "// Common utilities\n(function() {\n  console.log('Common JS loaded');\n})();\n"
    )
    
    # libs/common_i18n.js
    (template_dir / "libs" / "common_i18n.js").write_text(
        "// Internationalization utilities\n(function() {\n  console.log('i18n JS loaded');\n})();\n"
    )
    
    # libs/exe_export.js
    (template_dir / "libs" / "exe_export.js").write_text(
        "// eXe export utilities\n(function() {\n  console.log('eXe export JS loaded');\n})();\n"
    )
    
    # libs/bootstrap (mínimo)
    (template_dir / "libs" / "bootstrap").mkdir(exist_ok=True)
    (template_dir / "libs" / "bootstrap" / ".gitkeep").write_text("")
    
    # libs/jquery (mínimo)
    (template_dir / "libs" / "jquery").mkdir(exist_ok=True)
    (template_dir / "libs" / "jquery" / ".gitkeep").write_text("")
    
    # theme/style.css
    (template_dir / "theme").mkdir(exist_ok=True)
    (template_dir / "theme" / "style.css").write_text(
        """/* eXe Theme Styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: Arial, sans-serif;
  line-height: 1.6;
  color: #333;
  background-color: #f5f5f5;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

header {
  background-color: #2c3e50;
  color: white;
  padding: 20px;
  margin-bottom: 20px;
}

main {
  background-color: white;
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h1, h2, h3, h4, h5, h6 {
  color: #2c3e50;
  margin-bottom: 10px;
}

p {
  margin-bottom: 15px;
}

nav ul {
  list-style: none;
}

nav ul li {
  padding: 8px 0;
}

nav ul li a {
  color: #3498db;
  text-decoration: none;
}

nav ul li a:hover {
  text-decoration: underline;
}
"""
    )
    
    # theme/style.js
    (template_dir / "theme" / "style.js").write_text(
        """// eXe Theme JavaScript
(function() {
  'use strict';
  
  document.addEventListener('DOMContentLoaded', function() {
    console.log('eXe theme loaded');
  });
})();
"""
    )
    
    # content/css/base.css
    (template_dir / "content" / "css").mkdir(parents=True, exist_ok=True)
    (template_dir / "content" / "css" / "base.css").write_text(
        """/* Base content styles */
.exe-text {
  margin-bottom: 20px;
}

.exe-section {
  margin-bottom: 20px;
  padding: 15px;
  border-left: 4px solid #3498db;
  background-color: #f9f9f9;
}

.exe-section h2 {
  margin-top: 0;
}

.exe-section p {
  margin-bottom: 10px;
}

strong {
  font-weight: bold;
}

em {
  font-style: italic;
}

u {
  text-decoration: underline;
}

.mb-4 {
  margin-bottom: 20px;
}
"""
    )
    
    # content/source_html (para archivos fuente)
    (template_dir / "content" / "source_html").mkdir(parents=True, exist_ok=True)
    (template_dir / "content" / "source_html" / ".gitkeep").write_text("")
    
    # html (para páginas generadas)
    (template_dir / "html").mkdir(parents=True, exist_ok=True)
    (template_dir / "html" / ".gitkeep").write_text("")


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()

    if args.template_dir:
        template_dir = Path(args.template_dir).resolve()
    else:
        candidates = [
            Path("exe_unity_web"),
            Path("test_web"),
        ]
        template_dir = None
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                template_dir = candidate.resolve()
                break
        
        # Si no existe ninguna, usar exe_unity_web y crearla después
        if template_dir is None:
            template_dir = Path("exe_unity_web").resolve()

    output_dir = Path(args.output_dir).resolve()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    items = data.get("items", [])
    metadata = data.get("metadata", {})

    package_title = metadata.get("Title", "Unity Course")
    package_subtitle = metadata.get("By", "Unity")
    package_author = metadata.get("By", package_subtitle)
    package_description = metadata.get("Description", package_title)
    package_license = metadata.get("License", DEFAULT_LICENSE)
    package_license_url = metadata.get("LicenseUrl", DEFAULT_LICENSE_URL)
    modified_ms = int(datetime.now(UTC).timestamp() * 1000)
    item_anchor_ids = [exe_page_id(i) for i in range(1, len(items) + 1)]

    # Si template_dir y output_dir son iguales (template auto-generada), 
    # generar estructura en output_dir
    if template_dir.resolve() == output_dir.resolve():
        # Template será generada in-place
        print(f"Template no encontrada. Creando estructura base en: {output_dir}")
        ensure_template(output_dir)
    else:
        # Copiar template existente a output
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(template_dir, output_dir)

    html_dir = output_dir / "html"
    content_source_dir = output_dir / "content" / "source_html"
    index_file = output_dir / "index.html"
    html_dir.mkdir(parents=True, exist_ok=True)
    content_source_dir.mkdir(parents=True, exist_ok=True)

    if index_file.exists():
        index_file.unlink()

    for existing in html_dir.glob("*.html"):
        existing.unlink()

    source_base = manifest_path.parent

    embedded_sections: list[str | None] = []

    for i, item in enumerate(items, start=1):
        title = item.get("title", f"Unidad {i}")
        output_file = item.get("output_file", "")
        embedded_html: str | None = None
        source_name: str | None = None

        if output_file:
            source_file = source_base / output_file
            if source_file.exists():
                source_text = source_file.read_text(encoding="utf-8", errors="ignore")
                embedded_html = render_tutorial_sections_from_source(source_text)
                if embedded_html:
                    embedded_html = process_bold_markup(embedded_html, args.bold_mode)
                source_text = absolutize_source_html_links(source_text)
                source_text = process_bold_markup(source_text, args.bold_mode)
                source_name = f"source-{i:02d}.html"
                (content_source_dir / source_name).write_text(source_text, encoding="utf-8")

        content_html = build_item_sections(item, i, source_name, embedded_html)
        content_html = process_bold_markup(content_html, args.bold_mode)

        prev_href = None if i == 1 else f"../html/{page_filename(i - 1)}"
        next_href = None if i == len(items) else f"../html/{page_filename(i + 1)}"

        page_html = page_template(
            package_title=package_title,
            package_subtitle=package_subtitle,
            package_description=package_description,
            package_license=package_license,
            package_license_url=package_license_url,
            page_title=title,
            nav_block=nav_html(items, active_index=i),
            content_html=content_html,
            prev_href=prev_href,
            next_href=next_href,
            page_anchor=item_anchor_ids[i - 1],
            html_id=f"exe-{item_anchor_ids[i - 1]}",
            base_prefix="../",
        )
        (html_dir / page_filename(i)).write_text(page_html, encoding="utf-8")
        embedded_sections.append(embedded_html)

    content_xml = build_content_xml(
        items=items,
        embedded_sections=embedded_sections,
        package_title=package_title,
        package_subtitle=package_subtitle,
        package_description=package_description,
        package_author=package_author,
        package_license=package_license,
        package_license_url=package_license_url,
        item_page_ids=item_anchor_ids,
        modified_ms=modified_ms,
        bold_mode=args.bold_mode,
    )
    (output_dir / "content.xml").write_text(content_xml, encoding="utf-8")
    (output_dir / "content.dtd").write_text(ODE_DTD_CONTENT, encoding="utf-8")

    if args.copy_assets:
        source_assets = source_base / "assets"
        target_assets = output_dir / "content" / "assets"
        if source_assets.exists():
            shutil.copytree(source_assets, target_assets, dirs_exist_ok=True)

    print(f"Paquete generado en: {output_dir}")
    print(f"Paginas creadas: {len(items)}")
    print(f"HTML fuente copiados: {len(list(content_source_dir.glob('*.html')))}")
    
    # Compress the output directory
    zip_path = output_dir.parent / f"{output_dir.name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(output_dir), 'zip', output_dir.parent, output_dir.name)
    print(f"Archivo comprimido: {zip_path}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
