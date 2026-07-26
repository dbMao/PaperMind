"""
解析调度服务 —— 协调 PyMuPDF、pdfplumber、unstructured.io 三级解析策略。
"""

import base64
import logging

import fitz  # PyMuPDF

from app.parsers.pymupdf_parser import PyMuPDFParser, ParsedDocument, Section
from app.parsers.table_parser import TableParser

logger = logging.getLogger(__name__)

# 页面渲染 DPI（越高越清晰，文件越大）
RENDER_DPI = 150


class ParserService:
    """PDF 解析调度服务（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pymupdf = PyMuPDFParser()
            cls._instance._table = TableParser()
        return cls._instance

    def parse(self, file_path: str, enable_ai_enhance: bool = False) -> ParsedDocument:
        """
        解析 PDF 文件。

        Args:
            file_path: PDF 文件路径
            enable_ai_enhance: 是否启用 AI 增强（暂未实现，预留接口）

        Returns:
            ParsedDocument 对象
        """
        # Step 1: PyMuPDF 主力解析
        doc = self._pymupdf.parse(file_path)
        logger.info(f"PyMuPDF 解析完成: {doc.title}, {len(doc.sections)} 个节")

        # Step 2: 表格检测
        if self._pymupdf.has_tables(file_path):
            tables = self._table.extract_tables(file_path)
            if tables:
                logger.info(f"pdfplumber 补充提取了 {len(tables)} 个表格")
                self._merge_tables(doc, tables)

        # Step 3: AI 增强（预留）
        if enable_ai_enhance:
            logger.info("AI 增强解析已启用（暂未实现，使用默认解析）")

        return doc

    def render_pages(self, file_path: str) -> list[dict]:
        """
        渲染每页为图片 + 提取文字块坐标。

        Args:
            file_path: PDF 文件路径

        Returns:
            [{page, width, height, image_base64, blocks: [{text, bbox, font_size}]}]
        """
        pages = []
        doc = fitz.open(file_path)

        for page_num in range(len(doc)):
            page = doc[page_num]

            # 渲染高清图片
            pix = page.get_pixmap(dpi=RENDER_DPI)
            img_bytes = pix.tobytes("png")
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            # 提取文字块（含坐标）
            blocks_data = []
            text_dict = page.get_text("dict")
            for block in text_dict["blocks"]:
                if block["type"] != 0:  # 只处理文本块，跳过图片块
                    continue
                bbox = block["bbox"]  # (x0, y0, x1, y1) in PDF points
                block_text_parts = []
                max_font = 0
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        block_text_parts.append(span["text"])
                        max_font = max(max_font, span["size"])

                text = " ".join(block_text_parts).strip()
                if not text or len(text) < 2:
                    continue

                # 坐标转换为图片像素
                scale = RENDER_DPI / 72.0
                blocks_data.append({
                    "text": text,
                    "bbox": {
                        "x": round(bbox[0] * scale),
                        "y": round(bbox[1] * scale),
                        "w": round((bbox[2] - bbox[0]) * scale),
                        "h": round((bbox[3] - bbox[1]) * scale),
                    },
                    "font_size": round(max_font, 1),
                })

            pages.append({
                "page": page_num,
                "width": pix.width,
                "height": pix.height,
                "image": f"data:image/png;base64,{img_b64}",
                "blocks": blocks_data,
            })

        doc.close()
        logger.info(f"页面渲染完成: {len(pages)} 页, 总计 {sum(len(p['blocks']) for p in pages)} 个文字块")
        return pages

    def _merge_tables(self, doc: ParsedDocument, tables: list[dict]):
        """将表格数据合并到对应的节中"""
        for table in tables:
            page = table["page"]
            for section in doc.sections:
                if section.page_start <= page <= section.page_end:
                    section.has_table = True
                    table_text = "\n[TABLE]\n"
                    for row in table["rows"]:
                        table_text += " | ".join(row) + "\n"
                    section.content += table_text


parser_service = ParserService()

