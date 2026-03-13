import { ref } from 'vue'
import type { Message, ApiResponse } from '../../types'

export function useMessage() {
  const messages = ref<Message[]>([])

  const addMessage = (message: Message) => {
    messages.value.push(message)
  }

  const updateMessage = (id: string, updates: Partial<Message>) => {
    const message = messages.value.find((msg: Message) => msg.id === id)
    if (message) {
      Object.assign(message, updates)
    }
  }

  const removeMessage = (id: string) => {
    const index = messages.value.findIndex((msg: Message) => msg.id === id)
    if (index !== -1) {
      messages.value.splice(index, 1)
    }
  }

  const clearMessages = () => {
    messages.value = []
  }

  const handleResponse = (response: ApiResponse) => {
    if (response.type === 'error') {
      const content = response.response || response.content || response.message || `错误: ${response.error || '未知错误'}`
      if (content.trim()) {
        addMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content,
          type: 'text',
          timestamp: new Date()
        })
      }
    } else if (response.type === 'task') {
      const content = response.response || response.content || response.message || ''
      if (content.trim()) {
        addMessage({
          id: Date.now().toString(),
          role: 'assistant',
          content,
          type: 'text',
          timestamp: new Date(),
          thinking: response.thinking
        })
      }
    } else if (response.type === 'confirm') {
      addMessage({
        id: Date.now().toString(),
        role: 'system',
        content: response.content || '',
        type: 'confirm',
        timestamp: new Date(),
        metadata: response
      })
    } else if (response.type === 'parameter_fix') {
      addMessage({
        id: Date.now().toString(),
        role: 'system',
        content: response.message || '',
        type: 'parameter_fix',
        timestamp: new Date(),
        metadata: response
      })
    }
  }

  const markMessageAsProcessed = (messageContent: string, confirmed: boolean) => {
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const msg = messages.value[i]
      if (msg?.role === 'system' && 
          (msg.type === 'confirm' || msg.type === 'parameter_fix') && 
          msg.metadata?.message === messageContent) {
        msg.isProcessed = true
        msg.content += `\n\n${confirmed ? '✅ 已确认执行' : '❌ 已取消执行'}`
        break
      }
    }
  }

  const loadHistory = async (limit: number = 50) => {
    try {
      if (!window.pywebview?.api) {
        console.error('pywebview API 未就绪')
        return
      }
      
      const history = await window.pywebview.api.get_history(limit)
      if (history.history) {
        messages.value = history.history.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }))
      }
    } catch (error) {
      console.error('加载历史记录失败:', error)
    }
  }

  return {
    messages,
    addMessage,
    updateMessage,
    removeMessage,
    clearMessages,
    handleResponse,
    markMessageAsProcessed,
    loadHistory
  }
}
