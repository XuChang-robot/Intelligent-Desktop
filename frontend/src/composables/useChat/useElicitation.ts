import { ref } from 'vue'
import type { ElicitationSchema, Message } from '../../types'

export function useElicitation() {
  const currentElicitation = ref<{
    message: string
    schema?: ElicitationSchema
  } | null>(null)

  const setCurrentElicitation = (data: { message: string; schema?: ElicitationSchema }) => {
    currentElicitation.value = data
  }

  const clearCurrentElicitation = () => {
    currentElicitation.value = null
  }

  const createElicitationMessage = (data: { message: string; schema?: ElicitationSchema }): Message => {
    const hasSchema = data.schema && 
                      data.schema.properties && 
                      Object.keys(data.schema.properties).length > 0

    return {
      id: Date.now().toString(),
      role: 'system',
      content: data.message,
      type: hasSchema ? 'parameter_fix' : 'confirm',
      timestamp: new Date(),
      metadata: {
        type: 'elicitation',
        message: data.message,
        schema: data.schema
      }
    }
  }

  const handleElicitationResponse = async (
    confirmed: boolean,
    markMessageAsProcessed: (messageContent: string, confirmed: boolean) => void,
    handleResponse: (response: any) => void,
    formData?: any
  ) => {
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
      throw error
    } finally {
      clearCurrentElicitation()
    }
  }

  return {
    currentElicitation,
    setCurrentElicitation,
    clearCurrentElicitation,
    createElicitationMessage,
    handleElicitationResponse
  }
}
