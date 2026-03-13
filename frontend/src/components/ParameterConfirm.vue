<template>
  <div :class="['system-param-fix', { processed: message.isProcessed }]">
    <div class="param-fix-header">
      <el-icon><Edit /></el-icon>
      <span>⚠️ 参数确认</span>
    </div>
    <div class="param-fix-content" style="white-space: pre-wrap;">{{ message.content }}</div>
    
    <DynamicForm
      v-if="!message.isProcessed && message.metadata?.schema"
      v-model="formData"
      :schema="message.metadata.schema"
      label-width="120px"
      size="small"
    />
    
    <div v-if="!message.isProcessed" class="param-fix-actions">
      <el-button type="primary" @click="handleConfirm">
        ✅ 确认执行
      </el-button>
      <el-button @click="$emit('cancel')">
        ❌ 取消执行
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted } from 'vue'
import { Edit } from '@element-plus/icons-vue'
import DynamicForm from './DynamicForm.vue'
import type { Message } from '../types'

interface Props {
  message: Message
}

const props = defineProps<Props>()

const emit = defineEmits<{
  confirm: [formData: Record<string, any>]
  cancel: []
}>()

const formData = reactive<Record<string, any>>({})

onMounted(() => {
  if (props.message.metadata?.schema) {
    Object.assign(formData, initFormData(props.message.metadata.schema))
  }
})

const handleConfirm = () => {
  emit('confirm', { ...formData })
}

const initFormData = (schema: any): Record<string, any> => {
  if (!schema?.properties) return {}
  
  const formData: Record<string, any> = {}
  Object.keys(schema.properties).forEach(key => {
    const prop = schema.properties[key]
    formData[key] = prop.default !== undefined ? prop.default : getDefaultValue(prop.type)
  })
  return formData
}

const getDefaultValue = (type: string): any => {
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
</script>

<style scoped>
.system-param-fix {
  width: calc(100% - 24px);
  margin: 8px 0;
  background-color: var(--el-color-warning-light-9);
  border: 1px solid var(--el-color-warning);
  border-radius: 8px;
  padding: 12px;
  border-left: 4px solid var(--el-color-warning);
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  box-sizing: border-box;
}

.system-param-fix.processed {
  background-color: var(--el-color-success-light-9);
  border-color: var(--el-color-success);
  border-left-color: var(--el-color-success);
  padding: 8px 16px;
  margin: 4px auto;
}

.param-fix-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  color: var(--el-color-warning);
  margin-bottom: 12px;
}

.param-fix-content {
  margin-bottom: 16px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.param-fix-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}
</style>
