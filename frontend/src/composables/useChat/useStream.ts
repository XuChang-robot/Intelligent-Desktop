import { ref } from 'vue'
import type { Message } from '../../types'

export function useStream() {
  const currentStreamMessageId = ref<string | null>(null)

  const startStreamMessage = (sender: string = 'assistant', initialContent: string = '', thinking: string = '') => {
    endStreamMessage()
    
    const messageId = `stream_${Date.now()}`
    currentStreamMessageId.value = messageId
    
    return {
      id: messageId,
      role: sender as any,
      content: initialContent,
      timestamp: new Date(),
      thinking
    }
  }

  const updateStreamMessage = (messages: Message[], content: string, thinking: string = '') => {
    if (!currentStreamMessageId.value) return false
    
    const message = messages.find(msg => msg.id === currentStreamMessageId.value)
    if (message) {
      message.content += content
      if (thinking) {
        message.thinking = (message.thinking || '') + thinking
      }
      return true
    }
    return false
  }

  const endStreamMessage = () => {
    currentStreamMessageId.value = null
  }

  const isStreaming = () => {
    return currentStreamMessageId.value !== null
  }

  return {
    currentStreamMessageId,
    startStreamMessage,
    updateStreamMessage,
    endStreamMessage,
    isStreaming
  }
}
