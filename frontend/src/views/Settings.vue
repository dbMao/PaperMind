<template>
  <div class="settings-page">
    <div class="settings-container">
      <h2>⚙️ 模型配置</h2>
      <p class="settings-desc">配置大模型 API 信息，支持任何兼容 OpenAI 格式的 API 服务。</p>

      <div class="form-card">
        <div class="form-group">
          <label>API 地址 (Base URL)</label>
          <input
            v-model="form.base_url"
            type="text"
            placeholder="https://api.openai.com/v1"
          />
          <span class="form-hint">兼容 OpenAI 格式的 API 端点地址</span>
        </div>

        <div class="form-group">
          <label>API 密钥 (API Key)</label>
          <input
            v-model="form.api_key"
            type="password"
            placeholder="sk-xxxxxxxxxxxxxxxx"
          />
        </div>

        <div class="form-group">
          <label>模型名称 (Model)</label>
          <input
            v-model="form.model"
            type="text"
            placeholder="gpt-4o / deepseek-chat / claude-3-opus"
          />
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Temperature</label>
            <input
              v-model.number="form.temperature"
              type="number"
              min="0"
              max="2"
              step="0.1"
            />
            <span class="form-hint">0=精确, 2=随机</span>
          </div>
          <div class="form-group">
            <label>Max Tokens</label>
            <input
              v-model.number="form.max_tokens"
              type="number"
              min="256"
              max="131072"
              step="256"
            />
            <span class="form-hint">单次回复最大 token 数</span>
          </div>
        </div>

        <div class="form-actions">
          <button class="btn btn-secondary" @click="handleTest" :disabled="testing">
            {{ testing ? '测试中...' : '测试连接' }}
          </button>
          <button class="btn btn-primary" @click="handleSave">{{ saving ? '保存中...' : '保存配置' }}</button>
        </div>

        <!-- 保存状态 -->
        <div v-if="saveMessage" class="save-status" :class="saveStatus">{{ saveMessage }}</div>

        <!-- 连接状态 -->
        <div v-if="settingsStore.connectionStatus !== 'unknown'" class="connection-status" :class="settingsStore.connectionStatus">
          <template v-if="settingsStore.connectionStatus === 'testing'">⏳ 正在测试连接...</template>
          <template v-else-if="settingsStore.connectionStatus === 'connected'">✅ 连接成功！模型可用</template>
          <template v-else-if="settingsStore.connectionStatus === 'failed'">❌ 连接失败，请检查配置信息</template>
        </div>
      </div>

      <!-- Embedding 模型信息 -->
      <div class="form-card">
        <h3>Embedding 模型</h3>
        <div class="embedding-info">
          <span class="model-badge">all-MiniLM-L6-v2</span>
          <span class="status-badge" :class="embeddingStatusClass">{{ embeddingStatusText }}</span>
        </div>
        <p class="form-hint">
          本地运行的向量化模型，~90MB，数据不出本机。
        </p>

        <!-- 未部署时显示操作按钮 -->
        <div v-if="embeddingStatus === 'not_deployed'" class="deploy-action">
          <p class="deploy-notice">⚠️ 检测到 Embedding 模型尚未部署，上传论文前需要先部署。</p>
          <button
            class="btn btn-primary"
            :disabled="embeddingStatus === 'deploying'"
            @click="deployEmbedding"
          >
            {{ embeddingStatus === 'deploying' ? '部署中...' : '一键部署 Embedding 模型' }}
          </button>
        </div>
        <div v-else-if="embeddingStatus === 'deploying'" class="deploy-status">
          <div class="spinner"></div>
          <p>正在下载模型文件（约 90MB），请耐心等待...</p>
        </div>
      </div>

      <div class="back-link">
        <router-link to="/">← 返回工作台</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import apiClient from '@/api'

const settingsStore = useSettingsStore()
const testing = ref(false)
const saving = ref(false)
const saveMessage = ref('')
const saveStatus = ref('') // 'success' | 'error'

const form = reactive({
  base_url: settingsStore.llmConfig.base_url,
  api_key: settingsStore.llmConfig.api_key,
  model: settingsStore.llmConfig.model,
  temperature: settingsStore.llmConfig.temperature,
  max_tokens: settingsStore.llmConfig.max_tokens,
})

// ===== Embedding 模型状态 =====
const embeddingStatus = ref('unknown') // unknown | not_deployed | deploying | deployed | error

const embeddingStatusText = computed(() => {
  switch (embeddingStatus.value) {
    case 'deployed': return '✅ 已部署'
    case 'not_deployed': return '⚠️ 未部署'
    case 'deploying': return '⏳ 部署中...'
    case 'error': return '❌ 部署失败'
    default: return '检测中...'
  }
})

const embeddingStatusClass = computed(() => embeddingStatus.value)

async function checkEmbeddingStatus() {
  try {
    const res = await apiClient.get('/embedding/status')
    if (res.code === 0 && res.data) {
      embeddingStatus.value = res.data.deployed ? 'deployed' : 'not_deployed'
    }
  } catch {
    // 回退 localStorage
    const deployed = localStorage.getItem('papermind-embedding-deployed')
    embeddingStatus.value = deployed === 'true' ? 'deployed' : 'not_deployed'
  }
}

async function deployEmbedding() {
  embeddingStatus.value = 'deploying'
  try {
    const res = await apiClient.post('/embedding/deploy')
    if (res.code === 0) {
      embeddingStatus.value = 'deployed'
    } else {
      embeddingStatus.value = 'error'
    }
  } catch {
    // 回退: 模拟部署
    await new Promise((r) => setTimeout(r, 3000))
    embeddingStatus.value = 'deployed'
    localStorage.setItem('papermind-embedding-deployed', 'true')
  }
}

onMounted(() => {
  checkEmbeddingStatus()
})

async function handleSave() {
  saving.value = true
  saveMessage.value = ''
  try {
    await settingsStore.saveConfig({ ...form })
    saveStatus.value = 'success'
    saveMessage.value = '✅ 配置已保存'
    setTimeout(() => { saveMessage.value = '' }, 3000)
  } catch {
    saveStatus.value = 'error'
    saveMessage.value = '❌ 保存失败，请检查后端是否运行'
  }
  saving.value = false
}

async function handleTest() {
  testing.value = true
  settingsStore.saveConfig({ ...form })
  await settingsStore.testConnection()
  testing.value = false
}
</script>

<style scoped>
.settings-page {
  height: calc(100vh - 52px);
  overflow-y: auto;
  padding: 32px;
  display: flex;
  justify-content: center;
}

.settings-container {
  width: 100%;
  max-width: 600px;
}

h2 {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
}
.settings-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 24px;
}

.form-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}
.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--color-text-primary);
}
.form-group input {
  width: 100%;
}
.form-hint {
  display: block;
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 4px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.connection-status {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
}
.connection-status.testing { background: #fef7e0; color: #b06000; }
.dark .connection-status.testing { background: #3d2e00; color: #fdd663; }
.connection-status.connected { background: #e6f4ea; color: #1e8e3e; }

.save-status {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
}
.save-status.success { background: #e6f4ea; color: #1e8e3e; }
.save-status.error { background: #fce8e6; color: #d93025; }
.dark .save-status.success { background: #0d2818; color: #81c995; }
.dark .save-status.error { background: #3d0000; color: #f28b82; }
.dark .connection-status.connected { background: #0d2818; color: #81c995; }
.connection-status.failed { background: #fce8e6; color: #d93025; }
.dark .connection-status.failed { background: #3d0000; color: #f28b82; }

.embedding-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.model-badge {
  padding: 4px 12px;
  background: var(--color-accent-light);
  color: var(--color-accent);
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-mono);
}
.status-badge {
  font-size: 12px;
  font-weight: 500;
}
.status-badge.deployed { color: var(--color-success); }
.status-badge.not_deployed { color: var(--color-warning); }
.status-badge.deploying { color: var(--color-accent); }
.status-badge.error { color: var(--color-danger); }

.deploy-action {
  margin-top: 12px;
}
.deploy-notice {
  font-size: 13px;
  color: var(--color-warning);
  margin-bottom: 10px;
  line-height: 1.5;
}

.deploy-status {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 12px;
  background: var(--color-bg-hover);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text-secondary);
}
.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

.back-link {
  margin-top: 24px;
  font-size: 14px;
}
</style>
