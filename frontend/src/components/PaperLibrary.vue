<template>
  <aside class="paper-library">
    <!-- 折叠按钮 -->
    <button class="collapse-btn" @click="$emit('collapse')" title="折叠侧栏">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6" /></svg>
    </button>

    <!-- 上传 & 操作区 -->
    <div class="library-header">
      <button class="btn btn-primary upload-btn" @click="$emit('open-upload')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        上传论文
      </button>
    </div>

    <!-- 搜索 -->
    <div class="search-box">
      <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input
        type="text"
        placeholder="搜索论文..."
        :value="papers.searchQuery"
        @input="papers.setSearchQuery($event.target.value)"
      />
      <button v-if="papers.searchQuery" class="clear-btn" @click="papers.setSearchQuery('')">&times;</button>
    </div>

    <!-- 文件夹列表 -->
    <div class="folder-list">
      <div class="section-label">
        <span>文件夹</span>
        <button class="btn-ghost btn-sm" @click="showAddFolder = true">+新建</button>
      </div>

      <!-- 新建文件夹输入框 -->
      <div v-if="showAddFolder" class="folder-input-row">
        <input
          ref="folderInput"
          v-model="newFolderName"
          placeholder="文件夹名称"
          @keyup.enter="confirmAddFolder"
          @keyup.escape="cancelAddFolder"
        />
        <button class="btn btn-sm btn-primary" @click="confirmAddFolder">确定</button>
        <button class="btn btn-sm btn-ghost" @click="cancelAddFolder">取消</button>
      </div>

      <div
        v-for="f in papers.folderWithCounts"
        :key="f.id"
        class="folder-item"
        :class="{ active: papers.currentFolderId === f.id }"
        @click="papers.setFolder(f.id)"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        </svg>
        <span class="folder-name">{{ f.name }}</span>
        <span class="folder-count">{{ f.paperCount }}</span>

        <!-- 右键菜单（非默认文件夹） -->
        <div v-if="!f.isDefault" class="folder-actions" @click.stop>
          <button class="btn-ghost btn-sm" @click="startRename(f)" title="重命名">✎</button>
          <button class="btn-ghost btn-sm" @click="papers.removeFolder(f.id)" title="删除">✕</button>
        </div>
      </div>

      <!-- 重命名输入 -->
      <div v-if="renamingId !== null" class="folder-input-row">
        <input v-model="renameText" @keyup.enter="confirmRename" @keyup.escape="cancelRename" />
        <button class="btn btn-sm btn-primary" @click="confirmRename">确定</button>
      </div>
    </div>

    <!-- 论文列表 -->
    <div class="paper-list">
      <div class="section-label">
        <span>论文 ({{ papers.filteredPapers.length }})</span>
      </div>

      <div v-if="papers.filteredPapers.length === 0" class="empty-hint">
        暂无论文，上传你的第一篇 PDF 吧
      </div>

      <div
        v-for="paper in papers.filteredPapers"
        :key="paper.id"
        class="paper-item"
        :class="{ active: papers.selectedPaperId === paper.id }"
        @click="papers.selectPaper(paper.id)"
      >
        <div class="paper-item-main">
          <span class="paper-title">{{ paper.title }}</span>
          <span class="paper-meta">{{ paper.authors[0] }} · {{ paper.year }}</span>
        </div>
        <button
          class="btn-ghost btn-sm paper-delete"
          @click.stop="papers.removePaper(paper.id)"
          title="删除"
        >✕</button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { usePapersStore } from '@/stores/papers'

const papers = usePapersStore()

defineEmits(['collapse', 'open-upload'])

// 新建文件夹
const showAddFolder = ref(false)
const newFolderName = ref('')
const folderInput = ref(null)

async function confirmAddFolder() {
  const name = newFolderName.value.trim()
  if (name) {
    papers.addFolder(name)
    newFolderName.value = ''
    showAddFolder.value = false
  }
}
function cancelAddFolder() {
  newFolderName.value = ''
  showAddFolder.value = false
}

// 重命名
const renamingId = ref(null)
const renameText = ref('')

function startRename(folder) {
  renamingId.value = folder.id
  renameText.value = folder.name
  nextTick(() => {
    const inp = document.querySelector('.folder-input-row input')
    if (inp) inp.focus()
  })
}
function confirmRename() {
  if (renamingId.value !== null && renameText.value.trim()) {
    papers.renameFolder(renamingId.value, renameText.value.trim())
  }
  renamingId.value = null
}
function cancelRename() {
  renamingId.value = null
}
</script>

<style scoped>
.paper-library {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-sidebar);
  border-right: 1px solid var(--color-border);
  position: relative;
  overflow: hidden;
}

.collapse-btn {
  position: absolute;
  top: 12px;
  right: 8px;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-muted);
}
.collapse-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.library-header {
  padding: 16px 16px 8px;
}

.upload-btn {
  width: 100%;
  justify-content: center;
}

.search-box {
  position: relative;
  margin: 8px 16px;
}
.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-muted);
  pointer-events: none;
}
.search-box input {
  width: 100%;
  padding: 8px 32px 8px 32px;
}
.clear-btn {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  color: var(--color-text-muted);
  font-size: 16px;
  padding: 2px 6px;
}
.clear-btn:hover { color: var(--color-text-primary); }

.section-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--color-text-muted);
}

/* 文件夹 */
.folder-list { flex-shrink: 0; }

.folder-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text-secondary);
  transition: all var(--transition);
  border-radius: 0;
}
.folder-item:hover { background: var(--color-bg-hover); }
.folder-item.active {
  background: var(--color-accent-light);
  color: var(--color-accent);
}
.folder-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.folder-count { font-size: 11px; color: var(--color-text-muted); }
.folder-actions { display: none; }
.folder-item:hover .folder-actions { display: flex; gap: 2px; }

.folder-input-row {
  display: flex;
  gap: 4px;
  padding: 6px 16px;
}
.folder-input-row input {
  flex: 1;
  padding: 4px 8px;
  font-size: 13px;
  min-width: 0;
}

/* 论文列表 */
.paper-list {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 12px;
}

.empty-hint {
  padding: 24px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-muted);
}

.paper-item {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  background: transparent;
  transition: all var(--transition);
  border-left: 3px solid transparent;
}
.paper-item:hover { background: var(--color-bg-hover); }
.paper-item.active {
  background: var(--color-accent-light);
  border-left-color: var(--color-accent);
}

.paper-item-main {
  flex: 1;
  min-width: 0;
}
.paper-title {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.paper-meta {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 2px;
  display: block;
}
.paper-delete {
  flex-shrink: 0;
  opacity: 0;
}
.paper-item:hover .paper-delete { opacity: 1; }
</style>
