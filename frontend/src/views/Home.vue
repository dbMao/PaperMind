<template>
  <div class="home-layout">
    <!-- 左侧：论文库 (可折叠) -->
    <div class="sidebar" :style="{ width: sidebarCollapsed ? '0px' : papersStore.sidebarWidth + 'px' }">
      <PaperLibrary
        v-if="!sidebarCollapsed"
        @collapse="sidebarCollapsed = true"
        @open-upload="showUpload = true"
      />
    </div>

    <!-- 侧栏展开按钮（折叠后显示） -->
    <button v-if="sidebarCollapsed" class="expand-sidebar-btn" @click="sidebarCollapsed = false">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6" /></svg>
    </button>

    <!-- 可拖拽分隔条 -->
    <div
      v-if="!sidebarCollapsed"
      class="resize-handle"
      @mousedown="startResize"
    ></div>

    <!-- 右侧主区域 -->
    <div class="main-area">
      <!-- 状态一：未选中论文 → 欢迎页 -->
      <WelcomeScreen
        v-if="!papersStore.selectedPaperId"
      />

      <!-- 状态二：选中论文 → 论文 + 对话 -->
      <template v-else>
        <div class="content-area">
          <!-- 左侧 2/3：论文内容 -->
          <PaperViewer class="viewer-pane" />

          <!-- 右侧 1/3：对话框 -->
          <ChatPanel class="chat-pane" />
        </div>
      </template>
    </div>

    <!-- 上传对话框 -->
    <UploadDialog
      :visible="showUpload"
      @close="showUpload = false"
      @uploaded="onUploaded"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import PaperLibrary from '@/components/PaperLibrary.vue'
import WelcomeScreen from '@/components/WelcomeScreen.vue'
import PaperViewer from '@/components/PaperViewer.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import UploadDialog from '@/components/UploadDialog.vue'
import { usePapersStore } from '@/stores/papers'

const papersStore = usePapersStore()

const showUpload = ref(false)
const sidebarCollapsed = ref(false)

function onUploaded() {
  // 上传完成后自动选中新论文
  if (papersStore.papers.length > 0) {
    papersStore.selectPaper(papersStore.papers[0].id)
  }
}

// 侧边栏拖拽
let isResizing = false

function startResize(e) {
  isResizing = true
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onResize(e) {
  if (!isResizing) return
  const w = Math.min(480, Math.max(200, e.clientX))
  papersStore.sidebarWidth = w
}

function stopResize() {
  isResizing = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}
</script>

<style scoped>
.home-layout {
  display: flex;
  height: calc(100vh - 52px); /* 减去顶部导航栏高度 */
  overflow: hidden;
}

.sidebar {
  flex-shrink: 0;
  overflow: hidden;
  transition: width 0.25s ease;
}

.expand-sidebar-btn {
  position: absolute;
  top: 8px;
  left: 0;
  z-index: 10;
  width: 36px;
  height: 36px;
  background: var(--color-bg-sidebar);
  border: 1px solid var(--color-border);
  border-left: none;
  border-radius: 0 6px 6px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  cursor: pointer;
  box-shadow: 2px 0 4px rgba(0,0,0,0.08);
}
.expand-sidebar-btn:hover { color: var(--color-text-primary); background: var(--color-bg-hover); }

.resize-handle {
  width: 4px;
  cursor: col-resize;
  flex-shrink: 0;
  background: transparent;
  transition: background 0.2s;
  position: relative;
}
.resize-handle:hover,
.resize-handle:active {
  background: var(--color-accent);
}

.main-area {
  flex: 1;
  overflow: hidden;
  min-width: 0;
}

/* 状态二：论文 + 对话 */
.content-area {
  display: flex;
  height: 100%;
}

.viewer-pane {
  flex: 2;
  min-width: 0;
}

.chat-pane {
  flex: 1;
  min-width: 340px;
}
</style>
