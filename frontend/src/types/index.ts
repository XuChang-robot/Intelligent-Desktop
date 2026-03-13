/**
 * 全局类型定义
 * 集中管理所有类型，避免重复定义
 */

// ==================== 消息相关类型 ====================

export type MessageRole = 'user' | 'assistant' | 'system'
export type MessageType = 'text' | 'confirm' | 'parameter_fix' | 'image'

export interface Message {
  id: string
  role: MessageRole
  content: string
  type?: MessageType
  timestamp: Date
  metadata?: any
  thinking?: string
  isProcessed?: boolean
}

// ==================== 任务相关类型 ====================

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface Task {
  id: string
  name: string
  status: TaskStatus
  progress: number
  description?: string
  latestLog?: string
}

// ==================== 参数校验相关类型 ====================

export interface SchemaProperty {
  type: string
  title?: string
  description?: string
  default?: any
  enum?: any[]
  items?: any
  minimum?: number
  maximum?: number
  format?: string
}

export interface ElicitationSchema {
  properties: Record<string, SchemaProperty>
  required?: string[]
  description?: string
  title?: string
  type?: string
}

export interface ElicitationData {
  message: string
  schema?: ElicitationSchema
}

// ==================== 模型相关类型 ====================

export interface ModelOption {
  label: string
  value: string
}

export interface ModelsResponse {
  models?: string[]
  current_model?: string
  error?: string
}

// ==================== 窗口相关类型 ====================

export type ResizeDirection = 
  | 'top' | 'bottom' | 'left' | 'right'
  | 'topleft' | 'topright' | 'bottomleft' | 'bottomright'

export interface WindowRect {
  x: number
  y: number
  width: number
  height: number
  error?: string
}

// ==================== PyWebView 事件类型 ====================

export type PyWebViewEventType = 
  | 'stream_start' 
  | 'stream_update' 
  | 'stream_end' 
  | 'elicitation_request'
  | 'task_log'

export interface PyWebViewEventDetail {
  type: PyWebViewEventType
  data: any
}

// ==================== API 响应类型 ====================

export interface ApiResponse {
  type?: 'task' | 'error' | 'confirm' | 'parameter_fix' | 'stream'
  response?: string
  content?: string
  message?: string
  error?: string
  thinking?: string
  tasks?: Task[]
  metadata?: any
  // Stream 相关
  start?: boolean
  update?: boolean
  end?: boolean
  sender?: string
  initial_message?: string
}

// ==================== 布局相关类型 ====================

export interface LayoutConfig {
  rightPanelWidth: number
  taskSectionRatio: number
}

export interface LayoutConstraints {
  minRightPanelWidth: number
  maxRightPanelWidth: number
  minTaskRatio: number
  maxTaskRatio: number
}

// ==================== 状态相关类型 ====================

export interface StatusState {
  message: string
  loadingMessage: string
  debugInfo: string
}
