<template>
  <div class="welcome">
    <div class="welcome-content">
      <div class="welcome-icon">📚</div>
      <h2>欢迎使用 PaperMind</h2>
      <p class="welcome-subtitle">你的智能论文阅读助手</p>
      <p class="hint">从左侧文库选择一篇论文开始阅读，或点击组别旁的 + 导入论文</p>
    </div>
  </div>
</template>

<style scoped>
.welcome { display: flex; align-items: center; justify-content: center; height: 100%; background: var(--color-bg-primary); }
.welcome-content { text-align: center; max-width: 400px; }
.welcome-icon { font-size: 56px; margin-bottom: 16px; }
h2 { font-size: 24px; font-weight: 700; color: var(--color-text-primary); margin-bottom: 8px; }
.welcome-subtitle { font-size: 16px; color: var(--color-text-secondary); margin-bottom: 24px; }
.hint { font-size: 13px; color: var(--color-text-muted); }
</style>
