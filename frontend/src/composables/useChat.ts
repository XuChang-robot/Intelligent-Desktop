import { ref, onMounted, onUnmounted } from 'vue'
import type { 
  Message, 
  Task, 
  ElicitationSchema, 
  PyWebViewEventDetail,
  ApiResponse 
} from '../types'

/**
 * 聊天逻辑 Composable
 * 处理消息发送、接收、流式输出和任务跟踪
 */

export function useChat() {
  // ==================== 状态 ====================
  const messages = ref<Message[]>([])
  const loading = ref(false)
  const tasks = ref<Task[]>([])
  const inputMessage = ref('')
  const currentStreamMessageId = ref<string | null>(null)
  const currentElicitation = ref<{
    message: string
    schema?: ElicitationSchema
  } | null>(null)

  // ==================== 事件处理 ====================
  
  const handlePyWebViewEvent = (eventDetail: PyWebViewEventDetail) => {
    const { type, data } = eventDetail
    console.log('收到 pywebview 事件:', type, data)

    switch (type) {
      case 'stream_start':
        startStreamMessage(data.sender, data.initial_message, data.thinking)
        break
      case 'stream_update':
        updateStreamMessage(data.message, data.thinking)
        break
      case 'stream_end':
        endStreamMessage()
        break
      case 'elicitation_request':
        handleElicitationRequest(data)
        break
      case 'task_log':
        handleTaskLog(data.description)
        break
      case 'task_update':
        handleTaskUpdate(data)
        break
      case 'loading':
        handleLoading(data)
        break
      case 'progress':
        handleProgress(data)
        break
      default:
        console.log('未知事件类型:', type)
    }
  }

  /**
   * 处理任务更新
   */
  const handleTaskUpdate = (data: any) => {
    if (data.description) {
      // 调用全局状态管理
      if (window.setStatus) {
        window.setStatus(data.description)
      }
      // 也添加到任务日志
      handleTaskLog(data.description)
    }
  }

  /**
   * 处理加载状态
   */
  const handleLoading = (data: any) => {
    const isLoading = data.loading !== undefined ? data.loading : (data === true || (data && data[0] === true))
    const message = data.message || (typeof data === 'string' ? data : (data && data[1]) || '正在处理...')
    
    if (window.setLoading) {
      window.setLoading(isLoading, message)
    }
  }

  /**
   * 处理进度更新
   */
  const handleProgress = (data: any) => {
    const progress = data.progress !== undefined ? data.progress : (typeof data === 'number' ? data : (data && data[1]) || 0)
    
    if (window.setProgress) {
      window.setProgress(progress)
    }
  }

  /**
   * 处理 elicitation 请求
   */
  const handleElicitationRequest = (data: { message: string; schema?: ElicitationSchema }) => {
    // 调试日志：查看接收到的schema
    console.log('=== Elicitation Request Debug ===')
    console.log('Message:', data.message)
    console.log('Schema:', JSON.stringify(data.schema, null, 2))
    console.log('Schema keys:', data.schema ? Object.keys(data.schema) : 'no schema')
    console.log('Properties:', data.schema?.properties ? Object.keys(data.schema.properties) : 'no properties')
    console.log('================================')

    currentElicitation.value = {
      message: data.message,
      schema: data.schema
    }

    // 判断是否为参数修正：检查schema的description
    const isParameterFix = data.schema && 
                      data.schema.properties && 
                      Object.keys(data.schema.properties).length > 0 &&
                      !(data.schema.description && 
                        data.schema.description.includes('确认模型'))

    messages.value.push({
      id: Date.now().toString(),
      role: 'system',
      content: data.message,
      type: isParameterFix ? 'parameter_fix' : 'confirm',
      timestamp: new Date(),
      metadata: {
        type: 'elicitation',
        message: data.message,
        schema: data.schema
      }
    })
  }

  /**
   * 处理任务日志
   */
  const handleTaskLog = (description: string) => {
    // 查找现有的"系统日志"任务条目
    const existingLogTask = tasks.value.find(
      task => task.name === '系统日志' && task.status === 'completed'
    )
    
    if (existingLogTask) {
      const existingDesc = existingLogTask.description || ''
      existingLogTask.description = existingDesc 
        ? `${existingDesc}\n${description}` 
        : description
      existingLogTask.latestLog = description
    } else {
      tasks.value.push({
        id: `log_${Date.now()}`,
        name: '系统日志',
        status: 'completed',
        progress: 100,
        description,
        latestLog: description
      })
    }
  }

  /**
   * 注册事件回调
   */
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

  // ==================== 消息操作 ====================
  
  /**
   * 发送消息
   */
  const sendMessage = async (message: string) => {
    if (!message.trim() || loading.value) return

    // 用户输入新指令时清空任务列表
    tasks.value = []

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date()
    }
    messages.value.push(userMessage)
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
      messages.value.push({
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

  /**
   * 处理响应
   */
  const handleResponse = (response: ApiResponse) => {
    console.log('handleResponse 被调用:', response)
    
    if (response.type === 'error') {
      const content = response.response || response.content || response.message || `错误: ${response.error || '未知错误'}`
      if (content.trim()) {
        messages.value.push({
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
        messages.value.push({
          id: Date.now().toString(),
          role: 'assistant',
          content,
          type: 'text',
          timestamp: new Date(),
          thinking: response.thinking
        })
      }
    } else if (response.type === 'confirm') {
      messages.value.push({
        id: Date.now().toString(),
        role: 'system',
        content: response.content || '',
        type: 'confirm',
        timestamp: new Date(),
        metadata: response
      })
    } else if (response.type === 'parameter_fix') {
      messages.value.push({
        id: Date.now().toString(),
        role: 'system',
        content: response.message || '',
        type: 'parameter_fix',
        timestamp: new Date(),
        metadata: response
      })
    }
    
    // 处理流式响应
    if (response.type === 'stream') {
      if (response.start) {
        startStreamMessage('assistant', response.content || '', response.thinking || '')
      } else if (response.update) {
        updateStreamMessage(response.content || '', response.thinking || '')
      } else if (response.end) {
        endStreamMessage()
      }
    }
  }

  // ==================== 流式消息 ====================
  
  const startStreamMessage = (sender: string = 'assistant', initialContent: string = '', thinking: string = '') => {
    endStreamMessage()
    
    const messageId = `stream_${Date.now()}`
    currentStreamMessageId.value = messageId
    
    messages.value.push({
      id: messageId,
      role: sender as any,
      content: initialContent,
      timestamp: new Date(),
      thinking
    })
  }

  const updateStreamMessage = (content: string, thinking: string = '') => {
    if (!currentStreamMessageId.value) return
    
    const message = messages.value.find(msg => msg.id === currentStreamMessageId.value)
    if (message) {
      message.content += content
      if (thinking) {
        message.thinking = (message.thinking || '') + thinking
      }
    }
  }

  const endStreamMessage = () => {
    currentStreamMessageId.value = null
  }

  /**
   * 停止生成
   */
  const stopGeneration = () => {
    endStreamMessage()
    loading.value = false
    
    if (window.pywebview?.api) {
      window.pywebview.api.interrupt()
    }
  }

  // ==================== 确认/取消处理 ====================
  
  const handleConfirm = async (confirmed: boolean, metadata: any) => {
    try {
      if (!window.pywebview?.api) {
        console.error('pywebview API 未就绪')
        return
      }
      
      const message = metadata.message || metadata.content || ''
      const content = confirmed ? { confirmed: true } : { confirmed: false }
      
      // 标记对应的系统消息为已处理
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
      messages.value.push({
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

  /**
   * 标记消息为已处理
   */
  const markMessageAsProcessed = (messageContent: string, confirmed: boolean) => {
    for (let i = messages.value.length - 1; i >= 0; i--) {
      const msg = messages.value[i]
      if (msg?.role === 'system' && 
          (msg.type === 'confirm' || msg.type === 'parameter_fix') && 
          msg.metadata?.message === messageContent) {
        msg.isProcessed = true
        if (msg.type === 'parameter_fix') {
          msg.content += `\n\n${confirmed ? '✅ 已修正' : '❌ 取消修正'}`
        } else {
          msg.content += `\n\n${confirmed ? '✅ 已确认' : '❌ 已取消'}`
        }
        break
      }
    }
  }

  // ==================== Elicitation 响应 ====================
  
  const handleElicitationResponse = async (confirmed: boolean, formData?: any) => {
    if (!currentElicitation.value) {
      console.error('currentElicitation 为空，无法处理响应')
      return
    }

    try {
      if (!window.pywebview?.api) return
      
      const message = currentElicitation.value.message
      const content = confirmed ? (formData || { confirmed: true }) : { confirmed: false }
      
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
      console.error('Elicitation 响应失败:', error)
      messages.value.push({
        id: Date.now().toString(),
        role: 'assistant',
        content: `❌ 处理操作时出现错误: ${error instanceof Error ? error.message : String(error)}`,
        timestamp: new Date()
      })
    } finally {
      currentElicitation.value = null
    }
  }

  const handleFixParams = async (action: string, params?: any) => {
    if (action === 'confirm') {
      await handleElicitationResponse(true, params)
    } else if (action === 'cancel') {
      await handleElicitationResponse(false)
    }
  }

  // ==================== 历史记录 ====================
  
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
    // 状态
    messages,
    loading,
    tasks,
    inputMessage,
    currentElicitation,
    
    // 方法
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
