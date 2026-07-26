# PaperMind API 设计规范

## 设计原则

1. **RESTful 风格**：资源 URL 用复数名词
2. **统一响应格式**：`{ code: 0, message: "success", data: {...} }`
3. **流式接口**：AI 生成类接口使用 SSE（Server-Sent Events）
4. **分页**：列表类接口默认分页

---

## 接口列表

### 通用响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

错误：
```json
{
  "code": 40001,
  "message": "文件格式不支持，请上传 PDF 文件",
  "data": null
}
```

---

### Settings — 模型配置

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/settings/llm` | 获取当前 LLM 配置（API Key 脱敏） |
| PUT | `/api/settings/llm` | 保存 LLM 配置 |
| POST | `/api/settings/llm/test` | 测试 LLM 连接 |

**PUT /api/settings/llm**
```json
{
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-xxx",
  "model": "gpt-4o",
  "temperature": 0.7,
  "max_tokens": 4096
}
```

---

### Papers — 论文管理

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/papers` | 论文列表（分页，支持 folder_id 筛选） |
| POST | `/api/papers/upload` | 上传 PDF |
| GET | `/api/papers/{id}` | 论文详情（含解析文本） |
| PUT | `/api/papers/{id}` | 更新论文元数据（含移动到文件夹） |
| DELETE | `/api/papers/{id}` | 删除论文及向量索引 |
| GET | `/api/papers/{id}/segments` | 获取论文文本段落（用于前端展示和划词） |

**POST /api/papers/upload** (multipart/form-data)
- `file`: PDF 文件
- `folder_id`: int | null，目标文件夹 ID
- `enable_ai_enhance`: bool，是否启用 unstructured.io AI 增强

**响应**：
```json
{
  "code": 0,
  "message": "上传成功",
  "data": {
    "id": 1,
    "title": "Attention Is All You Need",
    "authors": ["Vaswani, Ashish", ...],
    "year": 2017,
    "abstract": "...",
    "page_count": 15,
    "status": "indexed"
  }
}
```

---

### Folders — 文件夹管理

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/folders` | 文件夹列表（树结构） |
| POST | `/api/folders` | 创建文件夹 |
| PUT | `/api/folders/{id}` | 重命名文件夹 |
| DELETE | `/api/folders/{id}` | 删除文件夹 |
| PUT | `/api/papers/{id}/move` | 移动论文到指定文件夹 |

**GET /api/folders** 响应：
```json
{
  "code": 0,
  "data": [
    { "id": 0, "name": "全部论文", "paper_count": 42, "is_default": true },
    { "id": 1, "name": "NLP", "paper_count": 15 },
    { "id": 2, "name": "Computer Vision", "paper_count": 10 }
  ]
}
```

**PUT /api/papers/{id}/move**
```json
{
  "folder_id": 1
}
```

---

### Embedding — 向量模型

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/embedding/status` | 检查 Embedding 模型部署状态 |
| POST | `/api/embedding/deploy` | 部署（下载）Embedding 模型 |

**GET /api/embedding/status**
```json
{
  "code": 0,
  "data": { "deployed": true, "model_name": "sentence-transformers/all-MiniLM-L6-v2", "model_size": "~90 MB" }
}
```

---

### Translation — 论文翻译

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/translation/status` | 检查翻译模型部署状态 |
| POST | `/api/translation/deploy` | 部署（下载）翻译模型 |
| POST | `/api/translation/translate` | 翻译段落列表（EN → ZH） |

**GET /api/translation/status**
```json
{
  "code": 0,
  "data": { "deployed": true, "model_name": "Helsinki-NLP/opus-mt-en-zh" }
}
```

**POST /api/translation/deploy**
```json
{
  "code": 0,
  "data": { "status": "deployed", "message": "模型部署成功" }
}
```

**POST /api/translation/translate**
```json
// Request
{
  "paragraphs": [
    "The dominant sequence transduction models are based on...",
    "We propose a new simple network architecture..."
  ]
}

// Response
{
  "code": 0,
  "data": {
    "translations": [
      "主要的序列转导模型基于...",
      "我们提出了一种新的简单网络架构..."
    ]
  }
}
```

---

### Chat — 对话

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chat/ask` | RAG 问答（SSE 流式） |
| POST | `/api/chat/summarize` | 生成论文摘要（SSE 流式） |
| POST | `/api/chat/compare` | 论文对比分析（SSE 流式） |
| GET | `/api/chat/sessions` | 对话历史列表 |
| GET | `/api/chat/sessions/{id}` | 某次对话的完整消息 |

**POST /api/chat/ask**
```json
{
  "question": "本文的主要贡献是什么？",
  "paper_id": 1,
  "selected_text": "Transformer is the first transduction model...",
  "session_id": "uuid-or-null",
  "mode": "single"
}
```

| 参数 | 说明 |
|---|---|
| `paper_id` | 单篇模式时指定论文 ID，全局模式为 null |
| `selected_text` | 划词提问时传入的选中文本，自由提问为 null |
| `session_id` | 继续已有会话时传入，新会话为 null |
| `mode` | `"single"` / `"global"` |

**SSE 响应流**（text/event-stream）：
```
data: {"type": "chunk", "content": "本文"}

data: {"type": "chunk", "content": "的主要"}

data: {"type": "sources", "sources": [{"paper_id": 1, "title": "...", "chunk_text": "...", "page": 3}]}

data: {"type": "done", "session_id": "uuid"}
```

**POST /api/chat/summarize**
```json
{
  "paper_id": 1,
  "language": "zh"
}
```

**POST /api/chat/compare**
```json
{
  "paper_ids": [1, 2, 3],
  "language": "zh"
}
```

---

### 分页规范

请求参数：`page` (default=1), `page_size` (default=20, max=100)

分页响应：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

---

## HTTP 状态码

| 状态码 | 使用场景 |
|---|---|
| 200 | 请求成功 |
| 201 | 创建/上传成功 |
| 204 | 删除成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 413 | 文件过大 |
| 422 | 参数校验失败 |
| 500 | 服务器内部错误 |
