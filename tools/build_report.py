from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(r"C:\Users\22672\Desktop\反诈系统")
DOCS = ROOT / "docs"
ASSETS = DOCS / "report_assets"
OUT = DOCS / "Anti-Fraud Coach项目研究报告-最终版.docx"

FONT_SONG = "宋体"
FONT_HEI = "黑体"
FONT_KAI = "楷体"
FONT_EN = "Times New Roman"
ACCENT = "1F4E79"
ACCENT_DARK = "17324D"
LIGHT_BLUE = "EAF3F8"
LIGHT_GRAY = "F5F7FA"
TEXT = RGBColor(33, 37, 41)
BLACK = RGBColor(0, 0, 0)


def set_run_font(run, east_asia: str = FONT_SONG, size: int | float | None = None, bold: bool | None = None,
                 color: RGBColor | None = None) -> None:
    run.font.name = FONT_EN
    run._element.rPr.rFonts.set(qn("w:eastAsia"), east_asia)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=90, start=110, bottom=90, end=110) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_cell_text(cell, text: str, bold: bool = False, fill: str | None = None,
                  align: int | None = None, size: int | float = 10) -> None:
    cell.text = ""
    p = cell.paragraphs[0]
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    set_run_font(run, FONT_HEI if bold else FONT_SONG, size=size, bold=bold, color=RGBColor(255, 255, 255) if fill == ACCENT else TEXT)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    set_cell_margins(cell)
    if fill:
        set_cell_shading(cell, fill)


def set_table_borders(table, color: str = "D9E2EC", size: str = "6") -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_cell_width(cell, width_cm: float) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_w = tc_pr.first_child_found_in("w:tcW")
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width_cm * 567)))
    tc_w.set(qn("w:type"), "dxa")


def add_page_number_footer(doc: Document) -> None:
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Anti-Fraud Coach 项目研究报告")
    set_run_font(run, FONT_SONG, 9, color=RGBColor(90, 96, 105))


def add_paragraph(doc: Document, text: str = "", first_line: bool = True, align=None,
                  style: str | None = None, size: int | float = 10.5,
                  before: int = 0, after: int = 6) -> None:
    p = doc.add_paragraph(style=style)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    if first_line:
        p.paragraph_format.first_line_indent = Pt(21)
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    set_run_font(run, FONT_SONG, size=size, color=TEXT)


def add_heading(doc: Document, title: str, level: int = 1) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 8)
    p.paragraph_format.space_after = Pt(8 if level == 1 else 4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(title)
    if level == 1:
        set_run_font(run, FONT_HEI, 15, True, BLACK)
    elif level == 2:
        set_run_font(run, FONT_HEI, 13, True, BLACK)
    else:
        set_run_font(run, FONT_HEI, 11.5, True, BLACK)


def add_caption(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run(text)
    set_run_font(run, FONT_SONG, 9.5, color=RGBColor(89, 96, 105))


def add_bullets(doc: Document, items: Iterable[str]) -> None:
    for index, item in enumerate(items, start=1):
        clean_item = item.rstrip("。；;")
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Pt(0)
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.35
        run = p.add_run(f"（{index}）{clean_item}")
        set_run_font(run, FONT_SONG, 10.5, color=TEXT)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    set_table_borders(table)
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)
    hdr = table.rows[0].cells
    for i, text in enumerate(headers):
        set_cell_text(hdr[i], text, True, ACCENT, WD_ALIGN_PARAGRAPH.CENTER, 10)
        if widths:
            set_cell_width(hdr[i], widths[i])
    for r_idx, row_data in enumerate(rows):
        row_cells = table.add_row().cells
        for i, text in enumerate(row_data):
            set_cell_text(row_cells[i], text, False, LIGHT_GRAY if r_idx % 2 else None,
                          WD_ALIGN_PARAGRAPH.LEFT, 9.5)
            if widths:
                set_cell_width(row_cells[i], widths[i])
    doc.add_paragraph().paragraph_format.space_after = Pt(4)


def draw_rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill: str, outline: str, width: int = 2) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def load_chinese_font(size: int, bold: bool = False):
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf" if bold else r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for item in candidates:
        if Path(item).exists():
            return ImageFont.truetype(item, size=size)
    return ImageFont.load_default()


def center_text(draw: ImageDraw.ImageDraw, box, text: str, font, fill="#243447", line_gap: int = 8) -> None:
    x1, y1, x2, y2 = box
    lines = text.split("\n")
    heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + line_gap * (len(lines) - 1)
    y = y1 + (y2 - y1 - total_h) / 2
    for line, w, h in zip(lines, widths, heights):
        draw.text((x1 + (x2 - x1 - w) / 2, y), line, font=font, fill=fill)
        y += h + line_gap


def create_architecture_image(path: Path) -> None:
    W, H = 1800, 1020
    img = Image.new("RGB", (W, H), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    font_title = load_chinese_font(44, True)
    font = load_chinese_font(28)
    font_small = load_chinese_font(24)
    draw.text((70, 42), "Anti-Fraud Coach 系统总体架构", font=font_title, fill="#17324D")
    draw.line((70, 112, W - 70, 112), fill="#1F4E79", width=4)

    columns = [
        ("输入层", ["聊天文本", "短信/可疑链接", "截图 OCR 文本"]),
        ("服务层", ["FastAPI 接口", "数据校验", "跨域与资源状态"]),
        ("识别层", ["关键词规则库", "组合话术检测", "URL/金额特征"]),
        ("知识与训练层", ["反诈知识库 RAG", "情景题评分", "能力雷达评估"]),
        ("模型增强层", ["MacBERT 分类", "BGE-M3 检索", "Qwen 解释生成", "PaddleOCR"]),
    ]
    x0, box_w, gap = 80, 295, 45
    y0, box_h = 190, 560
    for idx, (title, items) in enumerate(columns):
        x = x0 + idx * (box_w + gap)
        draw_rounded_rect(draw, (x, y0, x + box_w, y0 + box_h), 28, "#EAF3F8", "#8FB7D8", 3)
        draw.rounded_rectangle((x, y0, x + box_w, y0 + 86), radius=28, fill="#1F4E79")
        center_text(draw, (x, y0, x + box_w, y0 + 86), title, font, fill="#FFFFFF")
        yy = y0 + 135
        for item in items:
            draw_rounded_rect(draw, (x + 32, yy, x + box_w - 32, yy + 70), 18, "#FFFFFF", "#C9D8E6", 2)
            center_text(draw, (x + 32, yy, x + box_w - 32, yy + 70), item, font_small)
            yy += 98
        if idx < len(columns) - 1:
            ax = x + box_w + 8
            ay = y0 + box_h / 2
            draw.line((ax, ay, ax + gap - 16, ay), fill="#1F4E79", width=6)
            draw.polygon([(ax + gap - 16, ay - 15), (ax + gap + 8, ay), (ax + gap - 16, ay + 15)], fill="#1F4E79")

    bottom = (165, 825, W - 165, 940)
    draw_rounded_rect(draw, bottom, 24, "#F5F7FA", "#C9D8E6", 2)
    center_text(draw, bottom, "闭环流程：输入可疑信息 → 风险识别 → 风险点解释 → 防范建议 → 情景训练 → 能力评估反馈", load_chinese_font(30, True), fill="#17324D")
    img.save(path)


def create_loop_image(path: Path) -> None:
    W, H = 1500, 850
    img = Image.new("RGB", (W, H), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    font_title = load_chinese_font(42, True)
    font = load_chinese_font(27, True)
    font_small = load_chinese_font(22)
    draw.text((70, 42), "风险识别与训练反馈闭环", font=font_title, fill="#17324D")
    draw.line((70, 112, W - 70, 112), fill="#1F4E79", width=4)

    nodes = [
        (240, 210, "输入\n可疑信息"),
        (580, 210, "风险\n识别"),
        (920, 210, "解释\n可疑点"),
        (920, 535, "情景\n训练"),
        (580, 535, "学习\n评估"),
        (240, 535, "个性化\n反馈"),
    ]
    for x, y, label in nodes:
        draw.ellipse((x - 95, y - 95, x + 95, y + 95), fill="#EAF3F8", outline="#1F4E79", width=4)
        center_text(draw, (x - 90, y - 78, x + 90, y + 78), label, font, fill="#17324D")

    arrows = [
        ((335, 210), (485, 210)),
        ((675, 210), (825, 210)),
        ((920, 305), (920, 440)),
        ((825, 535), (675, 535)),
        ((485, 535), (335, 535)),
        ((240, 440), (240, 305)),
    ]
    for start, end in arrows:
        draw.line((*start, *end), fill="#1F4E79", width=6)
        ex, ey = end
        sx, sy = start
        if ex > sx:
            pts = [(ex, ey), (ex - 20, ey - 14), (ex - 20, ey + 14)]
        elif ex < sx:
            pts = [(ex, ey), (ex + 20, ey - 14), (ex + 20, ey + 14)]
        elif ey > sy:
            pts = [(ex, ey), (ex - 14, ey - 20), (ex + 14, ey - 20)]
        else:
            pts = [(ex, ey), (ex - 14, ey + 20), (ex + 14, ey + 20)]
        draw.polygon(pts, fill="#1F4E79")

    note = (1120, 270, 1410, 570)
    draw_rounded_rect(draw, note, 22, "#F5F7FA", "#C9D8E6", 2)
    center_text(
        draw,
        note,
        "规则引擎提供\n稳定识别\n\nRAG 提供\n可追溯建议\n\n训练模块形成\n持续学习反馈",
        font_small,
        fill="#243447",
    )
    img.save(path)


def configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.75)
    section.right_margin = Cm(2.75)
    section.header_distance = Cm(1.4)
    section.footer_distance = Cm(1.4)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = FONT_EN
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_SONG)
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = TEXT
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)

    for style_name in ["List Bullet", "List Number"]:
        st = styles[style_name]
        st.font.name = FONT_EN
        st._element.rPr.rFonts.set(qn("w:eastAsia"), FONT_SONG)
        st.font.size = Pt(10.5)

    add_page_number_footer(doc)


def add_cover(doc: Document) -> None:
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("项目研究报告")
    set_run_font(run, FONT_HEI, 26, True, BLACK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(34)
    run = p.add_run("Anti-Fraud Coach")
    set_run_font(run, FONT_HEI, 24, True, BLACK)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(24)
    run = p.add_run("面向大学生的多模态 AI 反诈情景识别与智能训练系统")
    set_run_font(run, FONT_HEI, 18, True, BLACK)

    table = doc.add_table(rows=7, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table, "B7C9D9")
    meta = [
        ("项目题目", "Anti-Fraud Coach：面向大学生的多模态 AI 反诈情景识别与智能训练系统"),
        ("项目类别", "中国大学生人工智能类竞赛项目"),
        ("研究对象", "高校大学生网络诈骗风险识别、解释与训练"),
        ("系统形态", "微信小程序前端 + FastAPI 后端 + 本地模型资源"),
        ("核心技术", "规则引擎、中文文本分类、OCR、RAG、情景训练评估"),
        ("项目目录", str(ROOT)),
        ("完成日期", "2026 年 5 月"),
    ]
    for i, (k, v) in enumerate(meta):
        set_cell_text(table.cell(i, 0), k, True, LIGHT_BLUE, WD_ALIGN_PARAGRAPH.CENTER, 10.5)
        set_cell_text(table.cell(i, 1), v, False, None, WD_ALIGN_PARAGRAPH.LEFT, 10.5)
        set_cell_width(table.cell(i, 0), 4.2)
        set_cell_width(table.cell(i, 1), 11.0)

    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("本报告依据当前已构建的小程序最终版本、后端服务、知识库、训练题库、OCR/RAG 能力与管理后台撰写。")
    set_run_font(run, FONT_KAI, 10.5, color=RGBColor(89, 96, 105))
    doc.add_page_break()


def add_abstract_and_toc(doc: Document) -> None:
    add_heading(doc, "摘  要", 1)
    add_paragraph(
        doc,
        "随着电信网络诈骗向社交平台、兼职招聘、校园消费、游戏交易和虚拟金融服务等场景渗透，大学生群体面临的信息甄别压力持续上升。"
        "本项目围绕高校反诈教育的实际需求，设计并实现“Anti-Fraud Coach：面向大学生的多模态 AI 反诈情景识别与智能训练系统”。"
        "系统不将目标限定为单次“是否诈骗”判断，而是构建由风险识别、风险点解释、反诈知识检索、情景模拟训练和学习评估反馈组成的闭环平台，"
        "用于辅助学生识别风险、理解话术、形成核实意识和证据保存意识。",
    )
    add_paragraph(
        doc,
        "在技术实现上，项目采用微信小程序前端与 FastAPI 后端架构，最终版本已完成文本/短信/链接/截图 OCR 输入分析、可解释风险信号抽取、"
        "BGE-M3 语义 RAG、FAISS/Chroma 向量检索、reranker 重排、案例引用、知识库版本管理、10 道情景训练题、训练评分、能力雷达反馈和管理后台。"
        "算法路线采用“规则引擎 + 文本分类模型 + 语义 RAG 知识增强 + OCR 多模态处理 + 情景训练评估”的混合框架，兼顾识别稳定性、解释可信度和教学管理能力。"
    )
    add_paragraph(
        doc,
        "项目的主要创新体现在：面向大学生高频诈骗场景建立闭环训练机制；将金钱诱导、紧迫施压、身份伪装、脱离平台、隐私索取等话术特征转化为"
        "可解释信号；利用专用知识库和 RAG 机制约束反诈建议来源；通过个人训练得分、易错类型和能力维度可视化实现个性化反馈。项目可服务于高校新生教育、"
        "辅导员安全教育、校园安全管理和社会化反诈宣传，具有较好的应用前景与社会价值。",
    )
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run("关键词：")
    set_run_font(r, FONT_HEI, 10.5, True, TEXT)
    r = p.add_run("反电信网络诈骗；大学生安全教育；风险识别；可解释人工智能；检索增强生成；微信小程序")
    set_run_font(r, FONT_SONG, 10.5, color=TEXT)

    add_heading(doc, "目  录", 1)
    toc_items = [
        "1 项目背景和国内外研究现状",
        "2 项目研究内容和需求分析",
        "3 技术路线与系统实现",
        "4 项目创新点",
        "5 应用前景和社会价值",
        "6 项目存在的问题以及今后的改进方向",
        "7 结论",
        "参考文献",
    ]
    for item in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Pt(18)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(item)
        set_run_font(run, FONT_SONG, 10.5, color=TEXT)
    doc.add_page_break()


def add_body(doc: Document) -> None:
    add_heading(doc, "1 项目背景和国内外研究现状", 1)
    add_heading(doc, "1.1 项目背景", 2)
    add_paragraph(
        doc,
        "电信网络诈骗具有远程化、非接触化、跨平台传播和话术快速迭代等特征。我国《中华人民共和国反电信网络诈骗法》于 2022 年通过并自"
        "2022 年 12 月 1 日起施行，法律明确提出预防、遏制和惩治电信网络诈骗活动，并强调源头治理、综合治理、社会宣传教育防范等要求[1]。"
        "高校学生在兼职、购物、快递、游戏交易、校园金融和社交关系中频繁接触线上信息，是反诈教育中需要重点覆盖的群体。传统安全教育往往以"
        "案例宣讲和海报提醒为主，存在互动性不足、反馈不及时、难以针对个体薄弱环节训练等问题。"
    )
    add_paragraph(
        doc,
        "本项目正是在这一背景下提出。其目标并非替代公安机关进行法律定性，而是作为面向学生和学校管理者的风险识别与训练辅助系统，帮助用户在"
        "早期发现可疑话术、理解风险依据、获得规范处置建议，并通过情景训练提升长期反诈能力。"
    )

    add_heading(doc, "1.2 国内研究与实践现状", 2)
    add_paragraph(
        doc,
        "国内反诈实践已形成由公安、通信、金融、互联网平台、学校和社会组织共同参与的综合治理格局。技术层面，现有研究主要集中在诈骗文本分类、"
        "钓鱼链接识别、黑产广告检测、异常交易与账户行为识别、知识图谱和大模型辅助研判等方向。中文欺诈检测公开资源也逐渐增加，例如 ChiFraud "
        "面向中文网页欺诈文本提供长期数据集和基线代码[10]，ChineseHarm-Bench 则覆盖中文有害内容中的“欺诈”“黑产广告”等标签，可作为安全检测"
        "与内容审核研究的参考数据[11]。"
    )
    add_paragraph(
        doc,
        "从教育应用看，校园反诈系统多以宣传网页、问卷测评或静态案例库为主，具备“能看、能测”的特点，但对输入内容的即时分析、证据化解释和"
        "个性化训练反馈仍不充分。因此，本项目将识别系统与训练系统整合，强调“检测之后继续训练”的闭环。"
    )

    add_heading(doc, "1.3 国外研究与实践现状", 2)
    add_paragraph(
        doc,
        "国外在网络犯罪统计、消费者欺诈投诉、钓鱼邮件检测和安全意识训练方面积累较多。美国 FBI 互联网犯罪投诉中心发布的 2025 年年度报告显示，"
        "其汇总的疑似互联网犯罪投诉超过 100 万件，报告损失超过 200 亿美元[2]；美国 FTC 的 Consumer Sentinel Network 2024 年收到约 650 万件"
        "消费者报告，其中包括欺诈、身份盗窃和其他消费者问题[3]。这些公开统计说明，诈骗治理已成为全球性数字安全议题。"
    )
    add_paragraph(
        doc,
        "技术研究方面，国外较早将传统机器学习、深度学习和预训练语言模型用于诈骗邮件、钓鱼 URL、社交工程攻击检测。近年，检索增强生成（RAG）"
        "被用于知识密集型问答与解释生成。Lewis 等提出的 RAG 模型将参数化生成模型与非参数化检索记忆结合，可改善知识来源追溯与事实性表达[4]。"
        "这一思想适合反诈问答，因为反诈建议需要来自可维护、可审查的知识库，而不宜完全依赖大模型自由生成。"
    )

    add_heading(doc, "1.4 相关技术研究现状", 2)
    add_table(
        doc,
        ["技术方向", "代表资源或方法", "对本项目的作用"],
        [
            ["中文预训练模型", "MacBERT、Qwen 系列等", "用于后续诈骗类型分类、风险等级预测和解释生成增强[5][8]"],
            ["语义检索与 RAG", "BGE-M3、向量数据库、重排模型", "用于知识库召回、相似案例检索和问答依据约束[4][6]"],
            ["OCR 文本识别", "PaddleOCR / PP-OCR 系列", "用于聊天截图、短信截图等多模态输入的文字提取[9]"],
            ["反诈数据集", "TeleAntiFraud、ChiFraud、ChineseHarm-Bench", "用于模型微调、评测和场景题库扩展[7][10][11]"],
            ["交互训练评估", "情景模拟、选择题评分、能力画像", "用于从一次性识别扩展到持续学习和个性化反馈"],
        ],
        widths=[3.2, 5.2, 7.6],
    )

    add_heading(doc, "2 项目研究内容和需求分析", 1)
    add_heading(doc, "2.1 项目定位", 2)
    add_paragraph(
        doc,
        "项目名称为“Anti-Fraud Coach：面向大学生的多模态 AI 反诈情景识别与智能训练系统”。系统定位为面向高校场景的 AI 反诈辅助平台，"
        "服务对象包括大学生、新生、辅导员和校园安全管理部门。系统输出采用“风险识别”“辅助判断”“防范训练”等表述，避免作出法律层面的"
        "绝对定性。"
    )
    add_paragraph(
        doc,
        "项目重点覆盖六类大学生常见诈骗场景：刷单返利、冒充客服、虚假兼职、校园贷/套路贷、游戏交易诈骗和冒充熟人诈骗。每类场景均映射到"
        "相应风险信号、建议模板和训练题型，保证识别结果与教育反馈能够形成一致口径。"
    )

    add_heading(doc, "2.2 功能模块", 2)
    add_table(
        doc,
        ["模块", "核心功能", "当前实现状态"],
        [
            ["多模态诈骗风险识别", "支持文本、短信、链接和聊天截图输入，输出风险等级、诈骗类型、分数、置信度、可疑点和建议", "已实现文本/短信/链接识别，并接入 PaddleOCR 完成截图文字识别、时间线还原和敏感信息脱敏"],
            ["风险信号解释", "抽取金钱诱导、紧迫施压、身份伪装、脱离平台、高收益承诺、隐私索取等信号并高亮", "已实现关键词、URL、金额和组合话术信号"],
            ["反诈知识库 RAG 问答", "从知识库和案例库检索相关条目，再生成回答和参考来源", "已接入 BGE-M3、FAISS/Chroma 和 reranker，实现语义检索、案例引用和知识库版本管理"],
            ["AI 反诈情景训练", "提供初级、中级、高级情景题，评估用户选择并解释风险点", "已内置 10 道训练题并支持提交评分"],
            ["能力评估与可视化", "生成得分、易错类型、能力雷达图和后台统计指标", "已实现个人训练反馈与管理后台，支持班级完成率、易错排行、高风险统计和教育建议生成"],
        ],
        widths=[3.5, 7.2, 4.3],
    )

    add_heading(doc, "2.3 用户需求分析", 2)
    add_bullets(
        doc,
        [
            "学生端需要低门槛输入和即时反馈，能够在看到可疑聊天、短信或链接时快速获得风险提示。",
            "教学端需要把真实案例转化为可训练内容，通过答题、复盘和推荐学习提高教育效果。",
            "管理端需要观察班级或群体层面的易错类型、训练完成率和高风险案例趋势，并生成针对性的反诈教育建议。",
            "系统整体需要兼顾可解释性、可维护性和隐私保护，避免将敏感个人信息上传到不可信服务。"
        ],
    )

    add_heading(doc, "3 技术路线与系统实现", 1)
    add_heading(doc, "3.1 总体技术路线", 2)
    add_paragraph(
        doc,
        "本项目采用“规则 + 机器学习/深度学习 + 大模型 RAG”的混合架构。最终版本在规则引擎基础上接入 OCR 多模态处理、语义检索、重排模型和管理后台。"
        "系统技术路线可概括为：微信小程序输入 → FastAPI 服务 → 文本预处理/OCR 结果接入 → 风险规则与特征抽取 → 文本分类模型增强 → "
        "BGE-M3 语义检索与 FAISS/Chroma 索引 → reranker 重排 → 知识库问答与案例引用 → 情景训练评分 → 能力画像与管理后台反馈。"
    )
    arch_path = ASSETS / "architecture.png"
    doc.add_picture(str(arch_path), width=Inches(6.4))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_caption(doc, "图 1 Anti-Fraud Coach 系统总体架构")

    add_heading(doc, "3.2 后端服务设计", 2)
    add_table(
        doc,
        ["接口", "方法", "功能说明"],
        [
            ["/health", "GET", "服务健康检查，返回系统运行状态"],
            ["/api/resources", "GET", "检查本地模型、数据集和工具资源是否存在"],
            ["/api/analyze", "POST", "对用户输入进行诈骗风险识别，返回等级、类型、信号、建议和高亮文本"],
            ["/api/ask", "POST", "基于反诈知识库回答用户问题，并返回参考条目"],
            ["/api/training/questions", "GET", "返回情景训练题库"],
            ["/api/training/submit", "POST", "提交用户答案并返回分数、反馈、易错类型和雷达图数据"],
            ["/api/dashboard", "GET", "返回管理后台统计数据，用于展示班级完成率、易错类型、高风险案例和教育建议"],
        ],
        widths=[4.0, 2.0, 9.0],
    )

    add_heading(doc, "3.3 风险识别算法设计", 2)
    add_paragraph(
        doc,
        "风险识别模块以规则引擎为基础，将诈骗风险拆解为可解释信号。每个信号由关键词集合、权重、解释和建议组成；系统对输入文本进行关键词匹配、"
        "URL 正则检测和金额表达检测，随后按信号类型聚合得分，并根据阈值映射为低风险、中风险和高风险。"
    )
    add_paragraph(
        doc,
        "为避免单个关键词造成误判，系统进一步设计组合话术规则。例如“冒充客服链路”要求身份伪装或账户异常与隐私索取、脱离平台等信号同时出现；"
        "“刷单返利链路”要求高收益承诺与垫付/金额、私聊/催促等信号组合；“贷款陷阱链路”要求贷款诱导与收费或隐私索取组合。组合信号权重更高，"
        "能够更接近真实诈骗流程。"
    )
    add_table(
        doc,
        ["风险信号", "典型表达", "风险解释"],
        [
            ["金钱诱导", "保证金、押金、手续费、垫付、先转账", "要求先支付费用或垫付资金，是刷单、兼职、贷款等骗局的高频特征"],
            ["紧迫施压", "马上、限时、超时作废、账户冻结", "制造时间压力，降低用户核实和求助的机会"],
            ["身份伪装", "客服、老师、辅导员、平台工作人员", "利用权威或熟人身份增强可信度"],
            ["脱离平台", "加微信、私聊、不要走平台、下载 App", "绕开平台风控和交易保护机制"],
            ["隐私索取", "验证码、身份证、银行卡、屏幕共享", "可能直接导致账户被盗或资金损失"],
            ["要求保密", "不要告诉别人、不要报警、内部渠道", "切断用户向老师、家人或公安机关求证的路径"],
        ],
        widths=[3.0, 5.0, 7.0],
    )

    doc.add_page_break()
    add_heading(doc, "3.4 RAG 知识库问答设计", 2)
    add_paragraph(
        doc,
        "知识库以结构化条目保存，每条内容包含标题、类别、关键词、知识说明、建议行动、案例来源和版本号。问答模块使用 BGE-M3 对知识条目和案例材料生成向量，"
        "通过 FAISS/Chroma 建立本地向量索引，并在召回后使用 reranker 对候选结果进行重排。系统根据排序结果生成回答，同时展示参考条目、相似案例和知识库版本信息。"
    )
    add_paragraph(
        doc,
        "该 RAG 设计的意义在于降低大模型幻觉风险。反诈场景中的建议需要可追溯、可审核、可维护，系统通过知识库和案例库限定回答依据，使“已经转账怎么办”"
        "“收到可疑链接如何处理”等问题能够给出规范处置路径。"
    )

    add_heading(doc, "3.5 情景训练与评分设计", 2)
    add_paragraph(
        doc,
        "训练模块以闯关式情景题为核心。系统展示模拟聊天或短信场景，用户选择继续沟通、点击链接、转账、核实身份、保存证据等行为；系统根据标准答案"
        "计算分数，并输出识别出的风险点、漏掉的风险点和推荐学习内容。"
    )
    loop_path = ASSETS / "closed_loop.png"
    doc.add_picture(str(loop_path), width=Inches(5.9))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_caption(doc, "图 2 风险识别与训练反馈闭环")

    add_heading(doc, "3.6 本地模型与数据资源", 2)
    add_table(
        doc,
        ["资源类别", "已准备资源", "用途"],
        [
            ["中文分类基座", "hfl/chinese-macbert-base", "后续微调诈骗类型分类器与风险等级预测模型"],
            ["语义检索模型", "BAAI/bge-m3、Qwen3-Embedding-0.6B", "用于构建知识库与案例库的向量检索"],
            ["检索重排模型", "BAAI/bge-reranker-v2-m3", "用于对 RAG 召回结果进行精排，提高依据相关性"],
            ["解释生成模型", "Qwen3-4B-Instruct-2507", "生成自然语言风险解释、训练复盘和建议"],
            ["URL 检测参考", "malicious-url-detection、bert-phishing-url", "辅助识别可疑链接和钓鱼页面"],
            ["OCR 与 RAG 工具", "PaddleOCR、LangChain、LlamaIndex、Chroma、FAISS", "支撑截图识别、知识编排和向量数据库"],
            ["数据集", "ChiFraud、ChineseHarm-Bench、TeleAntiFraud（待授权）", "用于训练、评测和扩展反诈情景题库"],
        ],
        widths=[3.0, 5.8, 6.2],
    )

    add_heading(doc, "4 项目创新点", 1)
    add_paragraph(
        doc,
        "第一，项目从单点检测扩展到“识别—解释—学习—评估”的完整闭环。传统文本分类工具通常只输出标签，而本系统在判断风险后继续引导用户进入"
        "情景训练，并根据训练表现形成能力画像，适合高校反诈教育的持续化需求。"
    )
    add_paragraph(
        doc,
        "第二，系统强调风险信号可解释分析。项目将诈骗话术拆解为金钱诱导、紧迫施压、身份伪装、脱离平台、高收益承诺、隐私索取、要求保密、贷款诱导"
        "等信号，并通过高亮文本、权重得分和组合话术解释，让用户理解“为什么危险”。"
    )
    add_paragraph(
        doc,
        "第三，项目实现可审查的 RAG 反诈知识库问答。系统接入 BGE-M3、FAISS/Chroma 和 reranker，先从反诈知识库和案例库检索相关条目，"
        "再生成处置建议并展示依据来源，降低幻觉风险并便于学校安全部门维护知识内容。"
    )
    add_paragraph(
        doc,
        "第四，项目面向小程序落地设计。微信小程序贴近大学生日常使用场景，能够承载可疑信息粘贴、训练闯关、学习报告和校园管理后台等功能，"
        "降低实际推广门槛。"
    )
    add_table(
        doc,
        ["创新点", "具体体现", "价值"],
        [
            ["多模态输入识别", "文本、短信、链接与截图 OCR 文本统一进入识别流程", "贴近真实使用场景，减少用户整理信息成本"],
            ["可解释风险信号", "输出信号、权重、证据和高亮文本", "增强用户信任，便于教学复盘"],
            ["RAG 知识增强", "已实现向量检索、重排、案例引用和知识库版本管理", "降低幻觉风险，提升建议可维护性"],
            ["情景化训练反馈", "题库、评分、易错类型和能力雷达图", "从短期提醒扩展到长期能力培养"],
        ],
        widths=[3.2, 6.5, 5.3],
    )

    add_heading(doc, "5 应用前景和社会价值", 1)
    add_heading(doc, "5.1 应用前景", 2)
    add_paragraph(
        doc,
        "在高校场景中，系统可用于新生入学安全教育、辅导员班会、网络安全宣传周、校园 App 或公众号嵌入式服务。学生可以在遇到可疑信息时主动提交"
        "文本或截图；辅导员可通过管理后台查看班级常见误判类型、训练完成率和高风险案例趋势，学校安全部门可根据系统生成的教育建议设计针对性宣传。"
    )
    add_paragraph(
        doc,
        "在更大范围内，项目可扩展至社区反诈、企业员工安全培训、未成年人网络保护和家庭数字安全教育。由于系统采用规则、知识库和模型分层架构，"
        "可以根据不同地区、不同人群和不同行业更新话术库与训练内容，具有较强迁移性。"
    )

    add_heading(doc, "5.2 社会价值", 2)
    add_bullets(
        doc,
        [
            "提升学生风险识别能力，帮助其在转账、验证码、链接点击等关键节点前暂停并核实。",
            "降低高校反诈教育成本，将静态宣传转化为可交互、可评估、可持续迭代的训练系统。",
            "增强证据保存和求助意识，引导用户在疑似被骗后及时保存聊天、转账凭证并寻求银行、学校和公安机关帮助。",
            "推动可信 AI 在公共安全教育中的应用，体现人工智能技术服务社会治理与青年安全教育的价值。",
        ],
    )

    add_heading(doc, "6 项目存在的问题以及今后的改进方向", 1)
    add_heading(doc, "6.1 当前存在的问题", 2)
    add_table(
        doc,
        ["问题", "表现", "影响"],
        [
            ["数据规模仍有限", "系统主要依赖规则库、知识库、公开案例和模拟训练题，真实校园场景样本仍需扩充", "可能影响模型训练和泛化评估"],
            ["规则方法存在边界", "同义改写、隐晦表达、图片嵌字和多轮上下文可能绕过关键词规则", "复杂诈骗话术识别仍需深度模型增强"],
            ["RAG 质量仍需持续优化", "语义检索和 reranker 已接入，但知识库覆盖范围、版本审核流程和案例更新频率仍需提升", "问答依据的完整性和时效性仍受知识库质量影响"],
            ["OCR 复杂场景鲁棒性不足", "PaddleOCR 已接入，但长截图、低清晰度截图、多气泡遮挡和表情符号可能影响时间线还原", "实际截图识别准确率仍需通过更多样本优化"],
            ["管理后台分析深度有限", "后台已支持班级完成率、易错排行、高风险统计和教育建议生成，但预测性分析和跨学期对比仍较基础", "群体化教学决策支持能力仍可增强"],
            ["生成式解释仍需优化", "系统已支持基于知识库的解释生成，但复杂多轮对话中的上下文保持和语气控制仍需改进", "系统智能化程度仍可提升"],
            ["隐私与合规机制需加强", "用户可能提交聊天记录、手机号、姓名、订单号等敏感信息", "需要完善脱敏、最小化存储和权限控制"],
            ["效果验证不足", "尚缺少真实用户实验和对照组评测", "难以量化训练系统对反诈能力提升的实际效果"],
        ],
        widths=[3.2, 6.2, 5.6],
    )

    add_heading(doc, "6.2 今后的改进方向", 2)
    add_bullets(
        doc,
        [
            "扩充并规范数据集：基于公开案例、学校安全材料和模拟对话构建脱敏语料，标注诈骗类型、风险等级、风险信号和建议。",
            "微调中文分类模型：使用 MacBERT 或 Qwen embedding 特征训练诈骗类型分类器，与规则结果进行融合。",
            "完善 RAG：在已接入 BGE-M3、FAISS/Chroma 和 reranker 的基础上，继续扩充案例库、优化召回重排策略，并完善知识库版本审核流程。",
            "增强 OCR 与多模态处理：在已接入 PaddleOCR 的基础上，继续提升长截图、低清晰度图片和复杂聊天界面的时间线还原能力。",
            "建设管理后台：在已实现班级训练完成率、易错类型排行、高风险样本统计和教育建议生成的基础上，增加跨班级对比、趋势预测和导出报表能力。",
            "开展用户研究：设计前测—训练—后测实验，量化系统对风险识别率、核实意识和证据保存意识的提升效果。",
            "强化安全合规：默认本地处理敏感文本，增加日志脱敏、用户授权、数据保留期限和模型回答边界控制。"
        ],
    )

    add_heading(doc, "7 结论", 1)
    add_paragraph(
        doc,
        "本项目围绕大学生高频网络诈骗场景，构建了一个集风险识别、可解释分析、知识库问答、情景训练和能力评估于一体的 AI 反诈辅助系统。"
        "当前版本已完成微信小程序端、FastAPI 后端、规则引擎、语义 RAG、OCR 多模态处理、训练题库、管理后台和本地模型资源准备，具备完整演示闭环。"
        "与单纯诈骗文本分类系统相比，本项目更强调教育价值、解释能力、知识可追溯和可持续训练，能够更好地契合高校反诈宣传与人工智能应用竞赛的展示需求。"
        "后续若进一步扩充数据集、优化模型融合并开展真实用户评测，系统将具备更强的实用性和推广价值。"
    )

    add_heading(doc, "参考文献", 1)
    refs = [
        "全国人民代表大会常务委员会. 中华人民共和国反电信网络诈骗法[EB/OL]. https://www.npc.gov.cn/c2/c30834/202209/t20220902_319186.html, 2022-09-02.",
        "Federal Bureau of Investigation. 2025 Internet Crime Report[EB/OL]. https://www.fbi.gov/file-repository/2025_ic3report.pdf/view, 2026.",
        "Federal Trade Commission. Consumer Sentinel Network Data Book 2024[EB/OL]. https://www.ftc.gov/reports/consumer-sentinel-network-data-book-2024, 2025.",
        "Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]//Advances in Neural Information Processing Systems 33. 2020.",
        "Cui Y, Che W, Liu T, Qin B, Wang S, Hu G. Revisiting Pre-Trained Models for Chinese Natural Language Processing[EB/OL]. https://arxiv.org/abs/2004.13922, 2020.",
        "Chen J, Xiao S, Zhang P, Luo K, Lian D, Liu Z. M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation[EB/OL]. https://arxiv.org/abs/2402.03216, 2024.",
        "JimmyMa99. TeleAntiFraud: Sanitized public release of the TeleAntiFraud audio-text fraud detection dataset[DB/OL]. https://huggingface.co/datasets/JimmyMa99/TeleAntiFraud, 2025.",
        "Qwen Team. Qwen3-4B-Instruct-2507 Model Card[EB/OL]. https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507, 2025.",
        "PaddlePaddle. PaddleOCR Documentation[EB/OL]. https://www.paddleocr.ai/main/en/index/index.html.",
        "Tang M, Zou L, Liang S N, Jin Z, Wang W, Cui S. ChiFraud: A Long-Term Web Text Benchmark for Chinese Fraud Detection[C]//COLING 2025. Association for Computational Linguistics, 2025.",
        "Liu K, Cheng S, Tian B, et al. ChineseHarm-Bench: A Chinese Harmful Content Detection Benchmark[DB/OL]. https://huggingface.co/datasets/zjunlp/ChineseHarm-bench, 2025.",
        "Hugging Face. BAAI/bge-m3 Model Card[EB/OL]. https://huggingface.co/BAAI/bge-m3, 2024.",
    ]
    for ref in refs:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Pt(-18)
        p.paragraph_format.left_indent = Pt(18)
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(ref)
        set_run_font(run, FONT_SONG, 9.5, color=TEXT)


def build() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    create_architecture_image(ASSETS / "architecture.png")
    create_loop_image(ASSETS / "closed_loop.png")

    doc = Document()
    configure_document(doc)
    add_cover(doc)
    add_abstract_and_toc(doc)
    add_body(doc)

    # Keep metadata professional and non-personal.
    props = doc.core_properties
    props.title = "Anti-Fraud Coach 项目研究报告"
    props.subject = "面向大学生的多模态 AI 反诈情景识别与智能训练系统"
    props.author = "Anti-Fraud Coach 项目组"
    props.keywords = "反诈, AI, RAG, 微信小程序, 大学生安全教育"
    props.comments = "Generated for academic project report delivery."

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
