import { ref, computed } from 'vue'

/**
 * 状态栏管理 Composable
 * 处理应用状态消息、加载状态和调试信息
 */

export function useStatus() {
  // ==================== 状态 ====================
  const statusMessage = ref('就绪')
  const loadingMessage = ref('正在处理...')
  const debugInfo = ref('')
  const isLoading = ref(false)

  // ==================== 计算属性 ====================
  
  /**
   * 当前显示的状态文本
   */
  const displayMessage = computed(() => {
    if (isLoading.value && loadingMessage.value) {
      return loadingMessage.value
    }
    return statusMessage.value
  })

  /**
   * 是否有调试信息
   */
  const hasDebugInfo = computed(() => debugInfo.value.length > 0)

  // ==================== 方法 ====================
  
  /**
   * 设置状态消息
   */
  const setStatus = (message: string) => {
    statusMessage.value = message
  }

  /**
   * 设置加载状态
   */
  const setLoading = (loading: boolean, message?: string) => {
    isLoading.value = loading
    if (message) {
      loadingMessage.value = message
    }
    if (loading) {
      statusMessage.value = message || '正在处理...'
    } else {
      statusMessage.value = '就绪'
    }
  }

  /**
   * 设置调试信息
   */
  const setDebugInfo = (info: string) => {
    debugInfo.value = info
    console.log('[Debug]', info)
  }

  /**
   * 追加调试信息
   */
  const appendDebugInfo = (info: string) => {
    debugInfo.value = debugInfo.value ? `${debugInfo.value}\n${info}` : info
    console.log('[Debug]', info)
  }

  /**
   * 清空调试信息
   */
  const clearDebugInfo = () => {
    debugInfo.value = ''
  }

  /**
   * 显示成功状态
   */
  const showSuccess = (message: string) => {
    statusMessage.value = message
    isLoading.value = false
  }

  /**
   * 显示错误状态
   */
  const showError = (message: string) => {
    statusMessage.value = `错误: ${message}`
    isLoading.value = false
  }

  /**
   * 显示警告状态
   */
  const showWarning = (message: string) => {
    statusMessage.value = message
  }

  /**
   * 重置到初始状态
   */
  const reset = () => {
    statusMessage.value = '就绪'
    loadingMessage.value = '正在处理...'
    debugInfo.value = ''
    isLoading.value = false
  }

  return {
    // 状态
    statusMessage,
    loadingMessage,
    debugInfo,
    isLoading,
    
    // 计算属性
    displayMessage,
    hasDebugInfo,
    
    // 方法
    setStatus,
    setLoading,
    setDebugInfo,
    appendDebugInfo,
    clearDebugInfo,
    showSuccess,
    showError,
    showWarning,
    reset
  }
}
