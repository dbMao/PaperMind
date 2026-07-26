# PaperMind 架构概览

## 项目定位

PaperMind —— 论文阅读 AI Agent。本地管理论文库，构建向量索引，通过大模型实现智能问答、摘要生成、论文对比。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Vite + Vue Router + Axios |
| 后端 | Python 3.12 + FastAPI + Pydantic |
| AI 框架 | LangChain（RAG pipeline、Agent 编排） |
| 大模型 | 用户自选，API 方式调用（OpenAI 兼容格式） |
| Embedding | all-MiniLM-L6-v2（本地运行） |
| 向量数据库 | ChromaDB |
| 业务数据库 | SQLite |
| PDF 解析 | PyMuPDF（主力）+ pdfplumber（表格）+ unstructured.io（可选 AI 增强） |

## 项目结构

```
PaperMind/
├── frontend/                       # Vue 3 前端
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── main.js                 # 应用入口
│       ├── App.vue                 # 根组件
│       ├── router/                 # 路由配置
│       │   └── index.js
│       ├── views/                  # 页面级组件
│       │   ├── Home.vue            # 主工作台（左右分栏）
│       │   └── Settings.vue        # 设置页（模型配置）
│       ├── components/             # 通用组件
│       │   ├── PaperLibrary.vue    # 论文库侧栏
│       │   ├── PaperViewer.vue     # 论文内容展示
│       │   ├── ChatPanel.vue       # 对话面板
│       │   └── UploadDialog.vue    # 上传对话框
│       ├── api/                    # API 调用封装
│       │   ├── index.js            # Axios 实例
│       │   ├── papers.js           # 论文相关 API
│       │   ├── chat.js             # 对话相关 API
│       │   └── settings.js         # 配置相关 API
│       ├── stores/                 # Pinia 状态管理
│       │   ├── papers.js           # 论文状态
│       │   ├── chat.js             # 对话状态
│       │   └── settings.js         # 配置状态
│       ├── composables/            # 组合式函数
│       └── assets/                 # 静态资源
│           └── main.css            # 全局样式
├── backend/                        # FastAPI 后端
│   ├── requirements.txt
│   ├── .env                        # 环境变量
│   └── app/
│       ├── main.py                 # 应用入口
│       ├── core/
│       │   ├── config.py           # 全局配置
│       │   └── llm.py              # LLM 工厂（动态模型创建）
│       ├── api/
│       │   └── routes/
│       │       ├── papers.py       # 论文管理路由
│       │       ├── chat.py         # 对话路由（RAG QA / 摘要 / 对比）
│       │       └── settings.py     # 配置路由（API Key 等）
│       ├── models/                 # Pydantic 模型
│       │       ├── paper.py
│       │       ├── chat.py
│       │       └── settings.py
│       ├── services/               # 业务逻辑层
│       │       ├── paper_service.py     # 论文 CRUD
│       │       ├── parser_service.py    # PDF 解析调度
│       │       ├── vector_service.py    # 向量索引管理
│       │       ├── rag_service.py       # RAG 核心逻辑
│       │       └── llm_service.py       # LLM 调用封装
│       ├── parsers/                # PDF 解析器
│       │       ├── base.py         # 解析器基类
│       │       ├── pymupdf_parser.py
│       │       ├── pdfplumber_parser.py
│       │       └── unstructured_parser.py
│       └── db/
│           ├── database.py         # SQLite 连接
│           ├── models.py           # SQLAlchemy 模型
│           └── chroma_client.py    # ChromaDB 客户端
└── docs/                           # 项目文档
    ├── ARCHITECTURE.md             # 架构说明（本文件）
    ├── SPECS.md                    # 功能规格
    ├── CONVENTIONS.md              # 编码规范
    ├── API.md                      # API 设计规范
    └── UI_LAYOUT.md                # 前端交互布局规范
```

## 数据流概览

```
用户上传 PDF
  → parser_service 调度解析器（PyMuPDF/pdfplumber/unstructured）
  → 提取文本 + 元数据
  → vector_service 切分文档 → embedding → 写入 ChromaDB
  → paper_service 存入 SQLite 元数据

用户提问
  → rag_service 将问题向量化 → ChromaDB 检索相关 chunk
  → LangChain 构建 prompt（问题 + 检索到的上下文 + 对话历史）
  → LLM 生成回答 → 返回前端（带引用来源）
```

## 开发运行

### 前端
```bash
cd frontend
npm run dev        # 端口 3000
```

### 后端
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 联调
Vite 配置 `/api` 代理 → `http://127.0.0.1:8000`。
