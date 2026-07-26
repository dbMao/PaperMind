import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSettingsStore = defineStore('settings', () => {
  const llmConfig = ref({
    base_url: '',
    api_key: '',
    model: '',
    temperature: 0.7,
    max_tokens: 4096,
  })

  const isConfigured = ref(false)
  const connectionStatus = ref('unknown') // 'unknown' | 'testing' | 'connected' | 'failed'

  function saveConfig(config) {
    llmConfig.value = { ...llmConfig.value, ...config }
    isConfigured.value = !!(config.base_url && config.api_key && config.model)
    // TODO: 调用 API 保存
    localStorage.setItem('papermind-llm-config', JSON.stringify(llmConfig.value))
  }

  function loadConfig() {
    const saved = localStorage.getItem('papermind-llm-config')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        llmConfig.value = { ...llmConfig.value, ...parsed }
        isConfigured.value = !!(parsed.base_url && parsed.api_key && parsed.model)
      } catch { /* ignore */ }
    }
  }

  async function testConnection() {
    connectionStatus.value = 'testing'
    // TODO: 调用 POST /api/settings/llm/test
    await new Promise((r) => setTimeout(r, 800))
    connectionStatus.value = 'connected'
    setTimeout(() => { connectionStatus.value = 'unknown' }, 3000)
  }

  // 初始化
  loadConfig()

  return { llmConfig, isConfigured, connectionStatus, saveConfig, loadConfig, testConnection }
})
