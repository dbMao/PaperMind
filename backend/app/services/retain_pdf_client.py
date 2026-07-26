"""
PDF 翻译客户端 — 基于 pdf2zh（PDFMathTranslate）。
pip 安装，零额外依赖，保留排版翻译。
"""

import logging
import os
import tempfile

logger = logging.getLogger(__name__)


class RetainPDFClient:
    """pdf2zh 翻译客户端"""

    _doc_model = None  # 缓存 ONNX 模型，避免每次加载

    def _get_model(self):
        if self._doc_model is not None:
            return self._doc_model
        from pdf2zh.doclayout import OnnxModel, get_doclayout_onnx_model_path
        onnx_path = get_doclayout_onnx_model_path()
        if onnx_path and onnx_path.exists():
            self._doc_model = OnnxModel(str(onnx_path))
        return self._doc_model

    def translate_pdf(
        self,
        pdf_path: str,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        lang_out: str = "zh",
    ) -> dict:
        """
        使用 pdf2zh 翻译 PDF 文件，保留排版。

        Args:
            pdf_path: 源 PDF 路径
            api_key: LLM API 密钥
            base_url: OpenAI 兼容 API 端点
            model: 模型名称
            lang_out: 目标语言

        Returns:
            {"success": bool, "pdf_path": str | None, "message": str}
        """
        try:
            from pdf2zh.high_level import translate

            doc_model = self._get_model()
            if not doc_model:
                return {"success": False, "pdf_path": None, "message": "文档布局模型未下载"}

            output_dir = tempfile.mkdtemp(prefix="papermind_trans_")

            old_env = {}
            for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL"):
                old_env[key] = os.environ.get(key, "")
            os.environ["OPENAI_API_KEY"] = api_key
            os.environ["OPENAI_BASE_URL"] = base_url.rstrip("/")
            os.environ["OPENAI_MODEL"] = model

            logger.info(f"pdf2zh 翻译开始: {pdf_path} (thread=16)")

            translate(
                files=[pdf_path],
                output=output_dir,
                lang_in="en",
                lang_out=lang_out,
                service="openai",
                thread=16,       # 高并发，大幅加速
                model=doc_model,
                ignore_cache=False,
            )

            # 恢复环境变量
            for key, val in old_env.items():
                if val:
                    os.environ[key] = val
                else:
                    os.environ.pop(key, None)

            # 查找输出文件（pdf2zh 输出为 <name>-mono.pdf 或 <name>-dual.pdf）
            base = os.path.splitext(os.path.basename(pdf_path))[0]
            candidates = [
                os.path.join(output_dir, f"{base}-mono.pdf"),
                os.path.join(output_dir, f"{base}-dual.pdf"),
            ]
            out_path = None
            for c in candidates:
                if os.path.exists(c):
                    out_path = c
                    break

            if out_path:
                logger.info(f"pdf2zh 翻译完成: {out_path}")
                return {"success": True, "pdf_path": out_path, "message": "翻译完成"}
            else:
                # 列出 output 目录看有什么
                files = os.listdir(output_dir) if os.path.exists(output_dir) else []
                logger.warning(f"未找到翻译输出文件，output 目录内容: {files}")
                return {"success": False, "pdf_path": None, "message": f"翻译输出未生成，目录内容: {files}"}

        except ImportError:
            return {"success": False, "pdf_path": None, "message": "pdf2zh 未安装，请运行 pip install pdf2zh"}
        except Exception as e:
            logger.exception("pdf2zh 翻译失败")
            return {"success": False, "pdf_path": None, "message": str(e)[:500]}


retain_pdf_client = RetainPDFClient()
