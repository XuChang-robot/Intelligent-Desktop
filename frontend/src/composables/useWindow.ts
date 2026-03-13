import { ref } from 'vue'
import type { ResizeDirection, WindowRect } from '../types'

/**
 * 窗口控制 Composable
 * 处理窗口的最小化、最大化、关闭、拖拽和调整大小
 */

export function useWindow() {
  // ==================== 状态 ====================
  const isMaximized = ref(true) // 窗口启动时已经是最大化状态
  const isDragging = ref(false)
  
  // 拖拽相关
  let dragStartX = 0
  let dragStartY = 0
  let isDraggingFromMaximized = false
  
  // 调整大小相关
  let resizeStartX = 0
  let resizeStartY = 0
  let resizeStartWidth = 0
  let resizeStartHeight = 0
  let currentResizeDirection: ResizeDirection | '' = ''

  // ==================== 窗口控制方法 ====================
  
  /**
   * 最小化窗口
   */
  const minimizeWindow = () => {
    if (window.pywebview?.api) {
      window.pywebview.api.minimize_window()
    }
  }

  /**
   * 最大化/还原窗口
   */
  const toggleMaximize = () => {
    if (!window.pywebview?.api) return
    
    const api = isMaximized.value ? 'restore_window' : 'maximize_window'
    window.pywebview.api[api]()
    isMaximized.value = !isMaximized.value
  }

  /**
   * 关闭窗口
   */
  const closeWindow = () => {
    if (window.pywebview?.api) {
      window.pywebview.api.close_window()
    }
  }

  // ==================== 拖拽处理 ====================
  
  /**
   * 处理标题栏鼠标按下事件
   * 用于从最大化状态拖拽还原
   */
  const handleTitleBarMouseDown = (e: MouseEvent) => {
    if (!isMaximized.value || !window.pywebview?.api) return
    
    e.preventDefault()
    e.stopPropagation() // 阻止事件冒泡，避免pywebview处理拖拽
    dragStartX = e.screenX
    dragStartY = e.screenY
    isDraggingFromMaximized = true
    
    document.addEventListener('mousemove', handleMaximizedDragMove)
    document.addEventListener('mouseup', handleMaximizedDragEnd)
  }

  /**
   * 处理从最大化状态开始的拖拽移动
   */
  const handleMaximizedDragMove = async (e: MouseEvent) => {
    if (!isDraggingFromMaximized || !window.pywebview?.api) return
    
    const deltaX = Math.abs(e.screenX - dragStartX)
    const deltaY = Math.abs(e.screenY - dragStartY)
    
    // 只有当移动距离超过阈值时才触发还原
    if (deltaX <= 5 && deltaY <= 5) return
    
    // 移除监听器
    document.removeEventListener('mousemove', handleMaximizedDragMove)
    document.removeEventListener('mouseup', handleMaximizedDragEnd)
    isDraggingFromMaximized = false
    
    // 计算新的窗口位置
    // 按照用户建议的逻辑：newX = 当前窗口位置X+鼠标当前位置X-屏幕中心点位置
    const screenCenterX = window.screen.width / 2
    const screenCenterY = window.screen.height / 2
    // 假设当前窗口位置在屏幕中心（最大化状态）
    const currentWindowX = screenCenterX
    const currentWindowY = screenCenterY
    // 计算新的窗口位置
    const newX = currentWindowX + e.screenX - screenCenterX
    const newY = currentWindowY + e.screenY - screenCenterY

    // 计算新的窗口大小：宽度为可用工作区宽度的9/10，高度为可用工作区高度的3/4
    // 确保不小于后端设置的最小尺寸 (1000, 600)
    const screenWidth = window.screen.width
    const screenHeight = window.screen.height
    const newWidth = Math.floor(screenWidth * 0.8) //Math.max(1000, Math.floor(screenWidth * 0.9)) // 宽度减十分之一，最小1000
    const newHeight = Math.floor(screenHeight * 0.7) //Math.max(600, Math.floor(screenHeight * 0.75)) // 高度减四分之一，最小600
    
    // 使用 restore_and_resize 方法一次性完成还原和移动，避免闪烁
    // 直接传递计算出的新窗口大小
    await window.pywebview.api.restore_and_resize(newWidth, newHeight, newX, newY)
    isMaximized.value = false
    
    // 模拟一次鼠标按下事件，让pywebview的easy_drag接管后续拖动
    // 这样用户可以继续拖动窗口，而不需要重新点击
    const titleBar = document.querySelector('.custom-titlebar')
    if (titleBar) {
      const mouseDownEvent = new MouseEvent('mousedown', {
        clientX: e.clientX,
        clientY: e.clientY,
        screenX: e.screenX,
        screenY: e.screenY,
        bubbles: true,
        cancelable: true
      })
      titleBar.dispatchEvent(mouseDownEvent)
    }
  }

  /**
   * 处理从最大化状态拖拽结束
   */
  const handleMaximizedDragEnd = () => {
    isDraggingFromMaximized = false
    document.removeEventListener('mousemove', handleMaximizedDragMove)
    document.removeEventListener('mouseup', handleMaximizedDragEnd)
  }

  // ==================== 调整大小处理 ====================
  
  /**
   * 开始调整窗口大小
   * @param direction - 调整方向
   * @param e - 鼠标事件
   */
  const startResize = (direction: ResizeDirection, e: MouseEvent) => {
    e.preventDefault()
    currentResizeDirection = direction
    resizeStartX = e.screenX
    resizeStartY = e.screenY
    
    if (!window.pywebview?.api) {
      console.error('pywebview API 不可用')
      return
    }
    
    window.pywebview.api.get_window_rect().then((rect: WindowRect) => {
      if (rect.error) {
        console.error('获取窗口矩形失败:', rect.error)
        return
      }
      resizeStartWidth = rect.width
      resizeStartHeight = rect.height
      
      window.addEventListener('mousemove', handleResizeMove)
      window.addEventListener('mouseup', handleResizeEnd)
    }).catch((err: any) => {
      console.error('获取窗口矩形异常:', err)
    })
  }

  /**
   * 处理调整大小移动
   */
  const handleResizeMove = (e: MouseEvent) => {
    const deltaX = e.screenX - resizeStartX
    const deltaY = e.screenY - resizeStartY
    
    const { newWidth, newHeight, fixPoint } = calculateNewSize(
      currentResizeDirection as ResizeDirection,
      deltaX,
      deltaY
    )
    
    if (window.pywebview?.api) {
      window.pywebview.api.resize_window_with_fixpoint(newWidth, newHeight, fixPoint)
        .catch((err: any) => console.error('调整大小异常:', err))
    }
  }

  /**
   * 计算新的窗口大小和固定点
   */
  const calculateNewSize = (
    direction: ResizeDirection,
    deltaX: number,
    deltaY: number
  ): { newWidth: number; newHeight: number; fixPoint: string } => {
    let newWidth = resizeStartWidth
    let newHeight = resizeStartHeight
    let fixPoint = 'NW'
    
    const MIN_WIDTH = 800
    const MIN_HEIGHT = 600
    
    switch (direction) {
      case 'right':
        newWidth = resizeStartWidth + deltaX
        fixPoint = 'NW'
        break
      case 'left':
        newWidth = resizeStartWidth - deltaX
        fixPoint = 'NE'
        break
      case 'bottom':
        newHeight = resizeStartHeight + deltaY
        fixPoint = 'NW'
        break
      case 'top':
        newHeight = resizeStartHeight - deltaY
        fixPoint = 'SW'
        break
      case 'topleft':
        newWidth = resizeStartWidth - deltaX
        newHeight = resizeStartHeight - deltaY
        fixPoint = 'SE'
        break
      case 'topright':
        newWidth = resizeStartWidth + deltaX
        newHeight = resizeStartHeight - deltaY
        fixPoint = 'SW'
        break
      case 'bottomleft':
        newWidth = resizeStartWidth - deltaX
        newHeight = resizeStartHeight + deltaY
        fixPoint = 'NE'
        break
      case 'bottomright':
        newWidth = resizeStartWidth + deltaX
        newHeight = resizeStartHeight + deltaY
        fixPoint = 'NW'
        break
    }
    
    return {
      newWidth: Math.max(MIN_WIDTH, newWidth),
      newHeight: Math.max(MIN_HEIGHT, newHeight),
      fixPoint
    }
  }

  /**
   * 结束调整大小
   */
  const handleResizeEnd = () => {
    window.removeEventListener('mousemove', handleResizeMove)
    window.removeEventListener('mouseup', handleResizeEnd)
    currentResizeDirection = ''
  }

  // ==================== 事件处理 ====================
  
  /**
   * 处理全局鼠标按下事件
   * 用于阻止非标题栏区域的拖拽
   */
  const handleGlobalMouseDown = (e: MouseEvent) => {
    const target = e.target as HTMLElement
    const isInTitleBar = target.closest('.custom-titlebar') !== null
    
    if (!isInTitleBar && window.pywebview) {
      e.stopPropagation()
    }
  }

  return {
    // 状态
    isMaximized,
    isDragging,
    
    // 窗口控制
    minimizeWindow,
    toggleMaximize,
    closeWindow,
    
    // 拖拽
    handleTitleBarMouseDown,
    
    // 调整大小
    startResize,
    
    // 全局事件
    handleGlobalMouseDown
  }
}
