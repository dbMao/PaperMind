import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getPreset } from '@/api/prompts'

export const useChatStore = defineStore('chat', () => {
  const sessionId = ref(null)
  const mode = ref('single')
  const messages = ref([])
  const isStreaming = ref(false)
  const inputText = ref('')
  const reasoningEffort = ref('medium')
  const activePresetId = ref(null)

  const activePreset = computed(() =>
    activePresetId.value ? getPreset(activePresetId.value) : null
  )

  // AbortController for cancelling SSE streams
  let abortController = null

  function addMessage(role, content, sources = []) {
    messages.value.push({
      id: Date.now(),
      role,
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

    abortController = new AbortController()

    try {
      const response = await fetch('/api/chat/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: text.trim(),
          paper_id: paperId,
          selected_text: selectedText,
          session_id: sessionId.value,
          mode: mode.value,
          reasoning_effort: reasoningEffort.value,
          preset_id: activePresetId.value,
          paper_ids: null,
        }),
        signal: abortController.signal,
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6)
            try {
              const event = JSON.parse(jsonStr)

              if (event.type === 'chunk') {
                updateLastAssistantMessage(event.content)
              } else if (event.type === 'sources') {
                setSources(event.sources || [])
              } else if (event.type === 'done') {
                sessionId.value = event.session_id || null
              } else if (event.type === 'error') {
                updateLastAssistantMessage(`\n\n[错误] ${event.message}`)
              }
            } catch {
              // 非 JSON 行，可能是注释，跳过
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('SSE 流错误:', err)
        updateLastAssistantMessage(`\n\n[连接错误] ${err.message}`)
      }
    }

    isStreaming.value = false
    abortController = null
  }

  function clearMessages() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    messages.value = []
    sessionId.value = null
    isStreaming.value = false
  }

  function setMode(m) {
    mode.value = m
    const preset = getPreset(activePresetId.value)
    if (preset && !preset.modes.includes(m)) {
      activePresetId.value = null
    }
  }

  function setReasoningEffort(level) {
    reasoningEffort.value = level
  }

  function setPreset(presetId) {
    if (activePresetId.value === presetId) {
      activePresetId.value = null
      return
    }
    activePresetId.value = presetId
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
