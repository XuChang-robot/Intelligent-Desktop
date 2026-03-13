import type { Message } from '../types'

/**
 * 检查消息是否包含 schema
 */
export const hasSchema = (message: Message): boolean => {
  return !!(
    message.metadata?.schema &&
    message.metadata.schema.properties &&
    Object.keys(message.metadata.schema.properties).length > 0
  )
}

/**
 * 获取默认表单值
 */
export const getDefaultValue = (type: string): any => {
  switch (type) {
    case 'string':
      return ''
    case 'number':
    case 'integer':
      return 0
    case 'boolean':
      return false
    case 'array':
      return []
    default:
      return ''
  }
}

/**
 * 初始化表单数据
 */
export const initFormData = (schema: any): Record<string, any> => {
  if (!schema?.properties) return {}
  
  const formData: Record<string, any> = {}
  Object.keys(schema.properties).forEach(key => {
    const prop = schema.properties[key]
    formData[key] = prop.default !== undefined ? prop.default : getDefaultValue(prop.type)
  })
  return formData
}
