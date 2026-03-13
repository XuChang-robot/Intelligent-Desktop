import { ref, onUnmounted } from 'vue'
import type { LayoutConfig, LayoutConstraints } from '../types'

/**
 * 布局控制 Composable
 * 处理右侧面板宽度和任务区域高度的拖拽调整
 */

// 默认配置
const DEFAULT_CONFIG: LayoutConfig = {
  rightPanelWidth: 500,
  taskSectionRatio: 75
}

// 约束条件
const CONSTRAINTS: LayoutConstraints = {
  minRightPanelWidth: 250,
  maxRightPanelWidth: 600,
  minTaskRatio: 30,
  maxTaskRatio: 90
}

export function useLayout() {
  // ==================== 状态 ====================
  const rightPanelWidth = ref(DEFAULT_CONFIG.rightPanelWidth)
  const taskSectionRatio = ref(DEFAULT_CONFIG.taskSectionRatio)
  
  // 拖拽状态
  let isResizingHorizontal = false
  let isResizingVertical = false
  let startX = 0
  let startWidth = 0
  let startY = 0
  let startRatio = 0

  // ==================== 水平调整（右侧面板宽度）====================
  
  /**
   * 开始水平拖拽调整
   */
  const startHorizontalResize = (e: MouseEvent) => {
    isResizingHorizontal = true
    startX = e.clientX
    startWidth = rightPanelWidth.value
    
    document.addEventListener('mousemove', handleHorizontalResize)
    document.addEventListener('mouseup', stopHorizontalResize)
    setResizeCursor('col-resize')
  }

  /**
   * 处理水平拖拽
   */
  const handleHorizontalResize = (e: MouseEvent) => {
    if (!isResizingHorizontal) return
    
    const delta = startX - e.clientX
    const newWidth = Math.max(
      CONSTRAINTS.minRightPanelWidth,
      Math.min(CONSTRAINTS.maxRightPanelWidth, startWidth + delta)
    )
    rightPanelWidth.value = newWidth
  }

  /**
   * 停止水平拖拽
   */
  const stopHorizontalResize = () => {
    isResizingHorizontal = false
    document.removeEventListener('mousemove', handleHorizontalResize)
    document.removeEventListener('mouseup', stopHorizontalResize)
    resetCursor()
  }

  // ==================== 垂直调整（任务区域高度）====================
  
  /**
   * 开始垂直拖拽调整
   */
  const startVerticalResize = (e: MouseEvent) => {
    isResizingVertical = true
    startY = e.clientY
    startRatio = taskSectionRatio.value
    
    document.addEventListener('mousemove', handleVerticalResize)
    document.addEventListener('mouseup', stopVerticalResize)
    setResizeCursor('row-resize')
  }

  /**
   * 处理垂直拖拽
   */
  const handleVerticalResize = (e: MouseEvent) => {
    if (!isResizingVertical) return
    
    const rightPanel = document.querySelector('.right-panel') as HTMLElement
    if (!rightPanel) return
    
    const rect = rightPanel.getBoundingClientRect()
    const deltaY = e.clientY - startY
    const deltaRatio = (deltaY / rect.height) * 100
    
    const newRatio = Math.max(
      CONSTRAINTS.minTaskRatio,
      Math.min(CONSTRAINTS.maxTaskRatio, startRatio + deltaRatio)
    )
    taskSectionRatio.value = newRatio
  }

  /**
   * 停止垂直拖拽
   */
  const stopVerticalResize = () => {
    isResizingVertical = false
    document.removeEventListener('mousemove', handleVerticalResize)
    document.removeEventListener('mouseup', stopVerticalResize)
    resetCursor()
  }

  // ==================== 工具方法 ====================
  
  /**
   * 设置拖拽时的光标样式
   */
  const setResizeCursor = (cursor: string) => {
    document.body.style.cursor = cursor
    document.body.style.userSelect = 'none'
  }

  /**
   * 重置光标样式
   */
  const resetCursor = () => {
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }

  /**
   * 重置布局到默认值
   */
  const resetLayout = () => {
    rightPanelWidth.value = DEFAULT_CONFIG.rightPanelWidth
    taskSectionRatio.value = DEFAULT_CONFIG.taskSectionRatio
  }

  // ==================== 生命周期 ====================
  
  onUnmounted(() => {
    // 清理所有事件监听器
    document.removeEventListener('mousemove', handleHorizontalResize)
    document.removeEventListener('mouseup', stopHorizontalResize)
    document.removeEventListener('mousemove', handleVerticalResize)
    document.removeEventListener('mouseup', stopVerticalResize)
    resetCursor()
  })

  return {
    // 状态
    rightPanelWidth,
    taskSectionRatio,
    inputSectionRatio: computed(() => 100 - taskSectionRatio.value),
    
    // 方法
    startHorizontalResize,
    startVerticalResize,
    resetLayout,
    
    // 约束（只读）
    constraints: CONSTRAINTS
  }
}

// 简单的 computed 实现（避免引入 vue 的 computed 如果不需要）
function computed<T>(getter: () => T): { value: T } {
  return {
    get value() {
      return getter()
    }
  } as { value: T }
}
