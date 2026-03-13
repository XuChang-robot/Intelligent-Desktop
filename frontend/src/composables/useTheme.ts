import { ref, watch } from 'vue'

export function useTheme() {
  // 暗色模式状态
  const isDarkMode = ref(false)

  // 从 localStorage 读取主题设置
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme) {
    isDarkMode.value = savedTheme === 'dark'
  } else {
    // 检测系统偏好
    isDarkMode.value = window.matchMedia('(prefers-color-scheme: dark)').matches
  }

  // 应用主题
  const applyTheme = (dark: boolean) => {
    const html = document.documentElement
    if (dark) {
      html.classList.add('dark')
    } else {
      html.classList.remove('dark')
    }
  }

  // 初始化主题
  applyTheme(isDarkMode.value)

  // 切换主题
  const toggleDarkMode = () => {
    isDarkMode.value = !isDarkMode.value
    applyTheme(isDarkMode.value)
    localStorage.setItem('theme', isDarkMode.value ? 'dark' : 'light')
  }

  // 监听变化
  watch(isDarkMode, (newVal) => {
    applyTheme(newVal)
  })

  return {
    isDarkMode,
    toggleDarkMode
  }
}
