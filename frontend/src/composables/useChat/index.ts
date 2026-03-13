import { ref, onMounted, onUnmounted } from 'vue'
import { useMessage } from './useMessage'
import { useStream } from './useStream'
import { useElicitation } from './useElicitation'
import { useTaskLog } from './useTaskLog'
import type { PyWebViewEventDetail } from '../../types'

export function useChat() {
  const {
    messages,
    addMessage,
    handleResponse,
    markMessageAsProcessed,
    loadHistory
  } = useMessage()

  const {
    startStreamMessage,
    updateStreamMessage,
    endStreamMessage
  } = useStream()

  const {
    currentElicitation,
    setCurrentElicitation,
    createElicitationMessage,
    handleElicitationResponse
  } = useElicitation()

  const {
    tasks,
    handleTaskLog,
    clearTasks
  } = useTaskLog()

  const loading = ref(false)
  const inputMessage = ref('')

  const handlePyWebViewEvent = (eventDetail: PyWebViewEventDetail) => {
    const { type, data } = eventDetail

    switch (type) {
      case 'stream_start':
        const streamMsg = startStreamMessage(data.sender, data.initial_message, data.thinking)
        addMessage(streamMsg)
        break
      case 'stream_update':
        updateStreamMessage(messages.value, data.message, data.thinking)
        break
      case 'stream_end':
        endStreamMessage()
        break
      case 'elicitation_request':
        setCurrentElicitation(data)
        addMessage(createElicitationMessage(data))
        break
      case 'task_log':
        handleTaskLog(data.description)
        break
      default:
        console.log('未知事件类型:', type)
    }
  }

  const registerEventCallback = () => {
    window.addEventListener('pywebview_event', ((event: CustomEvent) => {
      handlePyWebViewEvent(event.detail)
    }) as EventListener)

    if (window.pywebview?.api?.register_callback) {
      window.pywebview.api.register_callback('ui_events', (event_type: string, data: any) => {
        handlePyWebViewEvent({ type: event_type as any, data })
      })
    }
  }

  onMounted(() => {
    registerEventCallback()
  })

  onUnmounted(() => {
    window.removeEventListener('pywebview_event', (() => {}) as EventListener)
  })

  const sendMessage = async (message: string) => {
    if (!message.trim() || loading.value) return

    clearTasks()

    const userMessage = {
      id: Date.now().toString(),
      role: 'user' as const,
      content: message,
      timestamp: new Date()
    }
    addMessage(userMessage)
    inputMessage.value = ''
    loading.value = true

    try {
      if (window.pywebview?.api) {
        const response = await window.pywebview.api.send_message(message)
        handleResponse(response)
      } else {
        throw new Error('pywebview API 未就绪')
      }
    } catch (error) {
      console.error('发送消息失败:', error)
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: '抱歉，处理消息时出现错误。',
        type: 'text',
        timestamp: new Date()
      })
    } finally {
      loading.value = false
    }
  }

  const stopGeneration = () => {
    endStreamMessage()
    loading.value = false
    
    if (window.pywebview?.api) {
      window.pywebview.api.interrupt()
    }
  }

  const handleConfirm = async (confirmed: boolean, metadata: any) => {
    try {
      if (!window.pywebview?.api) {
        console.error('pywebview API 未就绪')
        return
      }
      
      const message = metadata.message || metadata.content || ''
      const content = confirmed ? { confirmed: true } : { confirmed: false }
      
      markMessageAsProcessed(message, confirmed)
      
      const response = await window.pywebview.api.confirm_elicitation(
        message,
        content,
        confirmed
      )
      
      if (response) {
        handleResponse(response)
      }
    } catch (error) {
      console.error('确认失败:', error)
      addMessage({
        id: Date.now().toString(),
        role: 'assistant',
        content: `❌ 处理操作时出现错误: ${error instanceof Error ? error.message : String(error)}`,
        timestamp: new Date()
      })
    }
  }

  const handleCancel = async (metadata: any) => {
    await handleConfirm(false, metadata)
  }

  const handleFixParams = async (action: string, params?: any) => {
    if (action === 'confirm') {
      await handleElicitationResponse(true, markMessageAsProcessed, handleResponse, params)
    } else if (action === 'cancel') {
      await handleElicitationResponse(false, markMessageAsProcessed, handleResponse)
    }
  }

  return {
    messages,
    loading,
    tasks,
    inputMessage,
    currentElicitation,
    sendMessage,
    stopGeneration,
    handleConfirm,
    handleCancel,
    handleFixParams,
    handleElicitationResponse,
    loadHistory,
    startStreamMessage,
    updateStreamMessage,
    endStreamMessage
  }
}
