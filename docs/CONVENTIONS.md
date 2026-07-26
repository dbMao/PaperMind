# PaperMind 编码规范

---

## 通用规范

### 命名

| 类型 | 规则 | 示例 |
|---|---|---|
| 文件 | kebab-case (JS) / snake_case (Python) | `paper-library.vue` / `paper_service.py` |
| 目录 | kebab-case (JS) / 小写 (Python) | `views/` / `routes/` |
| Vue 组件 | PascalCase | `PaperLibrary.vue` |
| JS 函数 | camelCase | `getUserById` |
| Python 函数 | snake_case | `get_user_by_id` |
| 常量 | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` |
| CSS 类 | kebab-case | `.paper-library__item` |

### Git 提交

```
<type>(<scope>): <subject>

feat(paper): 添加论文上传功能
feat(chat): 实现流式 RAG 问答
fix(parser): 修复 PDF 表格提取
docs: 更新 API 文档
refactor(vector): 重构向量检索逻辑
```

类型：`feat` | `fix` | `docs` | `style` | `refactor` | `test` | `chore`

Scope：`paper` | `chat` | `parser` | `vector` | `config` | `ui`

### 分支策略

- `master` — 稳定主分支
- `feat/<功能名>` — 功能分支
- `fix/<修复名>` — 修复分支

---

## 前端规范 (Vue 3)

### 组件结构

```vue
<template>
  <!-- 模板 -->
</template>

<script setup>
// 组合式 API
</script>

<style scoped>
/* 组件样式 */
</style>
```

- 使用 `<script setup>` 语法 + Composition API
- 状态管理使用 Pinia
- 样式默认 `scoped`，全局样式放 `assets/`

### 目录约定

| 目录 | 用途 |
|---|---|
| `views/` | 页面级组件（对应路由） |
| `components/` | 可复用组件 |
| `api/` | API 调用函数（按模块拆分文件） |
| `router/` | 路由配置 |
| `stores/` | Pinia 状态管理 |
| `composables/` | 组合式函数（复用逻辑） |
| `utils/` | 工具函数 |

### SSE 流式接收

```js
// api/chat.js
export const askQuestion = (params, onChunk, onDone, onError) => {
  const url = '/api/chat/ask'
  // 使用 fetch + ReadableStream 处理 SSE
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  }).then(response => {
    const reader = response.body.getReader()
    // ... 逐行解析 SSE
  })
}
```

---

## 后端规范 (FastAPI)

### 项目结构

```
app/
├── main.py              # FastAPI 应用入口
├── core/
│   ├── config.py        # Pydantic Settings
│   └── llm.py           # LLM 工厂函数
├── api/routes/          # 路由模块，按资源拆分
├── models/              # Pydantic 请求/响应模型
├── services/            # 业务逻辑层（核心）
├── parsers/             # PDF 解析器
└── db/                  # 数据库
    ├── database.py      # SQLite 连接
    ├── models.py        # SQLAlchemy ORM
    └── chroma_client.py # ChromaDB 客户端
```

### 路由定义

```python
# api/routes/paper.py
from fastapi import APIRouter

router = APIRouter(prefix="/papers", tags=["Papers"])

@router.get("/")
async def list_papers(page: int = 1, page_size: int = 20):
    ...

@router.post("/upload")
async def upload_paper(file: UploadFile, enable_ai_enhance: bool = False):
    ...
```

### 模型约定

```python
# Request / Response models
class PaperCreate(BaseModel):
    """创建论文的请求体"""
    title: str

class PaperResponse(BaseModel):
    """论文响应模型"""
    id: int
    title: str
    authors: list[str] = []
    year: int | None = None

    model_config = ConfigDict(from_attributes=True)
```

### Service 层设计

```python
# services/parser_service.py
class ParserService:
    """PDF 解析调度服务"""
    def __init__(self, llm_config: dict | None = None):
        self.pymupdf_parser = PyMuPDFParser()
        self.table_parser = PdfPlumberParser()
        self.ai_parser = UnstructuredParser(llm_config) if llm_config else None

    def parse(self, file_path: str, enable_ai: bool = False) -> ParsedDocument:
        text = self.pymupdf_parser.extract(file_path)
        if self.pymupdf_parser.has_tables(file_path):
            tables = self.table_parser.extract_tables(file_path)
        if enable_ai and self.ai_parser:
            enhanced = self.ai_parser.segment(file_path)
        ...
```

---

## LangChain 使用规范

### LLM 实例化

```python
# core/llm.py
from langchain_openai import ChatOpenAI

def create_llm(config: LLMConfig) -> ChatOpenAI:
    """根据用户配置创建 LLM 实例"""
    return ChatOpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        streaming=True,
    )
```

### Embedding

```python
from langchain_huggingface import HuggingFaceEmbeddings

# 全局单例
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)
```

### RAG Prompt 模板

```python
from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = """你是一个论文阅读助手。请基于以下论文内容回答用户的问题。

要求：
1. 仅在提供的论文内容范围内作答
2. 如果论文内容不足以回答问题，请明确说明
3. 回答时引用具体的段落来源
4. 使用中文回答（除非用户要求用英文）

论文内容：
{context}
"""

qa_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{question}"),
])
```

### 向量检索

```python
# services/vector_service.py
from langchain_chroma import Chroma

class VectorService:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.store = Chroma(
            embedding_function=embeddings,
            persist_directory=persist_dir,
        )

    def search(self, query: str, paper_id: int | None = None, k: int = 5):
        filter = {"paper_id": paper_id} if paper_id else None
        return self.store.similarity_search(query, k=k, filter=filter)
```

### 文档切分（Section-based Chunking）

```python
# services/chunking_service.py
import tiktoken

class ChunkingService:
    """基于论文节标题的语义切分"""

    MAX_TOKENS = 1500       # 单 chunk 上限
    MIN_TOKENS = 200        # 短节合并阈值
    OVERLAP_TOKENS = 200    # 超长节切分时的重叠
    ENCODING = "cl100k_base"

    def __init__(self):
        self.tokenizer = tiktoken.get_encoding(self.ENCODING)

    def chunk_document(self, sections: list[Section], paper_meta: dict) -> list[Chunk]:
        """
        sections: PyMuPDF 解析后的节列表，每个 Section 包含:
            - title: 节标题（如 "3. Model Architecture"）
            - level: 标题层级（1/2/3）
            - content: 节正文
            - page_start: 起始页码
        """
        chunks = []
        buffer = []  # 短节缓冲区

        for section in sections:
            token_count = len(self.tokenizer.encode(section.content))

            if token_count < self.MIN_TOKENS:
                # 短节 → 放入缓冲区，尝试与相邻节合并
                buffer.append(section)
                buffered_tokens = sum(
                    len(self.tokenizer.encode(s.content)) for s in buffer
                )
                if buffered_tokens >= self.MIN_TOKENS:
                    chunks.append(self._merge_sections(buffer, paper_meta))
                    buffer = []
            elif token_count > self.MAX_TOKENS:
                # 长节 → 先清空缓冲区，再对当前节二次切分
                if buffer:
                    chunks.append(self._merge_sections(buffer, paper_meta))
                    buffer = []
                chunks.extend(
                    self._split_long_section(section, paper_meta)
                )
            else:
                # 合适长度 → 先清空缓冲区，再独立成 chunk
                if buffer:
                    chunks.append(self._merge_sections(buffer, paper_meta))
                    buffer = []
                chunks.append(self._section_to_chunk(section, paper_meta))

        # 处理末尾残留的短节
        if buffer:
            chunks.append(self._merge_sections(buffer, paper_meta))

        return chunks

    def _split_long_section(self, section: Section, meta: dict) -> list[Chunk]:
        """按段落边界切分超长节，保留 overlap"""
        ...

    def _merge_sections(self, sections: list[Section], meta: dict) -> Chunk:
        """合并多个短节为一个 chunk"""
        ...

    def _section_to_chunk(self, section: Section, meta: dict) -> Chunk:
        return Chunk(
            text=section.content,
            metadata={
                "paper_id": meta["paper_id"],
                "title": meta["title"],
                "section": section.title,
                "heading_level": section.level,
                "page": section.page_start,
                "chunk_index": -1,  # 由调用方赋值
            },
        )
```

### 对比检索（Two-Round Retrieval）

```python
# services/compare_service.py

class CompareService:
    def __init__(self, vector_service: VectorService):
        self.vector = vector_service

    def retrieve_for_compare(
        self, query: str, paper_ids: list[int], m: int = 10, n: int = 5
    ) -> list[Document]:
        """两轮检索 — 论文对比场景专用"""

        # 第一轮：全局检索
        round1_results = self.vector.search(
            query=query,
            paper_id=None,  # 不限论文
            k=m,
        )

        # 记录第一轮命中的论文
        hit_paper_ids = set(r.metadata["paper_id"] for r in round1_results)

        # 确保所有用户选中的论文都被覆盖
        targeted_ids = set(paper_ids) | hit_paper_ids

        # 第二轮：对每篇命中论文单独补充检索
        round2_results = []
        for pid in targeted_ids:
            results = self.vector.search(
                query=query,
                paper_id=pid,
                k=n,
            )
            round2_results.extend(results)

        # 合并去重（按 chunk 文本 hash）
        all_results = round1_results + round2_results
        seen = set()
        deduped = []
        for doc in all_results:
            doc_hash = hash(doc.page_content)
            if doc_hash not in seen:
                seen.add(doc_hash)
                deduped.append(doc)

        # 按相关性排序（ChromaDB 默认已排序，保持原顺序）
        return deduped
```

---

## 前后端协作

### 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 错误码约定

| code | 含义 |
|---|---|
| 0 | 成功 |
| 40001 | 文件格式错误 |
| 40002 | 文件过大 |
| 40003 | API 配置无效 |
| 40004 | LLM 调用失败 |
| 40005 | 向量检索失败 |
| 40401 | 论文不存在 |
| 40402 | 会话不存在 |
