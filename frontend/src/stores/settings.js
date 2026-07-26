import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '@/api'

const CACHE_KEY = 'papermind-llm-config'

export const useSettingsStore = defineStore('settings', () => {
  const llmConfig = ref({
    base_url: '',
    api_key: '',
    model: '',
    temperature: 0.7,
    max_tokens: 4096,
  })

  const isConfigured = ref(false)
  const connectionStatus = ref('unknown')

  // ===== 本地缓存 =====
  function saveToCache(config) {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(config))
    } catch { /* ignore */ }
  }

  function loadFromCache() {
    try {
      const raw = localStorage.getItem(CACHE_KEY)
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed.base_url || parsed.api_key || parsed.model) {
          llmConfig.value = { ...llmConfig.value, ...parsed }
          isConfigured.value = !!(parsed.base_url && parsed.api_key && parsed.model)
        }
      }
    } catch { /* ignore */ }
  }

  // ===== 保存：同时写 API + 本地缓存 =====
  async function saveConfig(config) {
    const full = { ...llmConfig.value, ...config }
    llmConfig.value = full
    isConfigured.value = !!(full.base_url && full.api_key && full.model)

    // 本地缓存（存完整密钥）
    saveToCache(full)

    // API 持久化
    return apiClient.put('/settings/llm', full).catch((err) => {
      console.error('API 保存失败，仅本地缓存:', err)
    })
  }

  // ===== 加载：本地缓存优先（有完整密钥），API 补充其他字段 =====
  function loadConfig() {
    // 1. 先从本地缓存恢复（有完整密钥）
    loadFromCache()

    // 2. 再从 API 同步（api_key 是脱敏的，所以只用 API 验证配置是否存在）
    apiClient.get('/settings/llm').then((res) => {
      if (res.code === 0 && res.data) {
        // API 返回的 base_url/model 可能更新，覆盖
        if (res.data.base_url) llmConfig.value.base_url = res.data.base_url
        if (res.data.model) llmConfig.value.model = res.data.model
        if (res.data.temperature != null) llmConfig.value.temperature = res.data.temperature
        if (res.data.max_tokens != null) llmConfig.value.max_tokens = res.data.max_tokens
        // api_key 优先用本地缓存（完整），只有本地没有时用 API 的
        if (!llmConfig.value.api_key && res.data.api_key) {
          llmConfig.value.api_key = res.data.api_key
        }
        isConfigured.value = !!(llmConfig.value.base_url && llmConfig.value.api_key && llmConfig.value.model)
      }
    }).catch(() => {
      loadFromCache() // 回退
    })
  }

  // ===== 测试连接 =====
  async function testConnection() {
    connectionStatus.value = 'testing'
    try {
      const res = await apiClient.post('/settings/llm/test', {
        base_url: llmConfig.value.base_url,
        api_key: llmConfig.value.api_key,
        model: llmConfig.value.model,
      })
      if (res.code === 0 && res.data?.ok) {
        connectionStatus.value = 'connected'
      } else {
        connectionStatus.value = 'failed'
      }
    } catch {
      connectionStatus.value = 'failed'
    }
    setTimeout(() => { connectionStatus.value = 'unknown' }, 3000)
  }

  // 初始化
  loadConfig()

  return { llmConfig, isConfigured, connectionStatus, saveConfig, loadConfig, testConnection }
})
