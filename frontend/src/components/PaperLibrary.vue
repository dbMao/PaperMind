<template>
  <aside class="paper-library">
    <!-- 眉头：我的文库 + 折叠按钮 -->
    <div class="library-topbar">
      <span class="library-brand">我的文库</span>
      <button class="collapse-btn" @click="$emit('collapse')" title="收起侧栏">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6" /></svg>
      </button>
    </div>

    <!-- 搜索 -->
    <div class="search-box">
      <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" placeholder="搜索论文..." :value="papers.searchQuery" @input="papers.setSearchQuery($event.target.value)" />
      <button v-if="papers.searchQuery" class="clear-btn" @click="papers.setSearchQuery('')">&times;</button>
    </div>

    <!-- 组别列表 -->
    <div class="folder-list">
      <div class="section-label">
        <span>组别</span>
        <button class="btn-ghost btn-sm" @click="showAddFolder = true">+ 新建</button>
      </div>

      <div v-if="showAddFolder" class="folder-input-row">
        <input ref="folderInput" v-model="newFolderName" placeholder="组别名称" @keyup.enter="confirmAddFolder" @keyup.escape="cancelAddFolder" />
        <button class="btn btn-sm btn-primary" :disabled="addingFolder" @click="confirmAddFolder">{{ addingFolder ? '...' : '确定' }}</button>
        <button class="btn btn-sm btn-ghost" @click="cancelAddFolder">取消</button>
      </div>

      <div v-for="f in papers.folderWithCounts" :key="f.id">
        <div class="folder-item" :class="{ active: papers.currentFolderId === f.id }" @click="toggleFolder(f)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="!expandedFolderIds.includes(f.id)" d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            <path v-else d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2v1H4v10z"/>
          </svg>
          <span class="folder-name">{{ f.name }}</span>
          <button class="btn-ghost btn-sm folder-add" @click.stop="openUploadTo(f)" title="导入论文">+</button>
          <button class="btn-ghost btn-sm folder-edit" @click.stop="startRename(f)" title="重命名">✎</button>
          <button class="btn-ghost btn-sm folder-del" @click.stop="handleDeleteFolder(f)" title="删除">✕</button>
        </div>

        <!-- 重命名输入框（紧贴重命名中的文件夹下方） -->
        <div v-if="renamingId === f.id" class="folder-input-row">
          <input v-model="renameText" @keyup.enter="confirmRename" @keyup.escape="cancelRename" />
          <button class="btn btn-sm btn-primary" @click="confirmRename">确定</button>
        </div>

        <!-- 展开后显示该组别内的论文 -->
        <template v-if="expandedFolderIds.includes(f.id)">
          <div v-if="folderPapers(f.id).length === 0" class="empty-hint" style="padding:8px 16px 8px 36px">暂无论文</div>
          <template v-for="paper in folderPapers(f.id)" :key="paper.id">
            <div
              class="paper-item"
              :class="{ active: papers.selectedPaperId === paper.id && !papers.viewingTranslation }"
              @click="papers.selectPaper(paper.id)"
            >
              <div class="paper-item-main">
                <span class="paper-title">{{ paper.title }}</span>
                <span class="paper-meta">{{ (paper.authors[0] || '') }} · {{ paper.year || '' }}</span>
              </div>
              <div class="paper-menu-wrap" @click.stop>
                <button class="btn-ghost btn-sm paper-more" @click="togglePaperMenu(paper.id, $event)">···</button>
              </div>
            </div>
            <div
              v-if="paper.hasTranslation"
              class="paper-item translation-item"
              :class="{ active: papers.selectedPaperId === paper.id && papers.viewingTranslation }"
              @click="openTranslated(paper.id)"
            >
              <div class="paper-item-main">
                <span class="paper-title">📄 译文</span>
              </div>
            </div>
          </template>
        </template>
      </div>

    </div>

    <!-- 移动论文弹窗 -->
    <Teleport to="body">
      <div v-if="moveTarget" class="dialog-overlay" @click.self="moveTarget = null">
        <div class="dialog move-dialog">
          <div class="dialog-header"><h3>移动到组别</h3></div>
          <div class="dialog-body">
            <button
              v-for="f in moveCandidates"
              :key="f.id"
              class="move-option"
              @click="confirmMove(f.id)"
            >{{ f.name }} ({{ f.paperCount }})</button>
          </div>
        </div>
      </div>
    </Teleport>
    <!-- 三点菜单（Teleport 到 body，不受 overflow 裁剪） -->
    <Teleport to="body">
      <div v-if="paperMenuId" class="paper-dropdown" :style="{ top: menuY + 'px', left: menuX + 'px', position: 'fixed' }">
        <button @click="movePaper(papers.papers.find(p => p.id === paperMenuId))">📁 移动</button>
        <button @click="deletePaper(papers.papers.find(p => p.id === paperMenuId))">🗑 删除</button>
      </div>
    </Teleport>
  </aside>
</template>

<script setup>
import { computed, ref, nextTick, onMounted, onUnmounted } from 'vue'
import { usePapersStore } from '@/stores/papers'
import apiClient from '@/api'

const papers = usePapersStore()
const emit = defineEmits(['collapse', 'open-upload'])

// 展开的组别
const expandedFolderIds = ref([])

function toggleFolder(f) {
  const idx = expandedFolderIds.value.indexOf(f.id)
  if (idx >= 0) {
    expandedFolderIds.value.splice(idx, 1)
  } else {
    expandedFolderIds.value.push(f.id)
    papers.setFolder(f.id)
  }
}

function folderPapers(folderId) {
  return papers.papers.filter(p => p.folderId === folderId)
}

function openUploadTo(folder) {
  papers.setFolder(folder.id)
  emit('open-upload')
}

function openTranslated(paperId) {
  // 已在该论文译文视图 → 关闭
  if (papers.selectedPaperId === paperId && papers.viewingTranslation) {
    papers.selectedPaperId = null
    papers.viewingTranslation = false
    return
  }
  papers.selectedPaperId = paperId
  nextTick(() => {
    papers.viewingTranslation = true
    window.dispatchEvent(new CustomEvent('show-translation', { detail: { paperId } }))
  })
}

// 论文三点菜单
const paperMenuId = ref(null)
const menuX = ref(0)
const menuY = ref(0)
function togglePaperMenu(id, event) {
  if (paperMenuId.value === id) { paperMenuId.value = null; return }
  const btn = event?.currentTarget
  if (btn) {
    const rect = btn.getBoundingClientRect()
    menuX.value = rect.left - 100
    menuY.value = rect.bottom + 4
  }
  paperMenuId.value = id
}
function closePaperMenu() { paperMenuId.value = null }
onMounted(() => document.addEventListener('click', closePaperMenu))
onUnmounted(() => document.removeEventListener('click', closePaperMenu))

async function deletePaper(paper) {
  paperMenuId.value = null
  await papers.removePaper(paper.id)
}

// 移动论文
const moveTarget = ref(null)
const moveCandidates = computed(() => {
  const list = papers.folders.filter(f => !f.isDefault && f.id !== 0)
  return list
})

function movePaper(paper) {
  paperMenuId.value = null
  moveTarget.value = paper
}

async function confirmMove(folderId) {
  if (moveTarget.value) {
    await apiClient.put(`/papers/${moveTarget.value.id}/move`, { folder_id: folderId })
    papers.fetchPapers()
    papers.fetchFolders()
  }
  moveTarget.value = null
}

async function handleDeleteFolder(f) {
  await papers.removeFolder(f.id)
}

// 新建组别
const showAddFolder = ref(false)
const newFolderName = ref('')
const folderInput = ref(null)
const addingFolder = ref(false)

async function confirmAddFolder() {
  const name = newFolderName.value.trim()
  if (!name) return
  addingFolder.value = true
  try {
    const id = await papers.addFolder(name)
    if (id !== null && !expandedFolderIds.value.includes(id)) {
      expandedFolderIds.value.push(id)
    }
    newFolderName.value = ''
    showAddFolder.value = false
  } catch (e) {
    console.error('创建组别失败:', e)
  }
  addingFolder.value = false
}
function cancelAddFolder() { newFolderName.value = ''; showAddFolder.value = false }

// 重命名
const renamingId = ref(null)
const renameText = ref('')
function startRename(folder) { renamingId.value = folder.id; renameText.value = folder.name }
function confirmRename() {
  if (renamingId.value !== null && renameText.value.trim()) {
    papers.renameFolder(renamingId.value, renameText.value.trim())
  }
  renamingId.value = null
}
function cancelRename() { renamingId.value = null }
</script>

<style scoped>
.paper-library {
  display: flex; flex-direction: column; height: 100%;
  background: var(--color-bg-sidebar); border-right: 1px solid var(--color-border);
  overflow: hidden;
}

.library-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px 10px 16px;
  border-bottom: 1px solid var(--color-border);
}
.library-brand { font-size: 14px; font-weight: 700; color: var(--color-text-primary); }
.collapse-btn {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: var(--radius-sm);
  background: var(--color-bg-hover); color: var(--color-text-secondary);
  cursor: pointer; border: none;
}
.collapse-btn:hover { background: var(--color-accent-light); color: var(--color-accent); }

.search-box {
  position: relative; margin: 8px 12px;
}
.search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--color-text-muted); pointer-events: none; }
.search-box input { width: 100%; padding: 8px 32px 8px 32px; }
.clear-btn { position: absolute; right: 6px; top: 50%; transform: translateY(-50%); background: none; color: var(--color-text-muted); font-size: 16px; padding: 2px 6px; border: none; cursor: pointer; }
.clear-btn:hover { color: var(--color-text-primary); }

.section-label {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px 4px;
  font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--color-text-muted);
}

.folder-list { flex: 1; overflow-y: auto; overflow-x: visible; }

.folder-item {
  background-color: rgb(223, 223, 223);
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; cursor: pointer; font-size: 13px;
  color: var(--color-text-secondary); transition: all var(--transition);
}
.folder-item:hover { background: var(--color-bg-hover); }
.folder-item.active { background: var(--color-accent); color: #fff; }
.dark .folder-item.active { background: #444; color: #e8e8e8; }
.folder-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.folder-add, .folder-edit, .folder-del { display: none; flex-shrink: 0; padding: 2px 4px; font-size: 11px; }
.folder-item.active .folder-add,
.folder-item.active .folder-edit,
.folder-item.active .folder-del { color: #fff; }
.folder-item.active .folder-add:hover,
.folder-item.active .folder-edit:hover,
.folder-item.active .folder-del:hover { color: #fff; opacity: 0.8; }
.folder-item:hover .folder-add,
.folder-item:hover .folder-edit,
.folder-item:hover .folder-del { display: inline-flex; }

.folder-input-row { display: flex; gap: 4px; padding: 6px 12px; }
.folder-input-row input { flex: 1; padding: 4px 8px; font-size: 13px; min-width: 0; }

.empty-hint { padding: 24px 16px; text-align: center; font-size: 13px; color: var(--color-text-muted); }

.paper-item {
  background-color: #ffffff;
  display: flex; align-items: center; padding: 8px 12px 8px 32px;
  cursor: pointer; transition: all var(--transition); border-left: 3px solid transparent;
  overflow: hidden; min-width: 0;
}
.paper-item:hover { background: var(--color-bg-hover); }
.paper-item.active { background: var(--color-accent-light); border-left-color: var(--color-accent); }
.paper-item-main { flex: 1; min-width: 0; overflow: hidden; }
.paper-title { display: block; font-size: 13px; font-weight: 500; color: var(--color-text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.paper-meta { font-size: 11px; color: var(--color-text-muted); margin-top: 2px; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.paper-meta { font-size: 11px; color: var(--color-text-muted); margin-top: 2px; display: block; }

.paper-menu-wrap { position: relative; flex-shrink: 0; z-index: 5; }
.paper-menu-wrap:has(.paper-dropdown) { z-index: 40; }
.paper-more { opacity: 0; font-size: 16px; letter-spacing: 2px; padding: 2px 4px; }
.paper-item:hover .paper-more { opacity: 1; }

.translation-item { padding-left: 48px; font-size: 12px; opacity: 0.85; border-left: none; background: var(--color-bg-secondary); position: relative; z-index: 0; }
.dark .translation-item { background: rgba(255,255,255,0.03); }
.translation-item:hover { opacity: 1; background: var(--color-bg-hover); }
.paper-dropdown {
  background: var(--color-bg-primary); border: 1px solid var(--color-border);
  border-radius: var(--radius-md); box-shadow: var(--shadow-lg);
  padding: 4px; min-width: 100px; z-index: 9999;
}
.paper-dropdown button {
  display: block; width: 100%; padding: 6px 10px; border-radius: var(--radius-sm);
  background: transparent; color: var(--color-text-primary); font-size: 13px;
  text-align: left; cursor: pointer; border: none;
}
.paper-dropdown button:hover { background: var(--color-bg-hover); }

.dialog-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 999; }
.dialog { background: var(--color-bg-primary); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); width: 320px; max-width: 90vw; overflow: hidden; }
.dialog-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--color-border); }
.dialog-header h3 { font-size: 15px; font-weight: 600; }
.dialog-body { padding: 8px; max-height: 240px; overflow-y: auto; }
.move-option { display: block; width: 100%; padding: 8px 12px; border-radius: var(--radius-sm); background: transparent; color: var(--color-text-primary); font-size: 13px; text-align: left; cursor: pointer; border: none; }
.move-option:hover { background: var(--color-bg-hover); }
</style>
