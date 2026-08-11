from pathlib import Path

from .graph import build_target_ancestry
from .parser import parse_powercenter
from .rendering import render_model


def convert_powercenter(
    xml_path: str | Path,
    mapping_name: str,
    target_name: str,
) -> str:
    document = parse_powercenter(xml_path)
    ancestry = build_target_ancestry(document, mapping_name, target_name)

    return render_model(document, ancestry)


def write_model(
    xml_path: str | Path,
    mapping_name: str,
    target_name: str,
    output_path: str | Path,
) -> None:
    sql = convert_powercenter(xml_path, mapping_name, target_name)
    Path(output_path).write_text(sql + "\n", encoding="utf-8")
