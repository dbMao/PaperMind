"""
翻译服务 —— 基于 Helsinki-NLP/opus-mt-en-zh 的本地机器翻译。

首次使用需执行 scripts/deploy_opus_mt.py 下载模型（~300MB）。
模型下载到本地后，翻译完全离线运行，数据不出本机。
"""

import os
from pathlib import Path
from app.core.config import settings

# 模型缓存目录
MODEL_DIR = Path(settings.TRANSLATION_MODEL_DIR or "./models/opus-mt-en-zh")
MODEL_NAME = "Helsinki-NLP/opus-mt-en-zh"


class TranslationService:
    """本地翻译服务 —— 懒加载单例"""

    _instance = None
    _model = None
    _tokenizer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def is_deployed(self) -> bool:
        """检查模型是否已下载到本地"""
        return MODEL_DIR.exists() and any(MODEL_DIR.iterdir())

    def deploy(self) -> dict:
        """
        下载模型到本地。

        Returns:
            {"status": "deploying" | "deployed" | "error", "message": str}
        """
        if self.is_deployed:
            return {"status": "deployed", "message": "模型已部署"}

        try:
            from transformers import MarianMTModel, MarianTokenizer
            import shutil

            MODEL_DIR.mkdir(parents=True, exist_ok=True)

            # 下载并缓存到本地
            tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
            model = MarianMTModel.from_pretrained(MODEL_NAME)

            # 保存到本地目录
            tokenizer.save_pretrained(str(MODEL_DIR))
            model.save_pretrained(str(MODEL_DIR))

            self._tokenizer = tokenizer
            self._model = model

            return {"status": "deployed", "message": "模型部署成功"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _load_model(self):
        """懒加载模型到内存"""
        if self._model is not None:
            return

        from transformers import MarianMTModel, MarianTokenizer

        if self.is_deployed:
            # 从本地加载（更快）
            self._tokenizer = MarianTokenizer.from_pretrained(str(MODEL_DIR))
            self._model = MarianMTModel.from_pretrained(str(MODEL_DIR))
        else:
            # 首次从 HuggingFace 加载并缓存
            self._tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
            self._model = MarianMTModel.from_pretrained(MODEL_NAME)

    def translate(self, text: str) -> str:
        """
        翻译单段英文文本 → 中文。

        Args:
            text: 英文原文

        Returns:
            中文译文
        """
        if not text or not text.strip():
            return ""

        self._load_model()

        # opus-mt 模型按句翻译效果更好，按句号分句
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
        if not sentences:
            return ""

        translated_parts = []
        for sent in sentences:
            # MarianMT 要求的输入格式：">>{target_lang}<< {source_text}"
            inputs = self._tokenizer(
                sent, return_tensors="pt", padding=True, truncation=True, max_length=512
            )
            outputs = self._model.generate(**inputs, max_length=512)
            translated = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
            translated_parts.append(translated)

        return "。".join(translated_parts) + "。"

    def translate_batch(self, paragraphs: list[str]) -> list[str]:
        """
        批量翻译段落列表。

        Args:
            paragraphs: 英文段落列表

        Returns:
            中文译文列表（顺序对应）
        """
        return [self.translate(p) for p in paragraphs]


# 全局单例
translation_service = TranslationService()
