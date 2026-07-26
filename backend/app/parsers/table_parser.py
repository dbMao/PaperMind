"""
pdfplumber 表格解析器 —— 补充提取 PDF 中的表格数据。
"""

import logging

logger = logging.getLogger(__name__)


class TableParser:
    """基于 pdfplumber 的表格提取器"""

    def extract_tables(self, file_path: str) -> list[dict]:
        """
        提取 PDF 中的表格。

        Args:
            file_path: PDF 文件路径

        Returns:
            表格列表，每个表格为 {page, rows, headers}
        """
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber 未安装，跳过表格提取")
            return []

        tables = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    extracted = page.extract_tables()
                    if extracted:
                        for table_idx, table in enumerate(extracted):
                            if table and len(table) > 1:
                                # 清理单元格文本
                                cleaned = []
                                for row in table:
                                    if row and any(cell for cell in row if cell):
                                        cleaned.append([
                                            str(cell).strip() if cell else ""
                                            for cell in row
                                        ])
                                if cleaned:
                                    headers = cleaned[0] if cleaned else []
                                    tables.append({
                                        "page": page_num,
                                        "rows": cleaned,
                                        "headers": headers,
                                        "row_count": len(cleaned),
                                        "col_count": len(headers),
                                    })
        except Exception as e:
            logger.warning(f"表格提取出错: {e}")

        return tables
