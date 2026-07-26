<template>
  <div class="welcome">
    <div class="welcome-content">
      <div class="welcome-icon">📚</div>
      <h2>欢迎使用 PaperMind</h2>
      <p class="welcome-subtitle">你的智能论文阅读助手</p>
      <div class="welcome-actions">
        <button class="btn btn-primary" @click="$emit('open-upload')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          上传第一篇论文
        </button>
        <p class="hint">或从左侧论文库选择一篇论文开始阅读</p>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['open-upload'])
</script>

<style scoped>
.welcome {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: var(--color-bg-primary);
}

.welcome-content {
  text-align: center;
  max-width: 400px;
}

.welcome-icon {
  font-size: 56px;
  margin-bottom: 16px;
}

h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.welcome-subtitle {
  font-size: 16px;
  color: var(--color-text-secondary);
  margin-bottom: 32px;
}

.welcome-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.hint {
  font-size: 13px;
  color: var(--color-text-muted);
}
</style>
