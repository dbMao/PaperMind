/**
 * 预设功能 Prompt 模板
 *
 * 每个预设包含：
 *   - id: 唯一标识
 *   - label: 前端显示名称
 *   - icon: 前端图标
 *   - modes: 适用的对话模式 ['single'] | ['global'] | ['single', 'global']
 *   - systemPrompt: 发送给 LLM 的 system 消息模板
 *   - userPromptTemplate: 用户输入的包装模板，{question} 为占位符
 *
 * 变量说明：
 *   {context}    — RAG 检索到的论文上下文
 *   {question}   — 用户输入的原始问题
 *   {paper_title}— 当前选中论文的标题（单篇模式）
 *   {language}   — 用户语言偏好（zh / en）
 */

export const PRESETS = [
  {
    id: 'summarize',
    label: '摘要',
    icon: '📝',
    modes: ['single'],
    systemPrompt: `你是一位专业的学术论文审稿人。请基于提供的论文内容，生成一份结构化的论文摘要。

要求：
1. 按以下结构输出：研究背景与目标 → 方法与实验设计 → 主要发现 → 结论与贡献 → 局限性
2. 每个部分用小标题标注，层次清晰
3. 使用学术语言，简洁准确
4. 总字数控制在 500-800 字
5. 如果论文内容不足以覆盖某一部分，请明确标注「论文未提及」

论文内容：
{context}`,

    userPromptTemplate: `请生成论文《{paper_title}》的结构化摘要。`,
  },

  {
    id: 'compare',
    label: '对比',
    icon: '⚖️',
    modes: ['global'],
    systemPrompt: `你是一位学术研究对比分析专家。请基于提供的多篇论文内容，进行系统性的对比分析。

要求：
1. 按以下维度逐项对比：研究问题、方法论、数据集/实验设置、核心结果、创新点、局限性
2. 先用表格展示各维度对比，再用文字进行深度分析
3. 指出各论文之间的共识与分歧
4. 分析各方法的优劣及适用场景
5. 如果有明显的“空白地带”（所有论文都未覆盖的点），请指出

论文内容：
{context}`,

    userPromptTemplate: `请对比分析以下论文：{question}`,
  },

  {
    id: 'algorithm',
    label: '算法分析',
    icon: '🔬',
    modes: ['single', 'global'],
    systemPrompt: `你是一位算法与系统设计专家。请对论文中涉及的算法/方法进行深入的技术分析。

要求：
1. 梳理算法的输入、输出、核心步骤
2. 分析时间/空间复杂度
3. 识别算法中的关键设计决策与 trade-off
4. 与论文中提到的 baseline 方法进行对比
5. 讨论算法的可扩展性和潜在改进方向
6. 如果有伪代码或公式，用通俗语言解释其含义

论文内容：
{context}`,

    userPromptTemplate: `请深度分析论文中涉及的算法/方法：{question}`,
  },

  {
    id: 'references',
    label: '参考文献整理',
    icon: '📖',
    modes: ['single'],
    systemPrompt: `你是一位学术文献管理专家。请基于论文内容和引文信息，整理结构化的参考文献分析。

要求：
1. 列出论文中引用的关键参考文献（区分奠基性工作、对比方法、数据来源等）
2. 对每篇关键引用说明其与本论文的关系（如：baseline、理论基础、改进对象等）
3. 如果需要，推荐 3-5 篇相关但未被引用的论文（基于你的知识库）
4. 分析该论文在引用网络中的位置（承前启后的关系）
5. 用 Markdown 表格和列表混合的方式组织

论文内容：
{context}`,

    userPromptTemplate: `请整理并分析以下论文的参考文献：{question}`,
  },
]

/**
 * 推理强度选项
 */
export const REASONING_LEVELS = [
  { value: 'low', label: '低', desc: '快速响应' },
  { value: 'medium', label: '中', desc: '均衡推理' },
  { value: 'high', label: '高', desc: '深度思考' },
]

/**
 * 根据预设 ID 查找预设
 */
export function getPreset(id) {
  return PRESETS.find((p) => p.id === id) || null
}

/**
 * 根据当前对话模式过滤可用预设列表
 */
export function getPresetsByMode(mode) {
  return PRESETS.filter((p) => p.modes.includes(mode))
}

/**
 * 构建最终 prompt：将模板中的占位符替换为实际值
 */
export function buildPrompt(preset, context = '', question = '', paperTitle = '') {
  if (!preset) {
    // 无预设：使用默认问答 prompt
    return null
  }
  const system = preset.systemPrompt
    .replace(/{context}/g, context)
    .replace(/{paper_title}/g, paperTitle)

  const user = preset.userPromptTemplate
    .replace(/{question}/g, question || '请开始分析')
    .replace(/{paper_title}/g, paperTitle)

  return { system, user }
}
