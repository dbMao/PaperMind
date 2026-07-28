<template>
  <div class="paper-viewer" v-if="paper">
    <div class="viewer-toolbar">
      <span class="toolbar-title" :title="paper.title">{{ paper.title }}</span>
      <div class="toolbar-actions">
        <template v-if="hasTranslation">
          <button class="btn btn-sm" :class="showTranslated ? 'btn-primary' : 'btn-secondary'" @click="showTranslated = true; papers.viewingTranslation = true">译文</button>
          <button class="btn btn-sm" :class="!showTranslated ? 'btn-primary' : 'btn-secondary'" @click="showTranslated = false; papers.viewingTranslation = false">原文</button>
          <a :href="`/api/papers/${paper.id}/translated`" download class="btn btn-sm btn-secondary">⬇</a>
        </template>
        <div v-else class="translate-menu-wrap" ref="translateMenuRef">
          <button class="btn btn-secondary btn-sm" :disabled="translating" @click="showTranslateMenu = !showTranslateMenu">
            🌐 {{ translating ? '翻译中...' : '翻译' }}
          </button>
          <div v-if="showTranslateMenu" class="translate-dropdown">
            <button @click="requestTranslation('openai')"> 大模型翻译（更准确，需 API）</button>
            <button @click="requestTranslation('google')"> Google 翻译（免费，需 VPN）</button>
            <button @click="requestTranslation('bing')">= Bing 翻译（免费，需 VPN）</button>
          </div>
        </div>
      </div>
            <button class="btn-ghost btn-sm close-btn" @click="$emit('close')" title="关闭论文">✕</button>

    </div>

    <div class="paper-body">
      <iframe
        v-if="paper"
        ref="pdfFrameRef"
        :src="pdfSrc"
        class="pdf-iframe"
        frameborder="0"
      />
    </div>

    <Teleport to="body">
      <div v-if="translating" class="dialog-overlay">
        <div class="dialog translate-dialog">
          <div class="dialog-header"><h3>正在生成翻译版</h3></div>
          <div class="dialog-body">
            <p style="margin-bottom:12px">pdf2zh 保留排版翻译中...</p>
            <div class="progress-bar"><div class="progress-fill" :style="{ width: translateProgress + '%' }"></div></div>
            <p style="margin-top:8px;font-size:12px;color:var(--color-text-muted)">{{ translateMsg }}</p>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="selectionMenu.visible" class="selection-menu" :style="{ top: selectionMenu.y + 'px', left: selectionMenu.x + 'px' }">
        <button @click="askSelection">💬 基于此提问</button>
      </div>
    </Teleport>
  </div>
  <div v-else class="viewer-empty">请选择一篇论文</div>
</template>

<script setup>
import { computed, reactive, ref, watch, onMounted, onUnmounted } from 'vue'
import { usePapersStore } from '@/stores/papers'
import apiClient from '@/api'

const papers = usePapersStore()
const paper = computed(() => papers.selectedPaper)
defineEmits(['summarize', 'ask-selection', 'close'])

const translating = ref(false)
const translateProgress = ref(0)
const translateMsg = ref('')
const hasTranslation = ref(false)
const showTranslated = ref(false)
const showTranslateMenu = ref(false)
const translateMenuRef = ref(null)

const pdfSrc = computed(() => {
  if (!paper.value) return ''
  if (showTranslated.value && hasTranslation.value) {
    return `/api/papers/${paper.value.id}/translated`
  }
  return `/api/papers/${paper.value.id}/file`
})

// 切换论文时检查翻译状态
// 同步 sidebar 的高亮状态
watch(() => papers.viewingTranslation, (v) => {
  if (v) showTranslated.value = true
  else showTranslated.value = false
})

watch(() => paper.value?.id, async (pid) => {
  showTranslated.value = false
  hasTranslation.value = false
  papers.viewingTranslation = false
  if (!pid) return
  try {
    const res = await apiClient.get(`/papers/${pid}/translate/status`)
    if (res.code === 0 && res.data?.has_translation) {
      hasTranslation.value = true
    }
  } catch { /* ignore */ }
}, { immediate: true })

async function requestTranslation(service = 'openai') {
  if (!paper.value) return
  showTranslateMenu.value = false
  translating.value = true
  translateProgress.value = 10
  const labels = { openai: '大模型翻译', google: 'Google 翻译', bing: 'Bing 翻译' }
  translateMsg.value = `pdf2zh ${labels[service] || ''} 中，大约需要 1-5 分钟...`

  const timer = setInterval(() => {
    if (translateProgress.value < 85) translateProgress.value += 3
  }, 3000)

  try {
    const res = await apiClient.post(`/papers/${paper.value.id}/translate`, { service }, { timeout: 600000 })
    clearInterval(timer)
    if (res.code === 0) {
      hasTranslation.value = true
      showTranslated.value = true
      translateProgress.value = 100
      translateMsg.value = '翻译完成！已自动切换为译文。'
      // 更新 sidebar 中的论文 hasTranslation 标记
      const p = papers.papers.find(p => p.id === paper.value.id)
      if (p) p.hasTranslation = true
    } else {
      translateMsg.value = res.message || '翻译失败'
    }
  } catch (e) {
    clearInterval(timer)
    translateMsg.value = '翻译失败：' + (service === 'openai' ? '请确认已配置 LLM API' : '请检查网络连接（需 VPN）')
    console.error(e)
  }

  setTimeout(() => { translating.value = false }, 2500)
}

function onClickOutside(e) {
  if (translateMenuRef.value && !translateMenuRef.value.contains(e.target)) {
    showTranslateMenu.value = false
  }
}

const pdfFrameRef = ref(null)
const selectionMenu = reactive({ visible: false, x: 0, y: 0, text: '' })

function checkSelection() {
  setTimeout(() => {
    // 先尝试 iframe 内的选区
    const frame = pdfFrameRef.value
    let sel = null
    try {
      if (frame?.contentWindow) {
        sel = frame.contentWindow.getSelection()
      }
    } catch { /* cross-origin, fallback */ }
    if (!sel || !sel.toString().trim()) {
      sel = window.getSelection()
    }
    const text = sel?.toString().trim()
    if (text && text.length > 1) {
      try {
        const range = sel.getRangeAt(0); const rect = range.getBoundingClientRect()
        if (rect.width > 0 && rect.height > 0) {
          selectionMenu.visible = true; selectionMenu.x = rect.left + rect.width / 2 - 60
          selectionMenu.y = rect.bottom + 8; selectionMenu.text = text
        }
      } catch { selectionMenu.visible = false }
    } else { selectionMenu.visible = false }
  }, 80)
}
function askSelection() {
  window.dispatchEvent(new CustomEvent('paper-selection-ask', { detail: { text: selectionMenu.text } }))
  selectionMenu.visible = false; window.getSelection()?.removeAllRanges()
}
function onShowTranslation(e) {
  if (e.detail?.paperId === paper.value?.id) {
    hasTranslation.value = true
    showTranslated.value = true
  }
}
onMounted(() => {
  document.addEventListener('selectionchange', checkSelection)
  document.addEventListener('click', onClickOutside)
  window.addEventListener('show-translation', onShowTranslation)
})
onUnmounted(() => {
  document.removeEventListener('selectionchange', checkSelection)
  document.removeEventListener('click', onClickOutside)
  window.removeEventListener('show-translation', onShowTranslation)
})
</script>

<style scoped>
.paper-viewer { height: 100%; display: flex; flex-direction: column; background: var(--color-bg-primary); }
.viewer-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 8px 16px; flex-shrink: 0; border-bottom: 1px solid var(--color-border); gap: 12px; }
.toolbar-title { font-size: 13px; font-weight: 500; color: var(--color-text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.close-btn { width: 28px; height: 28px; font-size: 16px; display: flex; align-items: center; justify-content: center; border-radius: 4px; }
.close-btn:hover { background: var(--color-bg-hover); color: var(--color-danger); }
.toolbar-actions { display: flex; gap: 6px; align-items: center; flex-shrink: 0; }

.translate-menu-wrap { position: relative; }
.translate-dropdown {
  position: absolute; right: 0; top: 100%; z-index: 20;
  background: var(--color-bg-primary); border: 1px solid var(--color-border);
  border-radius: var(--radius-md); box-shadow: var(--shadow-lg);
  padding: 4px; min-width: 250px; margin-top: 4px;
}
.translate-dropdown button {
  display: block; width: 100%; padding: 6px 10px; border-radius: var(--radius-sm);
  background: transparent; color: var(--color-text-primary); font-size: 13px;
  text-align: left; cursor: pointer; border: none;
}
.translate-dropdown button:hover { background: var(--color-bg-hover); }
.paper-body { flex: 1; overflow: hidden; }
.pdf-iframe { width: 100%; height: 100%; border: none; background: var(--color-bg-primary); }
.dark .pdf-iframe { filter: invert(0.88) hue-rotate(180deg); }
.viewer-empty { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--color-text-muted); font-size: 15px; }

.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 999; }
.dialog { background: var(--color-bg-primary); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); width: 420px; max-width: 90vw; overflow: hidden; }
.dialog-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--color-border); }
.dialog-header h3 { font-size: 16px; font-weight: 600; }
.dialog-body { padding: 20px; }
.progress-bar { height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--color-accent); border-radius: 3px; transition: width 0.5s ease; width: 0; }

.selection-menu { position: fixed; z-index: 1000; background: var(--color-bg-primary); border: 1px solid var(--color-border); border-radius: var(--radius-md); box-shadow: var(--shadow-lg); padding: 4px; }
.selection-menu button { display: block; width: 100%; padding: 8px 14px; border-radius: var(--radius-sm); background: transparent; color: var(--color-text-primary); font-size: 13px; text-align: left; white-space: nowrap; cursor: pointer; border: none; }
.selection-menu button:hover { background: var(--color-accent-light); color: var(--color-accent); }
</style>
