#!/usr/bin/env python3
"""
部署 Helsinki-NLP/opus-mt-en-zh 翻译模型到本地。

首次运行会从 HuggingFace 下载模型文件（约 300MB），
下载完成后模型存储在 backend/models/opus-mt-en-zh/ 目录。

使用方式:
    python scripts/deploy_opus_mt.py

依赖（需先安装）:
    pip install transformers torch sentencepiece
"""

import sys
from pathlib import Path

# 将 backend 目录加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.translation_service import translation_service


def main():
    print("=" * 50)
    print("  PaperMind — 翻译模型部署")
    print("  模型: Helsinki-NLP/opus-mt-en-zh")
    print("=" * 50)
    print()

    if translation_service.is_deployed:
        print("✅ 模型已部署，无需重复下载。")
        print(f"   路径: {translation_service.MODEL_DIR}")
        return

    print("📥 正在从 HuggingFace 下载模型（约 300MB）...")
    print("   首次下载可能需要几分钟，请耐心等待。")
    print()

    result = translation_service.deploy()

    if result["status"] == "deployed":
        print(f"✅ {result['message']}")
        print(f"   路径: {translation_service.MODEL_DIR}")
    else:
        print(f"❌ 部署失败: {result['message']}")
        print("   请检查网络连接或手动运行:")
        print("   pip install transformers torch sentencepiece")
        print("   python -c \"from transformers import MarianMTModel; MarianMTModel.from_pretrained('Helsinki-NLP/opus-mt-en-zh').save_pretrained('./models/opus-mt-en-zh')\"")
        sys.exit(1)


if __name__ == "__main__":
    main()
