"""
PyMuPDF 解析器 —— 提取 PDF 文本、标题层级、元数据。
"""

import re
from collections import Counter
from dataclasses import dataclass, field

import fitz  # PyMuPDF


@dataclass
class Section:
    """文档节"""
    title: str
    level: int  # 标题层级 1-4
    content: str
    page_start: int
    page_end: int
    has_table: bool = False


@dataclass
class ParsedDocument:
    """解析后的论文文档"""
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str = ""
    page_count: int = 0
    sections: list[Section] = field(default_factory=list)
    raw_text: str = ""


class PyMuPDFParser:
    """基于 PyMuPDF 的 PDF 解析器"""

    # 常见的标题模式，用于识别论文标题
    TITLE_PATTERNS = [
        r"^(.*?(?:University|College|Institute|Laboratory|Lab|Department|School|Center|Centre).*)$",
    ]

    def __init__(self):
        self._median_font_size = 0

    def parse(self, file_path: str) -> ParsedDocument:
        """
        解析 PDF 文件，提取结构化内容。

        Args:
            file_path: PDF 文件路径

        Returns:
            ParsedDocument 对象
        """
        doc = fitz.open(file_path)
        page_count = len(doc)

        all_blocks = []
        for page_num in range(page_count):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if block["type"] == 0:  # 文本块
                    block["_page"] = page_num
                    all_blocks.append(block)

        # 计算中位数字体大小（用于标题检测）
        font_sizes = []
        for block in all_blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    font_sizes.append(span["size"])
        if font_sizes:
            self._median_font_size = sorted(font_sizes)[len(font_sizes) // 2]

        # 提取标题和作者
        title = self._extract_title(doc, all_blocks)
        authors = self._extract_authors(doc, all_blocks)
        year = self._extract_year(doc, all_blocks)
        abstract = self._extract_abstract(all_blocks)

        # 提取完整文本
        raw_text = ""
        for page in doc:
            raw_text += page.get_text()

        # 提取节
        sections = self._extract_sections(all_blocks)

        doc.close()

        return ParsedDocument(
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            page_count=page_count,
            sections=sections,
            raw_text=raw_text,
        )

    def _extract_title(self, doc: fitz.Document, blocks: list) -> str:
        """从第一页顶部提取论文标题"""
        if len(doc) == 0:
            return "未命名论文"

        first_page = doc[0]
        page_height = first_page.rect.height
        text_blocks = [b for b in blocks if b.get("_page") == 0]

        if not text_blocks:
            return "未命名论文"

        # 计算中位数字体（用于判断标题）
        all_sizes = []
        for b in text_blocks:
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    all_sizes.append(span["size"])
        median_size = sorted(all_sizes)[len(all_sizes) // 2] if all_sizes else 10

        # 按 Y 位置排序（从上到下），取页面顶部 1/3 区域内的块
        top_blocks = []
        for b in text_blocks:
            bbox = b.get("bbox", (0, 0, 0, 0))
            y = bbox[1]  # top Y
            # 只考虑页面顶部 1/3
            if y > page_height * 0.35:
                continue
            text = ""
            max_span = 0
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    text += span["text"] + " "
                    max_span = max(max_span, span["size"])
            text = text.strip()
            if len(text) > 5:
                top_blocks.append({
                    "text": text,
                    "y": y,
                    "size": max_span,
                })

        # 按 Y 排序，取第一个大于中位数字体的块
        top_blocks.sort(key=lambda b: b["y"])

        for b in top_blocks:
            if b["size"] >= median_size * 1.15 and len(b["text"]) > 10:
                # 排除明显不是标题的行（如作者信息、期刊名等）
                lower = b["text"].lower()
                skip = ["introduction", "abstract", "university", "college",
                        "ieee", "acm", "proceedings", "international",
                        "conference", "journal", "transaction"]
                if not any(w in lower for w in skip):
                    return b["text"][:500]

        # 回退：用最大字体的顶部块
        if top_blocks:
            return top_blocks[0]["text"][:500]
        return "未命名论文"

    def _extract_authors(self, doc: fitz.Document, blocks: list) -> list[str]:
        """提取作者列表"""
        if len(doc) > 0:
            first_page_text = doc[0].get_text()
            # 常见模式: 标题后面紧跟的作者行
            lines = first_page_text.split("\n")
            for i, line in enumerate(lines):
                if i < 10 and len(line) > 5:
                    # 包含逗号分隔的可能是作者行
                    if "," in line and len(line.split(",")) >= 2:
                        parts = [p.strip() for p in line.split(",")]
                        if all(len(p) < 60 for p in parts) and len(parts) <= 20:
                            # 过滤掉明显不是人名的行
                            skip_words = ["abstract", "university", "introduction"]
                            if not any(w in line.lower() for w in skip_words):
                                return parts[:10]
        return []

    def _extract_year(self, doc: fitz.Document, blocks: list) -> int | None:
        """从文本中提取年份"""
        if len(doc) > 0:
            text = doc[0].get_text()[:1000]
            # 匹配 19xx 或 20xx 年的模式
            match = re.search(r"(19|20)\d{2}", text)
            if match:
                return int(match.group())
        return None

    def _extract_abstract(self, blocks: list) -> str:
        """提取摘要"""
        in_abstract = False
        lines = []
        for block in blocks:
            text = ""
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text += span["text"] + " "
            text = text.strip()

            if not text:
                continue

            lower = text.lower()
            if lower.startswith("abstract"):
                in_abstract = True
                text = text[len("abstract"):].strip().lstrip(":.- ")
                if text:
                    lines.append(text)
                continue

            if in_abstract:
                # 遇到关键词或短标题结束摘要
                if lower.startswith(("introduction", "1.", "1 ", "ii.", "keywords")):
                    break
                if len(text) > 10:
                    lines.append(text)
                    if len(" ".join(lines)) > 800:
                        break

        return " ".join(lines) if lines else ""

    def _extract_sections(self, blocks: list) -> list[Section]:
        """按标题边界提取节结构"""
        sections = []
        current_title = "引言"
        current_level = 1
        current_content = []
        current_page_start = 0
        current_page_end = 0

        # 常见的节标题模式
        section_pattern = re.compile(
            r"^(\d+(?:\.\d+)*)\s+(.+?)$"  # "3.1 Model Architecture"
            r"|^([IVX]+\.)\s+(.+?)$"       # "IV. Results"
            r"|^(Abstract|Introduction|Related Work|Method|Experiment|Result|Conclusion|Discussion|Reference|Appendix|Acknowledg)",
            re.IGNORECASE,
        )

        for block in blocks:
            text = ""
            max_font = 0
            is_bold = False
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text += span["text"] + " "
                    max_font = max(max_font, span["size"])
                    if span["flags"] & 2**3:  # bold flag
                        is_bold = True
            text = text.strip()

            if not text:
                continue

            page = block.get("_page", 0)

            # 检测是否为标题
            is_heading = False
            heading_level = 1

            if max_font > self._median_font_size * 1.3 and len(text) < 200:
                is_heading = True
                heading_level = 2 if max_font > self._median_font_size * 1.6 else 3
            elif section_pattern.match(text) and len(text) < 150:
                is_heading = True
                heading_level = 2
            elif is_bold and len(text) < 100 and max_font >= self._median_font_size:
                is_heading = True
                heading_level = 3

            if is_heading:
                # 保存前一节
                if current_content:
                    sections.append(Section(
                        title=current_title,
                        level=current_level,
                        content="\n".join(current_content),
                        page_start=current_page_start,
                        page_end=current_page_end or page,
                    ))

                current_title = text
                current_level = heading_level
                current_content = []
                current_page_start = page
                current_page_end = page
            else:
                current_content.append(text)
                current_page_end = page

        # 保存最后一节
        if current_content:
            sections.append(Section(
                title=current_title,
                level=current_level,
                content="\n".join(current_content),
                page_start=current_page_start,
                page_end=current_page_end,
            ))

        # 如果只检测到一个节（可能无标题），尝试按空行分割
        if len(sections) <= 1 and sections:
            raw_paras = sections[0].content.split("\n\n")
            if len(raw_paras) > 3:
                new_sections = []
                for i, para in enumerate(raw_paras):
                    para = para.strip()
                    if not para:
                        continue
                    # 前几个段落可能是摘要
                    label = "正文"
                    new_sections.append(Section(
                        title=label,
                        level=2,
                        content=para,
                        page_start=0,
                        page_end=0,
                    ))
                sections = new_sections

        return sections

    def has_tables(self, file_path: str) -> bool:
        """检测 PDF 中是否包含表格"""
        doc = fitz.open(file_path)
        try:
            for page in doc:
                tabs = page.find_tables()
                if tabs and len(tabs.tables) > 0:
                    return True
            return False
        finally:
            doc.close()
