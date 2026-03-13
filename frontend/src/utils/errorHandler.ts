import { ElMessage, ElNotification } from 'element-plus'

export const ErrorLevel = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error'
} as const

export type ErrorLevel = typeof ErrorLevel[keyof typeof ErrorLevel]

export interface ErrorContext {
  module?: string
  action?: string
  details?: Record<string, any>
}

export interface ErrorHandlerOptions {
  showNotification?: boolean
  showMessage?: boolean
  logToConsole?: boolean
  context?: ErrorContext
}

const DEFAULT_OPTIONS: ErrorHandlerOptions = {
  showNotification: false,
  showMessage: true,
  logToConsole: true
}

export function handleError(
  error: unknown,
  options: ErrorHandlerOptions = {}
) {
  const opts = { ...DEFAULT_OPTIONS, ...options }
  const errorMessage = getErrorMessage(error)
  const contextInfo = opts.context ? `[${opts.context.module}${opts.context.action ? '::' + opts.context.action : ''}]` : ''

  if (opts.logToConsole) {
    console.error(`${contextInfo} Error:`, error)
    if (opts.context?.details) {
      console.error('Details:', opts.context.details)
    }
  }

  if (opts.showMessage) {
    ElMessage.error(errorMessage)
  }

  if (opts.showNotification) {
    ElNotification({
      title: '错误',
      message: errorMessage,
      type: 'error',
      duration: 5000
    })
  }

  return errorMessage
}

export function handleSuccess(
  message: string,
  options: Partial<ErrorHandlerOptions> = {}
) {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  if (opts.logToConsole) {
    console.log('Success:', message)
  }

  if (opts.showMessage) {
    ElMessage.success(message)
  }

  if (opts.showNotification) {
    ElNotification({
      title: '成功',
      message,
      type: 'success',
      duration: 3000
    })
  }
}

export function handleWarning(
  message: string,
  options: Partial<ErrorHandlerOptions> = {}
) {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  if (opts.logToConsole) {
    console.warn('Warning:', message)
  }

  if (opts.showMessage) {
    ElMessage.warning(message)
  }

  if (opts.showNotification) {
    ElNotification({
      title: '警告',
      message,
      type: 'warning',
      duration: 4000
    })
  }
}

export function handleInfo(
  message: string,
  options: Partial<ErrorHandlerOptions> = {}
) {
  const opts = { ...DEFAULT_OPTIONS, ...options }

  if (opts.logToConsole) {
    console.info('Info:', message)
  }

  if (opts.showMessage) {
    ElMessage.info(message)
  }

  if (opts.showNotification) {
    ElNotification({
      title: '提示',
      message,
      type: 'info',
      duration: 3000
    })
  }
}

function getErrorMessage(error: unknown): string {
  if (typeof error === 'string') {
    return error
  }

  if (error instanceof Error) {
    return error.message || '发生未知错误'
  }

  if (error && typeof error === 'object' && 'message' in error) {
    return String(error.message)
  }

  return '发生未知错误'
}

export function createErrorHandler(defaultContext: ErrorContext) {
  return {
    error: (error: unknown, options?: Partial<ErrorHandlerOptions>) => {
      return handleError(error, { ...options, context: { ...defaultContext, ...options?.context } })
    },
    success: (message: string, options?: Partial<ErrorHandlerOptions>) => {
      return handleSuccess(message, { ...options, context: { ...defaultContext, ...options?.context } })
    },
    warning: (message: string, options?: Partial<ErrorHandlerOptions>) => {
      return handleWarning(message, { ...options, context: { ...defaultContext, ...options?.context } })
    },
    info: (message: string, options?: Partial<ErrorHandlerOptions>) => {
      return handleInfo(message, { ...options, context: { ...defaultContext, ...options?.context } })
    }
  }
}

export const chatErrorHandler = createErrorHandler({ module: 'Chat' })
export const modelErrorHandler = createErrorHandler({ module: 'Model' })
export const windowErrorHandler = createErrorHandler({ module: 'Window' })
export const layoutErrorHandler = createErrorHandler({ module: 'Layout' })
