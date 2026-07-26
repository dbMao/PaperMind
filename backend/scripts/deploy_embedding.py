#!/usr/bin/env python3
"""
部署 sentence-transformers/all-MiniLM-L6-v2 Embedding 模型到本地。

首次运行会从 HuggingFace 下载模型文件（约 90MB），
下载完成后模型存储在 backend/models/all-MiniLM-L6-v2/ 目录。

使用方式:
    python scripts/deploy_embedding.py

依赖（需先安装）:
    pip install sentence-transformers
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.embedding_service import embedding_service


def main():
    print("=" * 50)
    print("  PaperMind — Embedding 模型部署")
    print("  模型: sentence-transformers/all-MiniLM-L6-v2")
    print("=" * 50)
    print()

    if embedding_service.is_deployed:
        print("✅ Embedding 模型已部署，无需重复下载。")
        print(f"   路径: {embedding_service.MODEL_DIR}")
        return

    print("📥 正在从 HuggingFace 下载模型（约 90MB）...")
    print("   首次下载可能需要几分钟，请耐心等待。")
    print()

    result = embedding_service.deploy()

    if result["status"] == "deployed":
        print(f"✅ {result['message']}")
        print(f"   路径: {embedding_service.MODEL_DIR}")
    else:
        print(f"❌ 部署失败: {result['message']}")
        print("   请检查网络连接或手动运行:")
        print("   pip install sentence-transformers")
        print("   python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2').save('./models/all-MiniLM-L6-v2')\"")
        sys.exit(1)


if __name__ == "__main__":
    main()
