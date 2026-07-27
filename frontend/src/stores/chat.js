import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getPreset } from '@/api/prompts'
import apiClient from '@/api'

export const useChatStore = defineStore('chat', () => {
  const sessionId = ref(null)
  const mode = ref('single')
  const messages = ref([])
  const isStreaming = ref(false)
  const inputText = ref('')
  const reasoningEffort = ref('medium')
  const activePresetId = ref(null)
  const sessions = ref([])

  const activePreset = computed(() =>
    activePresetId.value ? getPreset(activePresetId.value) : null
  )

  let abortController = null

  // ===== 会话管理 =====

  async function fetchSessions(paperId = null) {
    try {
      const params = { mode: mode.value }
      if (mode.value === 'single' && paperId) params.paper_id = paperId
      const res = await apiClient.get('/chat/sessions', { params })
      if (res.code === 0) sessions.value = res.data || []
      return sessions.value
    } catch (e) {
      console.error('获取会话列表失败:', e)
      return []
    }
  }

  // 切换到论文时：加载该论文的会话列表 + 自动打开最近一次
  async function switchToPaper(paperId) {
    clearMessages()
    const list = await fetchSessions(paperId)
    if (list.length > 0) {
      await loadSession(list[0].id)
    }
  }

  async function createSession(title, paperId) {
    try {
      const res = await apiClient.post('/chat/sessions', {
        title: title || '新对话',
        paper_id: paperId || null,
        mode: mode.value,
      })
      if (res.code === 0 && res.data?.id) {
        sessionId.value = res.data.id
        sessions.value.unshift(res.data)
        return res.data.id
      }
    } catch (e) {
      console.error('创建会话失败:', e)
    }
    return null
  }

  async function loadSession(id) {
    try {
      const res = await apiClient.get(`/chat/sessions/${id}`)
      if (res.code === 0) {
        messages.value = (res.data || []).map(m => ({
          id: m.id,
          role: m.role,
          content: m.content,
          sources: m.sources || [],
          timestamp: m.created_at,
        }))
        sessionId.value = id
      }
    } catch (e) {
      console.error('加载会话失败:', e)
    }
  }

  async function deleteSession(id) {
    try {
      await apiClient.delete(`/chat/sessions/${id}`)
      sessions.value = sessions.value.filter(s => s.id !== id)
      if (sessionId.value === id) {
        sessionId.value = null
        messages.value = []
      }
    } catch (e) {
      console.error('删除会话失败:', e)
    }
  }

  // ===== 消息操作 =====

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
    if (last && last.role === 'assistant') last.content += chunk
  }

  function setSources(sources) {
    const last = messages.value.at(-1)
    if (last && last.role === 'assistant') last.sources = sources
  }

  async function sendMessage(text, paperId = null, selectedText = null, paperIds = null) {
    if (isStreaming.value || !text.trim()) return

    addMessage('user', text.trim())
    inputText.value = ''

    // 首次发送时创建会话
    if (!sessionId.value) {
      await createSession(text.slice(0, 50), paperId)
      if (!sessionId.value) return
    }

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
          session_id: sessionId.value ? String(sessionId.value) : null,
          mode: mode.value,
          reasoning_effort: reasoningEffort.value,
          preset_id: activePresetId.value,
          paper_ids: paperIds,
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
            try {
              const event = JSON.parse(line.slice(6))
              if (event.type === 'chunk') updateLastAssistantMessage(event.content)
              else if (event.type === 'sources') setSources(event.sources || [])
              else if (event.type === 'done') sessionId.value = event.session_id || null
              else if (event.type === 'error') updateLastAssistantMessage(`\n\n[错误] ${event.message}`)
            } catch {}
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
    // 刷新会话列表
    fetchSessions(paperId)
  }

  function clearMessages() {
    if (abortController) { abortController.abort(); abortController = null }
    messages.value = []
    sessionId.value = null
    isStreaming.value = false
  }

  function newChat() {
    clearMessages()
  }

  function setMode(m) {
    mode.value = m
    const preset = getPreset(activePresetId.value)
    if (preset && !preset.modes.includes(m)) activePresetId.value = null
  }

  function setReasoningEffort(level) { reasoningEffort.value = level }
  function setPreset(presetId) {
    if (activePresetId.value === presetId) { activePresetId.value = null; return }
    activePresetId.value = presetId
    const preset = getPreset(presetId)
    if (preset && !preset.modes.includes(mode.value)) mode.value = preset.modes[0]
  }
  function clearPreset() { activePresetId.value = null }

  return {
    sessionId, mode, messages, isStreaming, inputText,
    reasoningEffort, activePresetId, activePreset, sessions,
    addMessage, sendMessage, clearMessages, newChat,
    setMode, setReasoningEffort, setPreset, clearPreset,
    fetchSessions, loadSession, createSession, deleteSession, switchToPaper,
  }
})
