<template>
  <Teleport to="body">
    <div v-if="visible" class="dialog-overlay" @click.self="$emit('close')">
      <div class="dialog upload-dialog">
        <div class="dialog-header">
          <h3>上传论文</h3>
          <button class="btn-ghost btn-sm" @click="$emit('close')">✕</button>
        </div>

        <div class="dialog-body">
          <!-- 拖拽区域 -->
          <div
            class="drop-zone"
            :class="{ dragover: isDragover }"
            @dragover.prevent="isDragover = true"
            @dragleave.prevent="isDragover = false"
            @drop.prevent="handleDrop"
            @click="openFilePicker"
          >
            <div v-if="!selectedFile">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="drop-icon">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <p>拖拽 PDF 文件到此处</p>
              <p class="drop-hint">或点击选择文件</p>
            </div>
            <div v-else class="file-selected">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <span class="file-name">{{ selectedFile.name }}</span>
              <span class="file-size">{{ formatSize(selectedFile.size) }}</span>
              <button class="btn-ghost btn-sm" @click.stop="selectedFile = null">移除</button>
            </div>
          </div>
          <input ref="fileInput" type="file" accept=".pdf" style="display:none" @change="onFilePicked" />

          <!-- Embedding 状态（仅在未部署时提示） -->
          <p v-if="!embeddingChecking && embeddingStatus === 'not_deployed'" class="ai-warning">
            ⚠️ Embedding 模型尚未部署（~90MB），上传论文前请先在<a href="/settings" @click.prevent="$router.push('/settings')" style="color: var(--color-accent); font-weight: 600;">设置页</a>部署，否则上传可能失败。
          </p>

          <!-- AI 增强选项 -->
          <label class="checkbox-label">
            <input type="checkbox" v-model="enableAI" />
            <span>启用 AI 增强语义解析</span>
          </label>
          <p v-if="enableAI" class="ai-warning">
            ⚠️ 此选项将调用大模型 API 进行语义分割，会消耗额外的 tokens。建议仅对需要解析公式、图标的重要论文使用。
          </p>
        </div>

        <!-- 上传进度 -->
        <div v-if="uploading" class="upload-progress-area">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: uploadPercent + '%' }"></div>
          </div>
          <p class="progress-step">{{ uploadStep }}</p>
        </div>

        <div v-if="uploadError" class="upload-error">{{ uploadError }}</div>

        <div class="dialog-footer">
          <button class="btn btn-secondary" @click="$emit('close')">取消</button>
          <button class="btn btn-primary" :disabled="!selectedFile || uploading" @click="handleUpload">
            {{ uploading ? '上传中...' : '上传' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 上传进度独立弹窗 -->
    <div v-if="uploading" class="progress-overlay">
      <div class="progress-dialog">
        <h4>正在上传论文</h4>
        <div class="progress-bar"><div class="progress-fill" :style="{ width: uploadPercent + '%' }"></div></div>
        <p class="progress-step">{{ uploadStep }}</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import apiClient from '@/api'
import { usePapersStore } from '@/stores/papers'

const props = defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'uploaded'])

const papers = usePapersStore()

const isDragover = ref(false)
const selectedFile = ref(null)
const enableAI = ref(false)
const uploading = ref(false)
const uploadError = ref('')
const uploadStep = ref('')
const uploadPercent = ref(0)
const fileInput = ref(null)
const embeddingStatus = ref('checking')
const embeddingChecking = ref(false)

// 对话框打开时检查 embedding 状态
watch(
  () => props.visible,
  async (v) => {
    if (v) {
      uploadError.value = ''
      uploadStep.value = ''
      uploadPercent.value = 0
      // 检查 embedding
      embeddingChecking.value = true
      embeddingStatus.value = 'checking'
      try {
        const res = await apiClient.get('/embedding/status')
        if (res.code === 0) {
          embeddingStatus.value = res.data?.deployed ? 'deployed' : 'not_deployed'
        } else {
          embeddingStatus.value = 'not_deployed'
        }
      } catch (e) {
        console.error('Embedding 状态检查失败:', e)
        embeddingStatus.value = 'check_error'
      }
      embeddingChecking.value = false
    }
  }
)

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

function openFilePicker() {
  fileInput.value?.click()
}

function onFilePicked(e) {
  const file = e.target.files[0]
  if (file && file.type === 'application/pdf') {
    selectedFile.value = file
    uploadError.value = ''
  }
}

function handleDrop(e) {
  isDragover.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.type === 'application/pdf') {
    selectedFile.value = file
    uploadError.value = ''
  }
}

async function handleUpload() {
  if (!selectedFile.value) return
  uploading.value = true
  uploadError.value = ''
  uploadPercent.value = 0

  uploadStep.value = '正在保存 PDF 文件...'
  uploadPercent.value = 5

  const file = selectedFile.value
  emit('close')

  const steps = [
    { pct: 15,  text: '正在提取文本与标题结构...' },
    { pct: 30,  text: '正在识别段落与章节边界...' },
    { pct: 50,  text: '正在将论文切分为语义片段...' },
    { pct: 70,  text: '正在生成向量索引（本地 Embedding 模型）...' },
    { pct: 85,  text: '正在保存解析结果...' },
  ]
  let stepIdx = 0

  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('enable_ai_enhance', enableAI.value)

    const timer = setInterval(() => {
      if (stepIdx < steps.length && uploadPercent.value >= steps[stepIdx].pct) {
        uploadStep.value = steps[stepIdx].text
        stepIdx++
      }
      if (uploadPercent.value < 85) uploadPercent.value += 2
    }, 400)

    const res = await apiClient.post('/papers/upload', formData, {
      params: { folder_id: papers.currentFolderId },
      timeout: 120000,
    })

    clearInterval(timer)

    if (res.code === 0 && res.data) {
      uploadStep.value = '解析完成，论文已加入文库'
      uploadPercent.value = 100

      papers.addPaper({
        id: res.data.id,
        title: res.data.title,
        authors: res.data.authors || [],
        year: res.data.year,
        folderId: res.data.folder_id,
        abstract: res.data.abstract || '',
        createdAt: res.data.created_at,
      })

      papers.fetchFolders()

      setTimeout(() => {
        uploading.value = false
        emit('uploaded')
      }, 800)
    } else {
      uploadStep.value = res.message || '上传失败'
      setTimeout(() => { uploading.value = false }, 2000)
    }
  } catch (err) {
    console.error('上传失败:', err)
    uploadStep.value = err.response?.data?.message || err.message || '上传失败'
    setTimeout(() => { uploading.value = false }, 2000)
  }
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}

.dialog {
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 480px;
  max-width: 90vw;
  overflow: hidden;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}
.dialog-header h3 { font-size: 16px; font-weight: 600; }

.dialog-body { padding: 20px; }

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  padding: 32px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition);
  color: var(--color-text-secondary);
  font-size: 14px;
}
.drop-zone:hover, .drop-zone.dragover {
  border-color: var(--color-accent);
  background: var(--color-accent-light);
}
.drop-hint { font-size: 12px; color: var(--color-text-muted); margin-top: 4px; }
.drop-icon { color: var(--color-text-muted); margin-bottom: 8px; }

.file-selected {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--color-text-primary);
}
.file-name { font-weight: 500; }
.file-size { font-size: 12px; color: var(--color-text-muted); }

.form-group {
  margin-top: 16px;
}
.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--color-text-secondary);
}
.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-input);
  color: var(--color-text-primary);
  font-size: 13px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
}
.checkbox-label input[type="checkbox"] { accent-color: var(--color-accent); }

.ai-warning {
  margin-top: 8px;
  padding: 8px 12px;
  background: #fef7e0;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: #b06000;
  line-height: 1.5;
}
.dark .ai-warning { background: #3d2e00; color: #fdd663; }

.upload-error {
  margin: 0 20px 8px;
  padding: 8px 12px;
  background: #fce8e6;
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: #d93025;
}
.dark .upload-error { background: #3d0000; color: #f28b82; }

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
}

.progress-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
}
.progress-dialog {
  background: var(--color-bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 380px; max-width: 90vw;
  padding: 32px 28px; text-align: center;
}
.progress-dialog h4 { font-size: 15px; font-weight: 600; margin-bottom: 16px; }
.progress-bar { height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--color-accent); border-radius: 3px; transition: width 0.5s ease; width: 0; }
.progress-step { margin-top: 10px; font-size: 13px; color: var(--color-text-secondary); }
</style>
