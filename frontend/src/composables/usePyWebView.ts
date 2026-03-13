import { ref } from 'vue'

/**
 * PyWebView API 管理 Composable
 * 处理与后端 Python 的通信初始化和状态检查
 */

const MAX_ATTEMPTS = 50
const RETRY_DELAY = 100

export function usePyWebView() {
  const isReady = ref(false)
  const lastError = ref('')

  /**
   * 检查 PyWebView API 是否就绪
   */
  const checkReady = (): boolean => {
    const pywebview = (window as any).pywebview
    return !!(pywebview?.api?.get_models)
  }

  /**
   * 等待 PyWebView API 就绪
   * @param maxAttempts - 最大尝试次数
   * @returns 是否成功
   */
  const waitForReady = async (maxAttempts = MAX_ATTEMPTS): Promise<boolean> => {
    for (let i = 0; i < maxAttempts; i++) {
      if (checkReady()) {
        isReady.value = true
        return true
      }
      await delay(RETRY_DELAY)
    }
    
    lastError.value = 'PyWebView API 未在预期时间内就绪'
    isReady.value = false
    return false
  }

  /**
   * 延迟函数
   */
  const delay = (ms: number): Promise<void> => {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  /**
   * 获取 PyWebView API
   */
  const getApi = () => {
    return (window as any).pywebview?.api
  }

  /**
   * 调用 API 方法
   */
  const callApi = async <T>(method: string, ...args: any[]): Promise<T | null> => {
    const api = getApi()
    if (!api || typeof api[method] !== 'function') {
      console.error(`API 方法 ${method} 不可用`)
      return null
    }
    
    try {
      return await api[method](...args)
    } catch (error) {
      console.error(`调用 ${method} 失败:`, error)
      throw error
    }
  }

  return {
    isReady,
    lastError,
    checkReady,
    waitForReady,
    getApi,
    callApi
  }
}
