import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useTranslatorStore = defineStore('translator', () => {
  // 模型部署状态：unknown | not_deployed | deploying | deployed | error
  const modelStatus = ref('unknown')

  // 翻译显示开关（当前论文）
  const translationVisible = ref(false)

  // 翻译缓存：{ [paperId]: { [paragraphIndex]: translatedText } }
  const translationCache = ref({})

  // 是否正在翻译
  const isTranslating = ref(false)

  // 翻译进度 (0-100)
  const progress = ref(0)

  // 当前正在翻译的 paperId
  const translatingPaperId = ref(null)

  const isModelReady = computed(() => modelStatus.value === 'deployed')

  function checkModelStatus() {
    // TODO: 调用 GET /api/translation/status
    // 模拟：检查 localStorage 中的部署标记
    const deployed = localStorage.getItem('papermind-translator-deployed')
    modelStatus.value = deployed === 'true' ? 'deployed' : 'not_deployed'
  }

  async function deployModel() {
    modelStatus.value = 'deploying'
    // TODO: 调用 POST /api/translation/deploy
    // 模拟部署过程
    await new Promise((r) => setTimeout(r, 5000))
    modelStatus.value = 'deployed'
    localStorage.setItem('papermind-translator-deployed', 'true')
  }

  function toggleTranslation() {
    translationVisible.value = !translationVisible.value
  }

  function getCachedTranslation(paperId) {
    return translationCache.value[paperId] || null
  }

  async function translatePaper(paperId, paragraphs) {
    if (isTranslating.value) return

    isTranslating.value = true
    translatingPaperId.value = paperId
    progress.value = 0

    // 初始化缓存
    if (!translationCache.value[paperId]) {
      translationCache.value[paperId] = {}
    }

    const total = paragraphs.length
    for (let i = 0; i < total; i++) {
      // TODO: 调用 POST /api/translation/translate
      // 模拟翻译（后续替换为真实 API）
      const translated = await mockTranslate(paragraphs[i])
      translationCache.value[paperId][i] = translated
      progress.value = Math.round(((i + 1) / total) * 100)
    }

    isTranslating.value = false
    translatingPaperId.value = null
  }

  // 模拟翻译（后续删除）
  async function mockTranslate(text) {
    await new Promise((r) => setTimeout(r, 200 + Math.random() * 300))
    return `[译文] ${text}`
  }

  // 初始化检查
  checkModelStatus()

  return {
    modelStatus,
    translationVisible,
    translationCache,
    isTranslating,
    progress,
    translatingPaperId,
    isModelReady,
    checkModelStatus,
    deployModel,
    toggleTranslation,
    getCachedTranslation,
    translatePaper,
  }
})
