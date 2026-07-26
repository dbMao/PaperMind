<template>
  <div class="chat-panel">
    <!-- 顶部模式切换 -->
    <div class="chat-header">
      <div class="mode-tabs">
        <button
          :class="{ active: chat.mode === 'single' }"
          @click="chat.setMode('single')"
        >单篇问答</button>
        <button
          :class="{ active: chat.mode === 'global' }"
          @click="chat.setMode('global')"
        >全局问答</button>
      </div>
      <button v-if="chat.messages.length" class="btn-ghost btn-sm" @click="chat.clearMessages()" title="清空对话">清空</button>
    </div>

    <!-- 消息区域 -->
    <div class="messages-area" ref="messagesRef">
      <div v-if="chat.messages.length === 0" class="messages-empty">
        <p>💡 基于论文内容向我提问</p>
      </div>

      <div
        v-for="msg in chat.messages"
        :key="msg.id"
        class="message"
        :class="msg.role"
      >
        <div class="message-bubble">
          <div class="message-text" v-html="renderText(msg.content)"></div>

          <!-- 引用来源 -->
          <div v-if="msg.sources && msg.sources.length" class="message-sources">
            <span class="sources-label">📖 引用来源：</span>
            <span
              v-for="(s, i) in msg.sources"
              :key="i"
              class="source-tag"
            >{{ s.title }} (p.{{ s.page }})</span>
          </div>
        </div>
      </div>

      <!-- 流式输出光标 -->
      <div v-if="chat.isStreaming" class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <!-- 控制栏：推理强度 + 预设功能 -->
      <div class="input-controls">
        <!-- 推理强度 -->
        <div class="reasoning-selector">
          <span class="control-label">推理强度</span>
          <div class="effort-btns">
            <button
              v-for="level in REASONING_LEVELS"
              :key="level.value"
              :class="{ active: chat.reasoningEffort === level.value }"
              :title="level.desc"
              @click="chat.setReasoningEffort(level.value)"
            >{{ level.label }}</button>
          </div>
        </div>

        <!-- 预设功能 -->
        <div class="preset-selector" ref="presetRef">
          <button
            class="preset-trigger"
            :class="{ active: chat.activePresetId }"
            @click="presetMenuOpen = !presetMenuOpen"
          >
            <span v-if="chat.activePreset">{{ chat.activePreset.icon }} {{ chat.activePreset.label }}</span>
            <span v-else>⚡ 预设功能</span>
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
          </button>

          <!-- 下拉菜单 -->
          <div v-if="presetMenuOpen" class="preset-menu">
            <button
              v-for="p in PRESETS"
              :key="p.id"
              class="preset-item"
              :class="{
                selected: chat.activePresetId === p.id,
                disabled: !p.modes.includes(chat.mode),
              }"
              :disabled="!p.modes.includes(chat.mode)"
              @click="p.modes.includes(chat.mode) && selectPreset(p.id)"
              :title="!p.modes.includes(chat.mode) ? modeHint(p) : ''"
            >
              <span class="preset-icon">{{ p.icon }}</span>
              <span class="preset-label">{{ p.label }}</span>
              <span v-if="!p.modes.includes(chat.mode)" class="preset-mode-tag">{{ p.modes[0] === 'single' ? '单篇' : '全局' }}</span>
              <span v-if="chat.activePresetId === p.id" class="preset-check">✓</span>
            </button>
            <div v-if="chat.activePresetId" class="preset-menu-footer">
              <button class="btn-ghost btn-sm" @click="chat.clearPreset(); presetMenuOpen = false">清除选择</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入行 -->
      <div class="input-row">
        <textarea
          v-model="chat.inputText"
          :placeholder="inputPlaceholder"
          rows="2"
          @keydown.enter.exact.prevent="handleSend"
          ref="inputRef"
        ></textarea>
        <button
          class="btn btn-primary send-btn"
          :disabled="!chat.inputText.trim() || chat.isStreaming"
          @click="handleSend"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import { usePapersStore } from '@/stores/papers'
import { PRESETS, REASONING_LEVELS, getPresetsByMode } from '@/api/prompts'

const chat = useChatStore()
const papers = usePapersStore()
const messagesRef = ref(null)
const inputRef = ref(null)
const presetRef = ref(null)
const presetMenuOpen = ref(false)

// 当前模式下可用的预设列表
const availablePresets = computed(() => getPresetsByMode(chat.mode))

// 输入框占位文字随预设变化
const inputPlaceholder = computed(() => {
  if (chat.activePreset) {
    const tips = {
      summarize: '输入摘要要求或直接发送...',
      compare: '描述对比维度或选择论文后直接发送...',
      algorithm: '指定要分析的算法或直接发送...',
      references: '输入额外要求或直接发送...',
    }
    return tips[chat.activePresetId] || '输入你的问题...（Enter 发送）'
  }
  return '输入你的问题...（Enter 发送，Shift+Enter 换行）'
})

function modeHint(preset) {
  if (preset.modes.includes('global') && !preset.modes.includes('single')) return '请切换到「全局问答」模式使用'
  if (preset.modes.includes('single') && !preset.modes.includes('global')) return '请切换到「单篇问答」模式使用'
  return ''
}

function selectPreset(id) {
  chat.setPreset(id)
  presetMenuOpen.value = false
}

function handleSend() {
  const pid = chat.mode === 'single' ? papers.selectedPaperId : null
  chat.sendMessage(chat.inputText, pid)
}

// 简单 markdown 渲染（换行 → <br>）
function renderText(text) {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
}

// 自动滚动到底部
function scrollToBottom() {
  nextTick(() => {
    const el = messagesRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}
watch(() => chat.messages.length, scrollToBottom)
watch(() => chat.isStreaming.value, scrollToBottom)

// 监听划词提问事件
function onPaperSelectionAsk(e) {
  chat.inputText = `关于这段内容：「${e.detail.text}」\n请解释其含义。`
  chat.setMode('single')
  nextTick(() => {
    inputRef.value?.focus()
  })
}

// 点击外部关闭预设菜单
function onClickDocument(e) {
  if (presetRef.value && !presetRef.value.contains(e.target)) {
    presetMenuOpen.value = false
  }
}

onMounted(() => {
  window.addEventListener('paper-selection-ask', onPaperSelectionAsk)
  document.addEventListener('click', onClickDocument)
})
onUnmounted(() => {
  window.removeEventListener('paper-selection-ask', onPaperSelectionAsk)
  document.removeEventListener('click', onClickDocument)
})
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-bg-primary);
  border-left: 1px solid var(--color-border);
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.mode-tabs {
  display: flex;
  gap: 2px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  padding: 2px;
}
.mode-tabs button {
  padding: 5px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  background: transparent;
  color: var(--color-text-secondary);
  transition: all var(--transition);
}
.mode-tabs button.active {
  background: var(--color-bg-primary);
  color: var(--color-accent);
  box-shadow: var(--shadow-sm);
}

/* 消息区域 */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.messages-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-muted);
  font-size: 14px;
}

.message {
  display: flex;
}
.message.user { justify-content: flex-end; }
.message.assistant { justify-content: flex-start; }

.message-bubble {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 14px;
  line-height: 1.65;
}

.message.user .message-bubble {
  background: var(--color-bg-bubble-user);
  color: var(--color-text-primary);
  border-bottom-right-radius: 4px;
}

.message.assistant .message-bubble {
  background: var(--color-bg-bubble-ai);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-light);
  border-bottom-left-radius: 4px;
}

.message-sources {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border-light);
}

.sources-label {
  font-size: 11px;
  color: var(--color-text-muted);
  display: block;
  margin-bottom: 4px;
}

.source-tag {
  display: inline-block;
  margin: 2px 4px 2px 0;
  padding: 2px 8px;
  font-size: 11px;
  background: var(--color-accent-light);
  color: var(--color-accent);
  border-radius: 10px;
}

/* 输入区域 */
.input-area {
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
  padding: 8px 16px 12px;
}

/* 控制栏 */
.input-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.control-label {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-right: 4px;
}

/* 推理强度 */
.reasoning-selector {
  display: flex;
  align-items: center;
  gap: 4px;
}
.effort-btns {
  display: flex;
  gap: 1px;
  background: var(--color-bg-hover);
  border-radius: 4px;
  padding: 1px;
}
.effort-btns button {
  padding: 3px 8px;
  font-size: 11px;
  border-radius: 3px;
  background: transparent;
  color: var(--color-text-muted);
  transition: all var(--transition);
}
.effort-btns button.active {
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

/* 预设功能下拉 */
.preset-selector {
  position: relative;
}

.preset-trigger {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
  transition: all var(--transition);
}
.preset-trigger:hover {
  background: var(--color-border);
  color: var(--color-text-primary);
}
.preset-trigger.active {
  background: var(--color-accent-light);
  color: var(--color-accent);
}

.preset-menu {
  position: absolute;
  bottom: 100%;
  right: 0;
  margin-bottom: 4px;
  min-width: 180px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  z-index: 100;
}

.preset-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  font-size: 13px;
  text-align: left;
  background: transparent;
  color: var(--color-text-primary);
  transition: background var(--transition);
}
.preset-item:hover:not(:disabled) {
  background: var(--color-bg-hover);
}
.preset-item.selected {
  background: var(--color-accent-light);
  color: var(--color-accent);
}
.preset-item:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.preset-icon { font-size: 14px; }
.preset-label { flex: 1; }
.preset-mode-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--color-text-muted);
  background: var(--color-bg-hover);
}
.preset-check {
  font-size: 12px;
  color: var(--color-accent);
}

.preset-menu-footer {
  padding: 6px 10px;
  border-top: 1px solid var(--color-border-light);
}

/* 输入行 */
.input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.input-row textarea {
  flex: 1;
  resize: none;
  min-height: 40px;
  max-height: 120px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--color-bg-input);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  font-size: 14px;
  line-height: 1.5;
  outline: none;
}
.input-row textarea:focus {
  border-color: var(--color-accent);
}

.send-btn {
  width: 40px;
  height: 40px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}
.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 14px;
}
.typing-indicator span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-text-muted);
  animation: blink 1.4s infinite both;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes blink {
  0%, 80%, 100% { opacity: 0.2; }
  40% { opacity: 1; }
}
</style>
