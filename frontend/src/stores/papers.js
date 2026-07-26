import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const usePapersStore = defineStore('papers', () => {
  // 论文列表（mock 数据，后续接 API）
  const papers = ref([
    {
      id: 1,
      title: 'Attention Is All You Need',
      authors: ['Vaswani, Ashish', 'Shazeer, Noam'],
      year: 2017,
      folderId: 2,
      abstract: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...',
      createdAt: '2026-07-20',
    },
    {
      id: 2,
      title: 'BERT: Pre-training of Deep Bidirectional Transformers',
      authors: ['Devlin, Jacob', 'Chang, Ming-Wei'],
      year: 2019,
      folderId: 2,
      abstract: 'We introduce a new language representation model called BERT...',
      createdAt: '2026-07-21',
    },
    {
      id: 3,
      title: 'Generative Adversarial Networks',
      authors: ['Goodfellow, Ian', 'Pouget-Abadie, Jean'],
      year: 2014,
      folderId: 3,
      abstract: 'We propose a new framework for estimating generative models via an adversarial process...',
      createdAt: '2026-07-22',
    },
  ])

  // 文件夹列表
  const folders = ref([
    { id: 0, name: '全部论文', isDefault: true },
    { id: 1, name: '未分类' },
    { id: 2, name: 'NLP' },
    { id: 3, name: '计算机视觉' },
  ])

  // 当前选中的论文 ID
  const selectedPaperId = ref(null)

  // 搜索关键词
  const searchQuery = ref('')

  // 当前文件夹 ID
  const currentFolderId = ref(0)

  const selectedPaper = computed(() =>
    papers.value.find((p) => p.id === selectedPaperId.value) || null
  )

  const filteredPapers = computed(() => {
    let list = papers.value
    if (currentFolderId.value !== 0) {
      list = list.filter((p) => p.folderId === currentFolderId.value)
    }
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      list = list.filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.authors.some((a) => a.toLowerCase().includes(q))
      )
    }
    return list
  })

  const folderWithCounts = computed(() =>
    folders.value.map((f) => ({
      ...f,
      paperCount: papers.value.filter((p) => p.folderId === f.id).length,
    }))
  )

  function selectPaper(id) {
    selectedPaperId.value = id
  }

  function setFolder(id) {
    currentFolderId.value = id
  }

  function setSearchQuery(query) {
    searchQuery.value = query
  }

  function addPaper(paper) {
    papers.value.unshift(paper)
  }

  function removePaper(id) {
    papers.value = papers.value.filter((p) => p.id !== id)
    if (selectedPaperId.value === id) selectedPaperId.value = null
  }

  function addFolder(name) {
    const newId = Math.max(...folders.value.map((f) => f.id)) + 1
    folders.value.push({ id: newId, name })
    return newId
  }

  function renameFolder(id, name) {
    const f = folders.value.find((f) => f.id === id)
    if (f) f.name = name
  }

  function removeFolder(id) {
    folders.value = folders.value.filter((f) => f.id !== id)
  }

  return {
    papers,
    folders,
    selectedPaperId,
    searchQuery,
    currentFolderId,
    selectedPaper,
    filteredPapers,
    folderWithCounts,
    selectPaper,
    setFolder,
    setSearchQuery,
    addPaper,
    removePaper,
    addFolder,
    renameFolder,
    removeFolder,
  }
})
