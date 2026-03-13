<template>
  <div v-if="visible" :class="['param-fix-container', { 'processed': isProcessed }]">
    <div class="param-fix-header">
      <h3 class="param-fix-title">参数修正</h3>
    </div>
    <div class="dialog-message" style="white-space: pre-wrap;">{{ messageContent }}</div>
    
    <DynamicForm
      v-if="!isProcessed"
      :schema="schema"
      :model-value="formData"
      @update:model-value="handleFormUpdate"
      label-width="120px"
      size="default"
    />
    
    <div v-if="!isProcessed" class="dialog-footer">
      <el-button @click="handleCancel">取消</el-button>
      <el-button @click="handleReset">重置</el-button>
      <el-button type="primary" @click="handleConfirm" :loading="confirming">
        确认
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive, computed } from 'vue'
import DynamicForm from './DynamicForm.vue'
import type { Message, ElicitationSchema } from '../types'
import { chatErrorHandler } from '../utils/errorHandler'

interface Props {
  visible: boolean
  message?: Message | string
  schema?: ElicitationSchema
}

const props = withDefaults(defineProps<Props>(), {
  message: '',
  schema: () => ({ properties: {} })
})

// 计算属性：消息内容
const messageContent = computed(() => {
  if (typeof props.message === 'string') {
    return props.message
  }
  return props.message?.content || ''
})

// 计算属性：schema
const schema = computed(() => {
  if (typeof props.message === 'object' && props.message.metadata?.schema) {
    return props.message.metadata.schema
  }
  return props.schema
})

// 计算属性：是否已处理
const isProcessed = computed(() => {
  if (typeof props.message === 'object') {
    return props.message.isProcessed
  }
  return false
})

const emit = defineEmits<{
  confirm: [data: any]
  cancel: []
  reset: []
}>()

const confirming = ref(false)
const formData = reactive<Record<string, any>>({})
const originalData = reactive<Record<string, any>>({})

// 监听schema变化，初始化表单数据
watch(() => schema.value, (schema) => {
  if (schema && schema.properties) {
    Object.keys(schema.properties).forEach(key => {
      const prop = schema.properties[key]
      if (prop) {
        const defaultValue = prop.default !== undefined ? prop.default : getDefaultValue(prop.type)
        formData[key] = defaultValue
        originalData[key] = defaultValue
      }
    })
  }
}, { immediate: true, deep: true })

const getDefaultValue = (type: string) => {
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

const handleFormUpdate = (newData: Record<string, any>) => {
  Object.assign(formData, newData)
}

const handleConfirm = async () => {
  confirming.value = true
  try {
    if (schema.value.required) {
      for (const key of schema.value.required) {
        if (formData[key] === '' || formData[key] === null || formData[key] === undefined) {
          chatErrorHandler.error(`请填写 ${schema.value.properties[key]?.title || key}`, {
            context: { action: 'validateForm' }
          })
          return
        }
      }
    }
    
    emit('confirm', { ...formData })
  } catch (error) {
    chatErrorHandler.error(error, { context: { action: 'handleConfirm' } })
  } finally {
    confirming.value = false
  }
}

const handleCancel = () => {
  emit('cancel')
}

const handleReset = () => {
  Object.keys(originalData).forEach(key => {
    formData[key] = originalData[key]
  })
  emit('reset')
}
</script>

<style scoped>
.param-fix-container {
  background-color: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  margin: 12px 0;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.param-fix-container.processed {
  background-color: var(--el-color-success-light-9);
  border-color: var(--el-color-success-light-7);
  box-shadow: 0 2px 12px 0 rgba(103, 194, 58, 0.2);
}

.param-fix-header {
  margin-bottom: 16px;
}

.param-fix-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
}

.dialog-message {
  margin-bottom: 20px;
  padding: 12px;
  background-color: var(--el-color-warning-light-9);
  border-left: 4px solid var(--el-color-warning);
  border-radius: 4px;
  color: var(--el-text-color-primary);
  line-height: 1.6;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.dialog-processed {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 12px;
  background-color: var(--el-color-success-light-9);
  border-left: 4px solid var(--el-color-success);
  border-radius: 4px;
  color: var(--el-text-color-primary);
}

.dialog-processed el-icon {
  color: var(--el-color-success);
  font-size: 16px;
}
</style>
