from __future__ import annotations

import argparse
import html
import json
from datetime import UTC, datetime
import shutil
import uuid
from pathlib import Path


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
        default="test_web",
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
    if active_index == 0:
        lines.append('<li class="active"> <a href="../index.html" class="active main-node no-ch">Inicio</a>')
    else:
        lines.append('<li> <a href="../index.html" class="main-node no-ch">Inicio</a>')
    lines.append("</li>")

    for i, item in enumerate(items, start=1):
        file_name = page_filename(i)
        title = html.escape(item.get("title", f"Unidad {i}"))
        href = f"../html/{file_name}"
        if active_index == i:
            lines.append(f'<li class="active"> <a href="{href}" class="active no-ch">{title}</a>')
        else:
            lines.append(f'<li> <a href="{href}" class="no-ch">{title}</a>')
        lines.append("</li>")

    lines.append("</ul>")
    return "\n".join(lines)


def nav_html_for_index(items: list[dict]) -> str:
    lines = ["<ul>"]
    lines.append('<li class="active"> <a href="index.html" class="active main-node no-ch">Inicio</a>')
    lines.append("</li>")
    for i, item in enumerate(items, start=1):
        file_name = page_filename(i)
        title = html.escape(item.get("title", f"Unidad {i}"))
        lines.append(f'<li> <a href="html/{file_name}" class="no-ch">{title}</a>')
        lines.append("</li>")
    lines.append("</ul>")
    return "\n".join(lines)


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


def build_item_sections(item: dict, index: int, source_name: str) -> str:
    mission = item.get("mission", "")
    summary = item.get("summary", "")
    item_type = item.get("type", "")
    duration = item.get("duration", "")
    url = item.get("url", "")

    assets = item.get("assets", [])
    assets_count = len(assets)
    assets_ok = sum(1 for asset in assets if asset.get("status") in {"downloaded", "skipped", "present"})
    assets_fail = assets_count - assets_ok

    sections = [
        '<section class="exe-text mb-4">',
        f'<p><strong>Mision:</strong> {html.escape(mission)}</p>',
        f'<p><strong>Tipo:</strong> {html.escape(item_type)} | <strong>Duracion:</strong> {html.escape(duration)}</p>',
        f'<p>{html.escape(summary)}</p>',
        '</section>',
        '<section class="exe-text mb-4">',
        '<h2>Enlaces</h2>',
        f'<p><a href="{html.escape(url)}" target="_blank" rel="noopener">Abrir original en Unity Learn</a></p>',
        f'<p><a href="../content/source_html/{source_name}" target="_blank" rel="noopener">Abrir HTML descargado</a></p>',
        '</section>',
        '<section class="exe-text mb-4">',
        '<h2>Recursos detectados</h2>',
        f'<p>Total: {assets_count} | Disponibles: {assets_ok} | No descargados/fallidos: {assets_fail}</p>',
        '</section>',
    ]
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
<html lang=\"es\" id=\"{html_id}\"> 
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
    package_title: str,
    package_subtitle: str,
    package_description: str,
    package_author: str,
    package_license: str,
    package_license_url: str,
    index_page_id: str,
    item_page_ids: list[str],
    modified_ms: int,
    source_base: Path,
) -> str:
    ode_project_id = ode_id("PRJ")
    ode_version_id = ode_id("VER")
    index_block_id = ode_id("BLK")
    index_component_id = ode_id("IDEV")
    item_block_ids = [ode_id("BLK") for _ in items]
    item_component_ids = [ode_id("IDEV") for _ in items]

    index_inner_html = build_index_sections(source_base, len(items))
    index_html_view = text_idevice_html(index_inner_html)
    index_props = text_idevice_props(index_component_id, index_inner_html)

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
        '  <odeProperty><key>pp_lang</key><value>es</value></odeProperty>',
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
        '  <odeNavStructure>',
        f'    <odePageId>{index_page_id}</odePageId>',
        '    <odeParentPageId></odeParentPageId>',
        '    <pageName>Inicio</pageName>',
        '    <odeNavStructureOrder>0</odeNavStructureOrder>',
        '    <odeNavStructureProperties>',
        '      <odeNavStructureProperty><key>titlePage</key><value>Inicio</value></odeNavStructureProperty>',
        '    </odeNavStructureProperties>',
        '    <odePagStructures>',
        '      <odePagStructure>',
        f'        <odePageId>{index_page_id}</odePageId>',
        f'        <odeBlockId>{index_block_id}</odeBlockId>',
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
        f'            <odePageId>{index_page_id}</odePageId>',
        f'            <odeBlockId>{index_block_id}</odeBlockId>',
        f'            <odeIdeviceId>{index_component_id}</odeIdeviceId>',
        '            <odeIdeviceTypeName>FreeTextIdevice</odeIdeviceTypeName>',
        f'            <htmlView><![CDATA[{escape_cdata(index_html_view)}]]></htmlView>',
        f'            <jsonProperties><![CDATA[{escape_cdata(json.dumps(index_props, ensure_ascii=False))}]]></jsonProperties>',
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

    for i, item in enumerate(items, start=1):
        page_id_value = item_page_ids[i - 1]
        block_id_value = item_block_ids[i - 1]
        component_id = item_component_ids[i - 1]
        source_name = f"source-{i:02d}.html"
        component_inner_html = build_item_sections(item, i, source_name)
        component_html = text_idevice_html(component_inner_html)
        json_props = text_idevice_props(component_id, component_inner_html)
        title = html.escape(item.get("title", f"Unidad {i}"))
        lines.extend(
            [
                '  <odeNavStructure>',
                f'    <odePageId>{page_id_value}</odePageId>',
                '    <odeParentPageId></odeParentPageId>',
                f'    <pageName>{title}</pageName>',
                f'    <odeNavStructureOrder>{i}</odeNavStructureOrder>',
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


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    template_dir = Path(args.template_dir).resolve()
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
    index_anchor_id = exe_page_id(0)
    item_anchor_ids = [exe_page_id(i) for i in range(1, len(items) + 1)]

    if output_dir.exists():
        shutil.rmtree(output_dir)

    shutil.copytree(template_dir, output_dir)

    html_dir = output_dir / "html"
    content_source_dir = output_dir / "content" / "source_html"
    html_dir.mkdir(parents=True, exist_ok=True)
    content_source_dir.mkdir(parents=True, exist_ok=True)

    for existing in html_dir.glob("*.html"):
        existing.unlink()

    source_base = manifest_path.parent
    index_content = build_index_sections(source_base, len(items))
    index_html = page_template(
        package_title=package_title,
        package_subtitle=package_subtitle,
        package_description=package_description,
        package_license=package_license,
        package_license_url=package_license_url,
        page_title="Inicio",
        nav_block=nav_html_for_index(items),
        content_html=index_content,
        prev_href=None,
        next_href=(f"html/{page_filename(1)}" if items else None),
        page_anchor=index_anchor_id,
        html_id="exe-index",
        base_prefix="",
    )
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")

    for i, item in enumerate(items, start=1):
        title = item.get("title", f"Unidad {i}")
        output_file = item.get("output_file", "")
        source_name = f"source-{i:02d}.html"

        if output_file:
            source_file = source_base / output_file
            if source_file.exists():
                shutil.copy2(source_file, content_source_dir / source_name)

        content_html = build_item_sections(item, i, source_name)

        prev_href = "../index.html" if i == 1 else f"../html/{page_filename(i - 1)}"
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

    content_xml = build_content_xml(
        items=items,
        package_title=package_title,
        package_subtitle=package_subtitle,
        package_description=package_description,
        package_author=package_author,
        package_license=package_license,
        package_license_url=package_license_url,
        index_page_id=index_anchor_id,
        item_page_ids=item_anchor_ids,
        modified_ms=modified_ms,
        source_base=source_base,
    )
    (output_dir / "content.xml").write_text(content_xml, encoding="utf-8")
    (output_dir / "content.dtd").write_text(ODE_DTD_CONTENT, encoding="utf-8")

    if args.copy_assets:
        source_assets = source_base / "assets"
        target_assets = output_dir / "content" / "assets"
        if source_assets.exists():
            shutil.copytree(source_assets, target_assets, dirs_exist_ok=True)

    print(f"Paquete generado en: {output_dir}")
    print(f"Paginas creadas: {len(items) + 1}")
    print(f"HTML fuente copiados: {len(list(content_source_dir.glob('*.html')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
