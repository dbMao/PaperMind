import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api'

export const usePapersStore = defineStore('papers', () => {
  const papers = ref([])
  const folders = ref([])

  const selectedPaperId = ref(null)
  const searchQuery = ref('')
  const currentFolderId = ref(null)
  const isSearching = ref(false)

  const selectedPaper = computed(() =>
    papers.value.find((p) => p.id === selectedPaperId.value) || null
  )

  const filteredPapers = computed(() => papers.value)

  const folderWithCounts = computed(() =>
    folders.value.map((f) => ({
      ...f,
      paperCount: f.paper_count ?? 0,
    }))
  )

  // 搜索防抖
  let searchTimer = null

  // ===== 数据加载 =====

  async function fetchPapers() {
    isSearching.value = true
    try {
      const params = { page: 1, page_size: 100 }
      if (currentFolderId.value != null) params.folder_id = currentFolderId.value
      if (searchQuery.value.trim()) params.search = searchQuery.value.trim()

      const res = await apiClient.get('/papers', { params })
      if (res.code === 0) {
        papers.value = (res.data.items || []).map((p) => ({
          id: p.id,
          title: p.title,
          authors: p.authors || [],
          year: p.year,
          folderId: p.folder_id,
          abstract: p.abstract,
          hasTranslation: p.has_translation || false,
          createdAt: p.created_at,
        }))
      }
    } catch (e) {
      console.error('获取论文列表失败:', e)
    }
    isSearching.value = false
  }

  async function fetchFolders() {
    try {
      const res = await apiClient.get('/folders')
      if (res.code === 0) {
        folders.value = res.data || []
      }
    } catch (e) {
      console.error('获取文件夹列表失败:', e)
    }
  }

  // 初始化
  fetchFolders()
  fetchPapers()

  // ===== 搜索（防抖 300ms） =====

  function setSearchQuery(query) {
    searchQuery.value = query
    clearTimeout(searchTimer)
    searchTimer = setTimeout(() => {
      fetchPapers()
    }, 300)
  }

  // ===== 文件夹切换 =====

  function setFolder(id) {
    currentFolderId.value = id
    fetchPapers()
  }

  // ===== 论文操作 =====

  function selectPaper(id) {
    selectedPaperId.value = id
  }

  function addPaper(paper) {
    papers.value.unshift(paper)
  }

  async function removePaper(id) {
    try {
      await apiClient.delete(`/papers/${id}`)
      papers.value = papers.value.filter((p) => p.id !== id)
      if (selectedPaperId.value === id) selectedPaperId.value = null
      fetchFolders() // 更新文件夹计数
    } catch (e) {
      console.error('删除论文失败:', e)
    }
  }

  // ===== 文件夹操作 =====

  async function addFolder(name) {
    try {
      const res = await apiClient.post('/folders', { name })
      if (res.code === 0) {
        folders.value.push({
          id: res.data.id,
          name: res.data.name,
          isDefault: false,
          paper_count: 0,
        })
      }
      return res.data?.id
    } catch (e) {
      console.error('创建文件夹失败:', e)
      return null
    }
  }

  async function renameFolder(id, name) {
    try {
      await apiClient.put(`/folders/${id}`, { name })
      const f = folders.value.find((f) => f.id === id)
      if (f) f.name = name
    } catch (e) {
      console.error('重命名文件夹失败:', e)
    }
  }

  async function removeFolder(id) {
    try {
      await apiClient.delete(`/folders/${id}?force=true`)
      folders.value = folders.value.filter((f) => f.id !== id)
    } catch (e) {
      console.error('删除文件夹失败:', e)
    }
  }

  return {
    papers,
    folders,
    selectedPaperId,
    searchQuery,
    currentFolderId,
    isSearching,
    selectedPaper,
    filteredPapers,
    folderWithCounts,
    fetchPapers,
    fetchFolders,
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
