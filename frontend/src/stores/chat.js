import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getPreset } from '@/api/prompts'

export const useChatStore = defineStore('chat', () => {
  // 当前会话 ID
  const sessionId = ref(null)

  // 对话模式：single | global
  const mode = ref('single')

  // 消息列表
  const messages = ref([])

  // 是否正在生成回复
  const isStreaming = ref(false)

  // 输入框内容
  const inputText = ref('')

  // 推理强度：low | medium | high
  const reasoningEffort = ref('medium')

  // 当前选中的预设功能 ID（null = 无预设）
  const activePresetId = ref(null)

  // 当前预设对象（computed）
  const activePreset = computed(() =>
    activePresetId.value ? getPreset(activePresetId.value) : null
  )

  function addMessage(role, content, sources = []) {
    messages.value.push({
      id: Date.now(),
      role, // 'user' | 'assistant'
      content,
      sources,
      timestamp: new Date().toISOString(),
    })
  }

  function updateLastAssistantMessage(chunk) {
    const last = messages.value.at(-1)
    if (last && last.role === 'assistant') {
      last.content += chunk
    }
  }

  function setSources(sources) {
    const last = messages.value.at(-1)
    if (last && last.role === 'assistant') {
      last.sources = sources
    }
  }

  async function sendMessage(text, paperId = null, selectedText = null) {
    if (isStreaming.value || !text.trim()) return

    addMessage('user', text.trim())
    inputText.value = ''

    isStreaming.value = true
    addMessage('assistant', '')

    // TODO: 替换为真实 SSE 调用，携带以下参数：
    // {
    //   question: text.trim(),
    //   paper_id: paperId,
    //   selected_text: selectedText,
    //   session_id: sessionId.value,
    //   mode: mode.value,
    //   reasoning_effort: reasoningEffort.value,          // ← 推理强度
    //   preset_id: activePresetId.value,                   // ← 预设功能 ID
    // }

    // 模拟流式输出（后续替换为 SSE）
    const presetLabel = activePreset.value ? `[${activePreset.value.label}] ` : ''
    const reasoningLabel = `[推理强度: ${reasoningEffort.value}]`
    const mockResponse =
      `${presetLabel}${reasoningLabel}\n\n` +
      '基于您提供的论文内容，主要贡献如下：\n\n' +
      '1. 提出了全新的架构设计，摒弃了传统的循环神经网络结构\n' +
      '2. 引入了自注意力机制来捕捉序列中的长距离依赖关系\n' +
      '3. 在机器翻译任务上取得了当时最优的性能\n\n' +
      '该工作的核心创新在于将注意力机制作为唯一的建模手段，这为后续的预训练大模型奠定了基础。'

    let i = 0
    const streamInterval = setInterval(() => {
      if (i < mockResponse.length) {
        updateLastAssistantMessage(mockResponse[i])
        i++
      } else {
        clearInterval(streamInterval)
        setSources([
          { paper_id: 1, title: 'Attention Is All You Need', page: 3, chunk_text: 'We propose a new simple network architecture...' },
          { paper_id: 1, title: 'Attention Is All You Need', page: 5, chunk_text: 'The Transformer allows significantly more parallelization...' },
        ])
        isStreaming.value = false
      }
    }, 30)
  }

  function clearMessages() {
    messages.value = []
    sessionId.value = null
  }

  function setMode(m) {
    mode.value = m
    // 切换模式后，如果当前预设不支持新模式，自动清除
    const preset = getPreset(activePresetId.value)
    if (preset && !preset.modes.includes(m)) {
      activePresetId.value = null
    }
  }

  function setReasoningEffort(level) {
    reasoningEffort.value = level
  }

  function setPreset(presetId) {
    // 再次点击同一预设则取消选择
    if (activePresetId.value === presetId) {
      activePresetId.value = null
      return
    }
    activePresetId.value = presetId

    // 自动切换模式：如果预设不支持当前模式，切换到支持的模式
    const preset = getPreset(presetId)
    if (preset && !preset.modes.includes(mode.value)) {
      mode.value = preset.modes[0]
    }
  }

  function clearPreset() {
    activePresetId.value = null
  }

  return {
    sessionId,
    mode,
    messages,
    isStreaming,
    inputText,
    reasoningEffort,
    activePresetId,
    activePreset,
    addMessage,
    sendMessage,
    clearMessages,
    setMode,
    setReasoningEffort,
    setPreset,
    clearPreset,
  }
})
