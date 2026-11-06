from pathlib import Path
import html
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
OUT_DIR.mkdir(exist_ok=True)

DRAWIO_PATH = OUT_DIR / "anti_fraud_media_reasoning_system.drawio"

PAGE_W = 1536
PAGE_H = 1024


def style(parts):
    return ";".join(f"{k}={v}" for k, v in parts.items() if v is not None) + ";"


def add_vertex(root, cell_id, value, x, y, w, h, cell_style):
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": cell_id,
            "value": value,
            "style": cell_style,
            "vertex": "1",
            "parent": "1",
        },
    )
    ET.SubElement(
        cell,
        "mxGeometry",
        {
            "x": str(x),
            "y": str(y),
            "width": str(w),
            "height": str(h),
            "as": "geometry",
        },
    )
    return cell


def add_text(root, cell_id, value, x, y, w, h, size=14, bold=False, align="center"):
    return add_vertex(
        root,
        cell_id,
        value,
        x,
        y,
        w,
        h,
        style(
            {
                "text": "",
                "html": "1",
                "strokeColor": "none",
                "fillColor": "none",
                "align": align,
                "verticalAlign": "middle",
                "whiteSpace": "wrap",
                "rounded": "0",
                "fontFamily": "Arial",
                "fontSize": str(size),
                "fontStyle": "1" if bold else "0",
                "fontColor": "#000000",
            }
        ),
    )


def rect_style(fill="#ffffff", stroke="#000000", gradient=None, dashed=False, rounded=True, width=1, font_size=13):
    return style(
        {
            "rounded": "1" if rounded else "0",
            "whiteSpace": "wrap",
            "html": "1",
            "arcSize": "8",
            "fillColor": fill,
            "gradientColor": gradient,
            "gradientDirection": "south" if gradient else None,
            "strokeColor": stroke,
            "strokeWidth": str(width),
            "dashed": "1" if dashed else None,
            "dashPattern": "8 4" if dashed else None,
            "fontFamily": "Arial",
            "fontSize": str(font_size),
            "fontColor": "#000000",
            "shadow": "0",
        }
    )


def add_rect(root, cell_id, value, x, y, w, h, fill="#ffffff", stroke="#000000", gradient=None, dashed=False, rounded=True, width=1, font_size=13):
    return add_vertex(root, cell_id, value, x, y, w, h, rect_style(fill, stroke, gradient, dashed, rounded, width, font_size))


def add_icon(root, cell_id, value, x, y, w, h, size=28):
    return add_text(root, cell_id, value, x, y, w, h, size=size, bold=False)


def label_value(title, subtitle=None, title_size=13, subtitle_size=11):
    if subtitle:
        return (
            f"<div><b>{html.escape(title)}</b></div>"
            f"<div><span style=\"font-size:{subtitle_size}px\">{html.escape(subtitle)}</span></div>"
        )
    return f"<b>{html.escape(title)}</b>"


def add_card(root, cell_id, x, y, w, h, fill, gradient, icon, title, subtitle=None, dashed=False, title_size=13, icon_size=30):
    add_rect(root, f"{cell_id}_box", "", x, y, w, h, fill=fill, gradient=gradient, dashed=dashed)
    add_icon(root, f"{cell_id}_icon", icon, x + 6, y + 12, 42, h - 24, size=icon_size)
    add_text(
        root,
        f"{cell_id}_label",
        label_value(title, subtitle, title_size=title_size),
        x + 50,
        y + 7,
        w - 56,
        h - 14,
        size=title_size,
        bold=False,
    )


def add_small_card(root, cell_id, x, y, w, h, fill, gradient, icon, title, subtitle=None, dashed=False, icon_size=28):
    add_rect(root, f"{cell_id}_box", "", x, y, w, h, fill=fill, gradient=gradient, dashed=dashed)
    add_icon(root, f"{cell_id}_icon", icon, x + 8, y + 11, 38, h - 22, size=icon_size)
    add_text(
        root,
        f"{cell_id}_label",
        label_value(title, subtitle, title_size=13, subtitle_size=10),
        x + 50,
        y + 7,
        w - 58,
        h - 14,
        size=12,
    )


def add_edge(root, cell_id, source, target, stroke="#000000", width=2):
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": cell_id,
            "value": "",
            "style": style(
                {
                    "edgeStyle": "orthogonalEdgeStyle",
                    "rounded": "0",
                    "orthogonalLoop": "1",
                    "jettySize": "auto",
                    "html": "1",
                    "endArrow": "block",
                    "endFill": "1",
                    "strokeColor": stroke,
                    "strokeWidth": str(width),
                }
            ),
            "edge": "1",
            "parent": "1",
            "source": source,
            "target": target,
        },
    )
    ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    return cell


def add_point_edge(root, cell_id, x1, y1, x2, y2, stroke="#000000", width=2):
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": cell_id,
            "value": "",
            "style": style(
                {
                    "edgeStyle": "orthogonalEdgeStyle",
                    "rounded": "0",
                    "orthogonalLoop": "1",
                    "jettySize": "auto",
                    "html": "1",
                    "endArrow": "block",
                    "endFill": "1",
                    "strokeColor": stroke,
                    "strokeWidth": str(width),
                }
            ),
            "edge": "1",
            "parent": "1",
        },
    )
    geom = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    ET.SubElement(geom, "mxPoint", {"x": str(x1), "y": str(y1), "as": "sourcePoint"})
    ET.SubElement(geom, "mxPoint", {"x": str(x2), "y": str(y2), "as": "targetPoint"})
    return cell


def add_poly_edge(root, cell_id, points, stroke="#000000", width=2, end_arrow=True):
    if len(points) < 2:
        raise ValueError("A polyline edge needs at least two points.")

    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": cell_id,
            "value": "",
            "style": style(
                {
                    "edgeStyle": "orthogonalEdgeStyle",
                    "rounded": "0",
                    "orthogonalLoop": "0",
                    "jettySize": "auto",
                    "html": "1",
                    "endArrow": "block" if end_arrow else "none",
                    "endFill": "1" if end_arrow else "0",
                    "strokeColor": stroke,
                    "strokeWidth": str(width),
                }
            ),
            "edge": "1",
            "parent": "1",
        },
    )
    geom = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    ET.SubElement(geom, "mxPoint", {"x": str(points[0][0]), "y": str(points[0][1]), "as": "sourcePoint"})
    ET.SubElement(geom, "mxPoint", {"x": str(points[-1][0]), "y": str(points[-1][1]), "as": "targetPoint"})
    if len(points) > 2:
        waypoints = ET.SubElement(geom, "Array", {"as": "points"})
        for x, y in points[1:-1]:
            ET.SubElement(waypoints, "mxPoint", {"x": str(x), "y": str(y)})
    return cell


def add_line(root, cell_id, x1, y1, x2, y2, stroke="#000000", width=1, dashed=False):
    cell = ET.SubElement(
        root,
        "mxCell",
        {
            "id": cell_id,
            "value": "",
            "style": style(
                {
                    "edgeStyle": "orthogonalEdgeStyle",
                    "rounded": "0",
                    "orthogonalLoop": "1",
                    "jettySize": "auto",
                    "html": "1",
                    "endArrow": "none",
                    "strokeColor": stroke,
                    "strokeWidth": str(width),
                    "dashed": "1" if dashed else None,
                    "dashPattern": "8 4" if dashed else None,
                }
            ),
            "edge": "1",
            "parent": "1",
        },
    )
    geom = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    ET.SubElement(geom, "mxPoint", {"x": str(x1), "y": str(y1), "as": "sourcePoint"})
    ET.SubElement(geom, "mxPoint", {"x": str(x2), "y": str(y2), "as": "targetPoint"})
    return cell


def main():
    mxfile = ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "modified": "2026-06-15T00:00:00.000Z",
            "agent": "Codex",
            "version": "30.0.4",
            "type": "device",
        },
    )
    diagram = ET.SubElement(mxfile, "diagram", {"id": "anti-fraud-media-reasoning", "name": "Page-1"})
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        {
            "dx": "1536",
            "dy": "1024",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": str(PAGE_W),
            "pageHeight": str(PAGE_H),
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    # White page background keeps exported PNG dimensions predictable.
    add_rect(root, "page_background", "", 0, 0, PAGE_W, PAGE_H, fill="#ffffff", stroke="none", rounded=False)

    add_text(
        root,
        "title",
        "Technical Logic Flow Diagram of Anti-Fraud Media Reasoning System",
        230,
        16,
        1080,
        50,
        size=32,
        bold=True,
    )

    # Section headings.
    headings = [
        ("h1", "1) Media Input", 18, 124, 126, 30),
        ("h2", "2) Text Preprocessing", 174, 124, 140, 30),
        ("h3", "3) Risk Feature<br>Extraction", 374, 116, 110, 48),
        ("h4", "4) Hybrid Evidence Retrieval", 650, 124, 250, 30),
        ("h6", "6) BGE-<br>Reranker-v2-m3", 972, 120, 120, 45),
        ("h7", "7) Prompt<br>Construction", 1124, 120, 105, 45),
        ("h8", "8) Qwen LLM<br>Reasoning", 1261, 111, 110, 56),
        ("h9", "9) Structured<br>Anti-Fraud<br>Output", 1414, 107, 112, 66),
    ]
    for hid, text, x, y, w, h in headings:
        add_text(root, hid, text, x, y, w, h, size=16, bold=True)

    # Outer containers.
    add_rect(root, "media_group", "", 9, 178, 134, 592, fill="#ffffff", stroke="#000000")
    add_rect(root, "preprocess_group", "", 178, 261, 128, 494, fill="#ffffff", stroke="#000000")
    add_rect(root, "risk_group", "", 339, 178, 165, 682, fill="#ffffff", stroke="#000000")
    add_rect(root, "hybrid_group", "", 563, 178, 385, 712, fill="none", stroke="#4b00a8", width=1.5)
    add_rect(root, "retrieval_inner", "", 599, 201, 335, 435, fill="none", stroke="#333333", dashed=True)
    add_rect(root, "fusion_inner", "", 548, 689, 380, 181, fill="none", stroke="#333333", dashed=True)
    add_rect(root, "rerank_group", "", 973, 183, 106, 585, fill="#d9efff", stroke="#000000", gradient="#ffffff")
    add_rect(root, "prompt_group", "", 1098, 183, 126, 585, fill="#ffffff", stroke="#000000")
    add_rect(root, "qwen_group", "", 1238, 183, 132, 585, fill="#e8dbff", stroke="#6f42c1", gradient="#ffffff")
    add_rect(root, "output_group", "", 1389, 183, 140, 585, fill="#ffffff", stroke="#000000")

    # 1) Media Input.
    red = "#ffd3d0"
    add_card(root, "sms", 18, 199, 116, 76, red, "#ffffff", "☵", "SMS", icon_size=32)
    add_card(root, "chat", 18, 312, 116, 83, red, "#ffffff", "▣", "Chat", "Screenshot", icon_size=32)
    add_card(root, "url", 18, 432, 116, 82, red, "#ffffff", "◎", "URL", icon_size=34)
    add_card(root, "social", 18, 550, 116, 82, red, "#ffffff", "◁", "Social", "Post", icon_size=34)
    add_card(root, "email", 18, 664, 116, 82, red, "#ffffff", "✉", "Email", icon_size=32)

    # 2) Text Preprocessing.
    yellow = "#ffe58b"
    green = "#c9f3ba"
    blue = "#d7ecfb"
    add_rect(root, "parsing_box", "<b>Parsing</b>", 190, 284, 106, 64, fill=yellow, gradient="#fff8ce", font_size=15)
    add_rect(root, "ocr_box", "<b>OCR</b>", 190, 396, 106, 65, fill=yellow, gradient="#fff8ce", font_size=16)
    add_rect(root, "norm_box", "<b>Normalization</b>", 190, 510, 106, 64, fill=green, gradient="#ffffff", font_size=14)
    add_rect(root, "token_box", "<b>Tokenized /<br>Normalized Text</b>", 190, 633, 106, 99, fill=blue, gradient="#ffffff", dashed=True, font_size=13)

    # 3) Risk Feature Extraction.
    add_small_card(root, "risk_suspicious", 351, 200, 142, 71, blue, "#ffffff", "🔍", "Suspicious", "Keywords")
    add_small_card(root, "risk_urgency", 351, 294, 142, 71, blue, "#ffffff", "⚠", "Urgency /", "Threat Wording")
    add_small_card(root, "risk_link", 351, 390, 142, 71, blue, "#ffffff", "🔗", "Link / Domain", "Signals")
    add_small_card(root, "risk_sender", 351, 485, 142, 70, blue, "#ffffff", "●", "Sender Identity", "Clues", icon_size=30)
    add_small_card(root, "risk_pattern", 351, 580, 142, 70, blue, "#ffffff", "◌", "Fraud Pattern", "Cues", icon_size=32)
    add_small_card(root, "risk_entity", 351, 676, 142, 69, blue, "#ffffff", "▤", "Entity", "Extraction", icon_size=30)
    add_rect(root, "risk_converted_box", "<b>Converted to<br>Risk Features</b>", 351, 772, 142, 70, fill=blue, gradient="#ffffff", dashed=True, font_size=13)

    # 4) Hybrid Evidence Retrieval.
    add_rect(root, "query_box", "<b>Query /</b><br><span style=\"font-size:11px\">Risk Features</span>", 516, 397, 68, 70, fill="#eadfff", gradient="#ffffff", font_size=13)
    add_small_card(root, "bm25", 614, 225, 208, 69, "#eadfff", "#ffffff", "🔍", "BM25 Retrieval", "lexical keyword matching", icon_size=32)
    add_small_card(root, "bge", 614, 324, 208, 70, "#eadfff", "#ffffff", "✣", "BGE-M3 Dense Retrieval", "semantic embedding retrieval", icon_size=34)
    add_small_card(root, "url_match", 614, 425, 208, 70, "#eadfff", "#ffffff", "◎", "URL / Domain Exact Match", "exact rule-based lookup", icon_size=34)
    add_small_card(root, "risk_lookup", 614, 526, 208, 87, "#eadfff", "#ffffff", "▥", "Risk-key Lookup / Knowledge Cues", "domain knowledge signals", icon_size=34)
    add_rect(
        root,
        "candidates_box",
        "<b>Retrieved</b><br><br><b>Candidates</b><br><br><span style=\"font-size:11px\">(from multiple<br>sources)</span>",
        854,
        368,
        72,
        139,
        fill=yellow,
        gradient="#ffffff",
        font_size=12,
    )

    add_text(root, "fusion_title", "5) Evidence Fusion<br><span style=\"font-size:13px\"><i>multi-source score fusion</i></span>", 620, 700, 232, 45, size=16, bold=True)
    add_rect(
        root,
        "fusion_formula",
        "<b>final score = α · bm25 + β · dense + γ · url + δ · risk</b><br><br><i>Deduplication &amp; score normalization</i>",
        551,
        762,
        362,
        92,
        fill=green,
        gradient="#ffffff",
        font_size=13,
    )

    # 6) Reranking.
    add_text(root, "rerank_icon", "↻", 994, 300, 64, 64, size=46)
    add_text(root, "rerank_label", "<b>Semantic<br>Reranking<br>of Retrieved<br>Evidence</b>", 987, 387, 80, 88, size=14, bold=False)
    add_line(root, "rerank_divider", 981, 522, 1072, 522, stroke="#000000", width=1)
    add_text(root, "rerank_output", "Output:<br>Top-K<br>Ranked<br>Evidence", 999, 553, 55, 88, size=14, bold=False)

    # 7) Prompt Construction.
    add_small_card(root, "prompt_user", 1106, 205, 108, 70, yellow, "#ffffff", "●", "User", "Content", icon_size=28)
    add_small_card(root, "prompt_risk", 1106, 308, 108, 70, yellow, "#ffffff", "☷", "Risk", "Features", icon_size=28)
    add_small_card(root, "prompt_evidence", 1106, 407, 108, 92, yellow, "#ffffff", "▤", "Top Retrieved", "Evidence", icon_size=28)
    add_small_card(root, "prompt_task", 1106, 530, 108, 70, yellow, "#ffffff", "✎", "Task", "Instruction", icon_size=28)
    add_rect(root, "assembled_prompt_box", "<b>Assembled<br>Reasoning<br>Prompt</b>", 1106, 641, 108, 106, fill="#ffffff", stroke="#333333", dashed=True, font_size=13)

    # 8) Qwen LLM Reasoning.
    add_text(root, "robot_body", "▣", 1270, 213, 75, 55, size=44)
    add_text(root, "robot_face", "● ●", 1286, 225, 44, 18, size=18)
    add_small_card(root, "qwen_context", 1249, 309, 112, 62, "#eadfff", "#ffffff", "☷", "Context-aware", "Reasoning", icon_size=27)
    add_small_card(root, "qwen_fraud", 1249, 407, 112, 72, "#eadfff", "#ffffff", "♢", "Fraud", "Analysis", icon_size=30)
    add_small_card(root, "qwen_explain", 1249, 504, 112, 88, "#eadfff", "#ffffff", "▤", "Evidence-grounded", "Explanation", icon_size=28)
    add_small_card(root, "qwen_question", 1249, 624, 112, 90, "#eadfff", "#ffffff", "?", "Training Question", "Generation", icon_size=32)

    # 9) Structured Anti-Fraud Output.
    add_small_card(root, "out_risk", 1397, 204, 118, 67, blue, "#ffffff", "♢", "Risk Level", icon_size=29)
    add_small_card(root, "out_type", 1397, 296, 118, 68, blue, "#ffffff", "◇", "Fraud Type", icon_size=30)
    add_small_card(root, "out_explain", 1397, 388, 118, 68, blue, "#ffffff", "▤", "Explanation", icon_size=29)
    add_small_card(root, "out_advice", 1397, 480, 118, 67, blue, "#ffffff", "◉", "Advice", icon_size=29)
    add_small_card(root, "out_training", 1397, 572, 118, 68, blue, "#ffffff", "?", "Training", "Question", icon_size=30)
    add_rect(root, "out_json_box", "<b>{ }</b>&nbsp;&nbsp; <b>Structured<br>JSON Output<br>(JSON)</b>", 1397, 664, 118, 82, fill=blue, gradient="#ffffff", font_size=12)

    # 10) Training question.
    add_rect(root, "training_box", "", 1340, 807, 182, 137, fill=green, gradient="#ffffff", stroke="#000000")
    add_text(root, "h10", "10) Anti-fraud<br>Training Question", 1364, 823, 138, 48, size=16, bold=True)
    add_icon(root, "training_icon", "▰", 1358, 883, 42, 38, size=31)
    add_text(root, "training_label", "<b>Final User-facing<br>Learning Prompt</b>", 1400, 882, 100, 42, size=12, bold=False)

    # Data flow footer.
    add_rect(root, "footer_box", "", 134, 890, 1175, 109, fill="#ffffff", stroke="#000000")
    footer = (
        "<b>Data flow:</b>&nbsp;&nbsp; media input&nbsp; → &nbsp;preprocessing&nbsp; → &nbsp;risk feature extraction&nbsp; → "
        "&nbsp;hybrid evidence retrieval&nbsp; → &nbsp;evidence fusion&nbsp; →<br>"
        "BGE reranking&nbsp; → &nbsp;prompt construction&nbsp; → &nbsp;Qwen LLM reasoning&nbsp; → "
        "&nbsp;structured JSON output&nbsp; → &nbsp;anti-fraud training question"
    )
    add_text(root, "footer_text", footer, 206, 907, 1038, 73, size=16, bold=False)

    # Main data-flow arrows fixed to the original image layout.
    add_poly_edge(root, "e_media_preprocess", [(134, 426), (178, 426)])
    add_poly_edge(root, "e_preprocess_risk", [(296, 428), (339, 428)])
    add_poly_edge(root, "e_risk_query", [(493, 432), (516, 432)])
    add_poly_edge(root, "e_candidates_rerank", [(926, 438), (973, 438)])
    add_poly_edge(root, "e_rerank_prompt", [(1060, 475), (1098, 475)])
    add_poly_edge(root, "e_prompt_qwen", [(1214, 475), (1238, 475)])
    add_poly_edge(root, "e_qwen_output", [(1361, 475), (1389, 475)])
    add_poly_edge(root, "e_output_training", [(1456, 746), (1456, 807)])

    # Internal preprocessing / feature arrows.
    add_poly_edge(root, "e_parse_ocr", [(243, 348), (243, 396)])
    add_poly_edge(root, "e_ocr_norm", [(243, 461), (243, 510)])
    add_poly_edge(root, "e_norm_token", [(243, 574), (243, 633)])
    add_poly_edge(root, "e_entity_converted", [(422, 745), (422, 772)])

    # Hybrid retrieval fixed buses and branches, matching the source composition.
    add_line(root, "retrieval_left_bus", 594, 254, 594, 570, stroke="#000000", width=2)
    add_poly_edge(root, "e_query_to_retrieval_bus", [(584, 432), (594, 432)], width=2)
    add_poly_edge(root, "e_left_bus_bm25", [(594, 260), (614, 260)], width=2)
    add_poly_edge(root, "e_left_bus_bge", [(594, 359), (614, 359)], width=2)
    add_poly_edge(root, "e_left_bus_url", [(594, 460), (614, 460)], width=2)
    add_poly_edge(root, "e_left_bus_lookup", [(594, 570), (614, 570)], width=2)

    add_line(root, "retrieval_right_bus", 834, 259, 834, 570, stroke="#000000", width=2)
    add_poly_edge(root, "e_bm25_to_right_bus", [(822, 259), (834, 259)], width=2, end_arrow=False)
    add_poly_edge(root, "e_bge_to_right_bus", [(822, 359), (834, 359)], width=2, end_arrow=False)
    add_poly_edge(root, "e_url_to_right_bus", [(822, 460), (834, 460)], width=2, end_arrow=False)
    add_poly_edge(root, "e_lookup_to_right_bus", [(822, 570), (834, 570)], width=2, end_arrow=False)
    add_poly_edge(root, "e_right_bus_candidates", [(834, 438), (854, 438)], width=2)

    add_poly_edge(root, "e_retrieval_fusion", [(718, 613), (718, 689)], width=2)

    xml = ET.tostring(mxfile, encoding="utf-8", xml_declaration=True)
    DRAWIO_PATH.write_bytes(xml)
    print(DRAWIO_PATH)


if __name__ == "__main__":
    main()
