import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useUiStore = defineStore('ui', () => {
  // 主题：从 localStorage 恢复，默认跟随系统
  const stored = localStorage.getItem('papermind-theme')
  const theme = ref(stored || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'))

  // 应用主题到 <html>
  function applyTheme(t) {
    document.documentElement.classList.toggle('dark', t === 'dark')
    localStorage.setItem('papermind-theme', t)
  }

  applyTheme(theme.value)

  watch(theme, (val) => {
    applyTheme(val)
  })

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  function setTheme(t) {
    theme.value = t
  }

  // 侧边栏宽度拖拽
  const sidebarWidth = ref(280) // px

  return { theme, toggleTheme, setTheme, sidebarWidth }
})
