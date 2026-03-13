import { ref } from 'vue'
import type { ModelOption, ModelsResponse } from '../types'

/**
 * 模型管理 Composable
 * 处理模型列表的获取、选择和切换
 */

export function useModel() {
  // ==================== 状态 ====================
  const selectedModel = ref('')
  const availableModels = ref<ModelOption[]>([])
  const isLoading = ref(false)
  const error = ref('')

  // ==================== 方法 ====================
  
  /**
   * 获取可用模型列表
   */
  const fetchModels = async (): Promise<void> => {
    isLoading.value = true
    error.value = ''
    
    try {
      if (!window.pywebview?.api) {
        throw new Error('pywebview API 未就绪')
      }
      
      const result: ModelsResponse = await window.pywebview.api.get_models()
      
      if (result.error) {
        throw new Error(result.error)
      }
      
      if (result.models) {
        availableModels.value = result.models.map((model: string) => ({
          label: model,
          value: model
        }))
        
        // 设置当前模型
        selectedModel.value = result.current_model || result.models[0] || ''
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : '获取模型列表失败'
      console.error('获取模型列表失败:', err)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 切换模型
   * @param model - 要切换到的模型名称
   */
  const switchModel = async (model: string): Promise<boolean> => {
    if (!window.pywebview?.api) {
      error.value = 'pywebview API 未就绪'
      return false
    }
    
    isLoading.value = true
    error.value = ''
    
    try {
      const response = await window.pywebview.api.set_model(model)
      
      if (response.error) {
        throw new Error(response.error)
      }
      
      selectedModel.value = model
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : '切换模型失败'
      console.error('切换模型失败:', err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * 处理模型选择变化
   */
  const handleModelChange = async (model: string): Promise<void> => {
    const success = await switchModel(model)
    if (!success) {
      // 如果切换失败，恢复之前的选中状态
      // 这里需要外部传入之前的值来恢复
    }
  }

  /**
   * 刷新模型列表
   */
  const refreshModels = async (): Promise<void> => {
    await fetchModels()
  }

  return {
    // 状态
    selectedModel,
    availableModels,
    isLoading,
    error,
    
    // 方法
    fetchModels,
    switchModel,
    handleModelChange,
    refreshModels
  }
}
