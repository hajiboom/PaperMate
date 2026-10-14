"""生成 testdata/sample.pdf：一个模拟知网社科论文版式的中文 PDF。"""

import pymupdf

W, H = 595, 842
doc = pymupdf.open()

FONT = "china-s"


def add_text(page, text, fontsize: float = 12, y: float = 0, x: float = 72, align: int = 0, rect=None) -> None:
    if rect:
        page.insert_textbox(rect, text, fontname=FONT, fontsize=fontsize, align=align or 0)
        return
    page.insert_text((x, y), text, fontname=FONT, fontsize=fontsize)


def add_paragraph(page, text, fontsize: float = 12, y: float = 0, x: float = 72, chars_per_line: int = 38, line_gap: float = 16) -> float:
    """把长段落手动换行插入，模拟真实 PDF 的排版换行（段首两格缩进）。"""
    lines = [text[i : i + chars_per_line] for i in range(0, len(text), chars_per_line)]
    lines[0] = "　　" + lines[0]
    for i, line in enumerate(lines):
        add_text(page, line, fontsize=fontsize, y=y + i * line_gap, x=x)
    return y + len(lines) * line_gap


# ---- 第 1 页 ----
page = doc.new_page(width=W, height=H)

# 标题（大字号，供版面标题提取）
add_text(page, "数字化转型背景下基层治理能力提升研究", fontsize=18, y=120, x=72)
add_text(page, "张明  李华", fontsize=12, y=155, x=72)
add_text(page, "(某大学 社会管理学院, 北京 100000)", fontsize=10, y=175, x=72)

add_text(
    page,
    "摘　要：数字技术正在深刻改变基层治理的运行方式。本文基于对某市12个社区的实地调查，",
    fontsize=10.5,
    y=215,
    x=72,
)
cursor = add_paragraph(
    page,
    "考察数字化转型对基层治理能力的影响机制。研究发现，数字技术通过信息整合、流程再造与"
    "协同动员三条路径提升了基层治理能力，但也带来了数字形式主义与基层负担加重的问题。",
    fontsize=10.5,
    y=235,
    x=100,
)
add_text(page, "关键词：数字化转型；基层治理；社区治理；数字形式主义", fontsize=10.5, y=290, x=72)

body1 = [
    ("一、问题的提出", 14, None),
    (("随着数字政府建设的推进，基层治理的数字化转型成为公共管理研究的重要议题。既有研究多关注技"
     "术采纳的宏观条件，对基层治理能力如何因数字化而改变的经验研究仍不充分。"
     "本文试图回答：数字化转型在何种条件下能够提升基层治理能力？"), 12, "para"),
    ("（一）研究背景", 12, None),
    (("近年来，各地推进智慧社区建设，网格化管理平台、政务服务App在基层普遍落地。然而基层干部"
     "普遍反映线上填表负担加重，出现了指尖上的形式主义。"), 12, "para"),
    ("（二）文献回顾", 12, None),
    (("技术治理文献强调技术嵌入科层结构的过程。治理能力文献则关注资源、组织与合法性的匹配。"
     "两类文献较少对话，本文尝试将其结合。"), 12, "para"),
]

cursor = 330
for text, size, kind in body1:
    if kind == "para":
        cursor = add_paragraph(page, text, fontsize=size, y=cursor) + 14
    else:
        add_text(page, text, fontsize=size, y=cursor, x=72)
        cursor += size * 2.2 + 6

# 页脚
add_text(page, "2", fontsize=10, y=H - 40, x=W / 2)

# ---- 第 2 页 ----
page2 = doc.new_page(width=W, height=H)
add_text(page2, "数字化转型背景下基层治理能力提升研究", fontsize=9, y=50, x=72)

body2 = [
    ("二、研究设计", 14, None),
    (("本文采用案例比较方法，选取某市中心城区12个社区作为研究对象，"
     "于2024年6月至12月开展实地调查，共访谈社区工作者36人、居民58人。"), 12, "para"),
    ("三、案例分析", 14, None),
    ("（一）信息整合", 12, None),
    ("平台将原本分散在多个条线的台账整合为统一数据底座，减少了重复填报。", 12, "para"),
    ("（二）流程再造", 12, None),
    ("网格事件处置流程由线下逐级上报转为线上派单，平均处置周期从7天缩短至2天。", 12, "para"),
    ("（三）数字形式主义", 12, None),
    (("与此同时，App打卡、拍照留痕等要求使社区工作者平均每天额外投入约1.5小时用于线上应付，"
     "技术负担在考核压力下转化为新的负担。"), 12, "para"),
    ("四、结论与讨论", 14, None),
    (("数字化转型对基层治理能力的影响具有两面性：信息整合与流程再造提升效率，"
     "但缺乏统筹的线上考核会诱发数字形式主义。本文的政策建议仍属原则性判断，"
     "其因果识别也受到案例数量限制，结论需谨慎对待。"), 12, "para"),
]

cursor = 90
for text, size, kind in body2:
    if kind == "para":
        cursor = add_paragraph(page2, text, fontsize=size, y=cursor) + 14
    else:
        add_text(page2, text, fontsize=size, y=cursor, x=72)
        cursor += size * 2.4 + 6

add_text(page2, "参考文献", fontsize=14, y=cursor + 10, x=72)
cursor += 40
refs = [
    "1. 阿加. 技术治理的限度. 公共管理学报, 2020(3).",
    "2. 陈家建. 项目制与基层政府动员. 中国社会科学, 2015(10).",
    "3. Digitizing State Capacity. American Political Science Review, 2023.",
]
for ref in refs:
    add_text(page2, ref, fontsize=10, y=cursor, x=72)
    cursor += 20

add_text(page2, "1", fontsize=10, y=H - 40, x=W / 2)

doc.save("testdata/sample.pdf")
doc.close()
print("saved testdata/sample.pdf")
