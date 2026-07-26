<template>
  <div class="paper-viewer" v-if="paper">
    <!-- 论文元信息 -->
    <div class="viewer-header">
      <h1 class="paper-title">{{ paper.title }}</h1>
      <div class="paper-meta-row">
        <span class="paper-authors">{{ paper.authors.join(', ') }}</span>
        <span v-if="paper.year" class="paper-year">{{ paper.year }}</span>
      </div>
      <div class="viewer-actions">
        <button
          class="btn btn-secondary btn-sm"
          :class="{ active: translator.translationVisible }"
          @click="handleTranslationToggle"
        >
          🌐 {{ translator.translationVisible ? '隐藏翻译' : '显示翻译' }}
        </button>
      </div>
    </div>

    <!-- 论文摘要 -->
    <div class="paper-abstract" v-if="paper.abstract">
      <h3>摘要</h3>
      <p>{{ paper.abstract }}</p>
    </div>

    <!-- 正文 -->
    <div class="paper-body" ref="paperBodyRef">
      <!-- 普通模式 -->
      <template v-if="!translator.translationVisible">
        <p
          v-for="(para, i) in paragraphs"
          :key="i"
          class="paper-paragraph"
        >{{ para }}</p>
      </template>

      <!-- 翻译对照模式 -->
      <template v-else>
        <div v-if="translator.isTranslating" class="translation-progress">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: translator.progress + '%' }"></div>
          </div>
          <span class="progress-text">翻译中... {{ translator.progress }}%</span>
        </div>

        <div
          v-for="(para, i) in paragraphs"
          :key="i"
          class="translation-row"
        >
          <div class="translation-cell en">
            <span class="lang-tag">EN</span>
            <p>{{ para }}</p>
          </div>
          <div class="translation-cell zh">
            <span class="lang-tag">ZH</span>
            <p v-if="translations[i]">{{ translations[i] }}</p>
            <p v-else class="translating-hint">翻译中...</p>
          </div>
        </div>
      </template>
    </div>

    <!-- 模型部署对话框 -->
    <Teleport to="body">
      <div v-if="showDeployDialog" class="dialog-overlay" @click.self="showDeployDialog = false">
        <div class="dialog deploy-dialog">
          <div class="dialog-header">
            <h3>部署翻译模型</h3>
            <button class="btn-ghost btn-sm" @click="showDeployDialog = false">✕</button>
          </div>
          <div class="dialog-body">
            <div class="deploy-info">
              <div class="deploy-icon">🤖</div>
              <h4>Helsinki-NLP/opus-mt-en-zh</h4>
              <p class="deploy-desc">
                这是一个本地运行的英译中神经机器翻译模型，基于 MarianMT 架构。
              </p>
            </div>

            <div class="deploy-details">
              <div class="detail-item">
                <span class="detail-label">模型大小</span>
                <span class="detail-value">~300 MB</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">运行方式</span>
                <span class="detail-value">本地 CPU/GPU</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">隐私</span>
                <span class="detail-value">数据不出本地</span>
              </div>
            </div>

            <!-- 部署状态 -->
            <div v-if="deployState === 'deploying'" class="deploy-status">
              <div class="spinner"></div>
              <p>正在下载并部署模型，首次部署需下载约 300MB 文件，请耐心等待...</p>
            </div>
            <div v-else-if="deployState === 'error'" class="deploy-status error">
              <p>❌ 部署失败，请检查网络连接后重试。</p>
            </div>
          </div>
          <div class="dialog-footer">
            <button class="btn btn-secondary" @click="showDeployDialog = false">取消</button>
            <button
              class="btn btn-primary"
              :disabled="deployState === 'deploying'"
              @click="startDeploy"
            >
              {{ deployState === 'deploying' ? '部署中...' : '同意并部署' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 划词悬浮按钮 -->
    <Teleport to="body">
      <div
        v-if="selectionMenu.visible"
        class="selection-menu"
        :style="{ top: selectionMenu.y + 'px', left: selectionMenu.x + 'px' }"
      >
        <button @click="askSelection">💬 基于此提问</button>
      </div>
    </Teleport>
  </div>
  <div v-else class="viewer-empty">
    请选择一篇论文
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { usePapersStore } from '@/stores/papers'
import { useTranslatorStore } from '@/stores/translator'

const papers = usePapersStore()
const translator = useTranslatorStore()
const paper = computed(() => papers.selectedPaper)

defineEmits(['summarize', 'ask-selection'])

const showDeployDialog = ref(false)
const deployState = ref('idle') // idle | deploying | error

// 模拟正文段落（实际后续从 API 获取）
const paragraphs = computed(() => {
  if (!paper.value) return []
  // TODO: 从 GET /api/papers/{id}/segments 获取真实段落
  return [
    'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder.',
    'The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.',
    'Experiments on two machine translation tasks show that these models are superior in quality while being more parallelizable and requiring significantly less time to train.',
    'Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles, by over 2 BLEU.',
    'On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.0 after training for 3.5 days on eight GPUs.',
  ]
})

// 当前论文的翻译缓存
const translations = computed(() => {
  if (!paper.value) return {}
  return translator.translationCache[paper.value.id] || {}
})

// 点击「显示翻译」
async function handleTranslationToggle() {
  if (translator.translationVisible) {
    translator.toggleTranslation()
    return
  }

  // 检查模型是否已部署
  if (translator.modelStatus === 'unknown') {
    translator.checkModelStatus()
  }

  if (!translator.isModelReady) {
    deployState.value = 'idle'
    showDeployDialog.value = true
    return
  }

  // 模型已就绪，开启翻译
  translator.toggleTranslation()
  const pid = paper.value.id
  const cached = translator.getCachedTranslation(pid)
  if (!cached || Object.keys(cached).length === 0) {
    await translator.translatePaper(pid, paragraphs.value)
  }
}

async function startDeploy() {
  deployState.value = 'deploying'
  try {
    await translator.deployModel()
    deployState.value = 'idle'
    showDeployDialog.value = false
    // 部署成功后自动开启翻译
    translator.toggleTranslation()
    const pid = paper.value.id
    await translator.translatePaper(pid, paragraphs.value)
  } catch {
    deployState.value = 'error'
  }
}

// 划词菜单
const selectionMenu = reactive({ visible: false, x: 0, y: 0, text: '' })

function onMouseUp() {
  const sel = window.getSelection()
  const text = sel?.toString().trim()
  if (text && text.length > 0) {
    const range = sel.getRangeAt(0)
    const rect = range.getBoundingClientRect()
    selectionMenu.visible = true
    selectionMenu.x = rect.left + rect.width / 2 - 60
    selectionMenu.y = rect.bottom + 8
    selectionMenu.text = text
  } else {
    selectionMenu.visible = false
  }
}

function askSelection() {
  const event = new CustomEvent('paper-selection-ask', { detail: { text: selectionMenu.text } })
  window.dispatchEvent(event)
  selectionMenu.visible = false
  window.getSelection()?.removeAllRanges()
}

function onClickOutside() {
  selectionMenu.visible = false
}

onMounted(() => {
  document.addEventListener('mouseup', onMouseUp)
  document.addEventListener('click', onClickOutside)
})
onUnmounted(() => {
  document.removeEventListener('mouseup', onMouseUp)
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped>
.paper-viewer {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  background: var(--color-bg-primary);
}

.viewer-header {
  margin-bottom: 20px;
}

.paper-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.paper-meta-row {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}

.viewer-actions {
  display: flex;
  gap: 8px;
}
.viewer-actions .btn.active {
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-weight: 600;
}

.paper-abstract {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 20px;
}
.paper-abstract h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--color-text-primary);
}
.paper-abstract p {
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.paper-body {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-primary);
}
.paper-paragraph {
  margin-bottom: 12px;
}

.viewer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-muted);
  font-size: 15px;
}

/* ====== 翻译对照 ====== */
.translation-progress {
  margin-bottom: 16px;
}
.progress-bar {
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 6px;
}
.progress-fill {
  height: 100%;
  background: var(--color-accent);
  border-radius: 2px;
  transition: width 0.3s ease;
}
.progress-text {
  font-size: 12px;
  color: var(--color-text-muted);
}

.translation-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border-light);
}
.translation-row:last-child {
  border-bottom: none;
}

.translation-cell {
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  position: relative;
}
.translation-cell.en {
  background: var(--color-bg-secondary);
}
.translation-cell.zh {
  background: var(--color-accent-light);
}
.translation-cell p {
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text-primary);
}

.lang-tag {
  position: absolute;
  top: -8px;
  left: 10px;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 3px;
  letter-spacing: 0.5px;
}
.translation-cell.en .lang-tag {
  background: var(--color-bg-primary);
  color: var(--color-text-muted);
}
.translation-cell.zh .lang-tag {
  background: var(--color-accent);
  color: #fff;
}
.dark .translation-cell.zh .lang-tag {
  color: #1a1a1a;
}

.translating-hint {
  color: var(--color-text-muted);
  font-style: italic;
}

/* ====== 部署对话框 ====== */
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
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid var(--color-border);
}

.deploy-icon { font-size: 48px; text-align: center; margin-bottom: 8px; }
.deploy-dialog h4 {
  text-align: center;
  font-size: 15px;
  font-family: var(--font-mono);
  margin-bottom: 6px;
}
.deploy-desc {
  text-align: center;
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 16px;
}

.deploy-details {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  margin-bottom: 16px;
}
.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
}
.detail-item + .detail-item { border-top: 1px solid var(--color-border-light); }
.detail-label { color: var(--color-text-muted); }
.detail-value { color: var(--color-text-primary); font-weight: 500; }

.deploy-status {
  text-align: center;
  padding: 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.deploy-status.error { color: var(--color-danger); }
.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 10px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ====== 划词菜单 ====== */
.selection-menu {
  position: fixed;
  z-index: 1000;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: 4px;
}
.selection-menu button {
  display: block;
  width: 100%;
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-primary);
  font-size: 13px;
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
  border: none;
}
.selection-menu button:hover {
  background: var(--color-accent-light);
  color: var(--color-accent);
}
</style>
