<template>
  <div class="dynamic-form">
    <div class="params-container">
      <div
        v-for="(param, key) in schema.properties"
        :key="key"
        class="param-row"
      >
      <div class="param-label">
        <span class="param-name">{{ param.title || key }}</span>
        <el-tooltip v-if="param.description" :content="param.description" placement="top">
          <el-icon class="label-icon"><QuestionFilled /></el-icon>
        </el-tooltip>
      </div>
      
      <div class="param-value">
        <el-input
          v-if="param.type === 'string'"
          v-model="formData[key]"
          :placeholder="param.description || '请输入' + (param.title || key)"
          :type="param.format === 'textarea' ? 'textarea' : 'text'"
          :rows="param.format === 'textarea' ? 3 : 1"
          class="param-input"
        />

        <el-input-number
          v-else-if="param.type === 'number' || param.type === 'integer'"
          v-model="formData[key]"
          :placeholder="param.description || '请输入' + (param.title || key)"
          :min="param.minimum"
          :max="param.maximum"
          class="param-input"
        />

        <el-switch
          v-else-if="param.type === 'boolean'"
          v-model="formData[key]"
          :active-text="activeText"
          :inactive-text="inactiveText"
          class="param-input"
        />

        <el-select
          v-else-if="param.enum"
          v-model="formData[key]"
          :placeholder="param.description || '请选择' + (param.title || key)"
          class="param-input"
        >
          <el-option
            v-for="option in param.enum"
            :key="option"
            :label="option"
            :value="option"
          />
        </el-select>

        <el-select
          v-else-if="param.type === 'array'"
          v-model="formData[key]"
          multiple
          :placeholder="param.description || '请选择' + (param.title || key)"
          class="param-input"
        >
          <el-option
            v-for="item in param.items?.enum || []"
            :key="item"
            :label="item"
            :value="item"
          />
        </el-select>

        <el-input
          v-else
          v-model="formData[key]"
          :placeholder="param.description || '请输入' + (param.title || key)"
          class="param-input"
        />
      </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { QuestionFilled } from '@element-plus/icons-vue'
import type { ElicitationSchema } from '../types'
import { initFormData } from '../utils/messageUtils'

interface Props {
  schema: ElicitationSchema
  modelValue?: Record<string, any>
  labelWidth?: string
  size?: 'large' | 'default' | 'small'
  activeText?: string
  inactiveText?: string
}

const props = withDefaults(defineProps<Props>(), {
  labelWidth: '120px',
  size: 'default',
  activeText: '是',
  inactiveText: '否'
})

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, any>]
}>()

const formRef = ref()
const formData = reactive<Record<string, any>>({})

// 调试日志
console.log('=== DynamicForm Debug ===')
console.log('Schema:', props.schema)
console.log('Properties:', props.schema?.properties)
console.log('Property keys:', props.schema?.properties ? Object.keys(props.schema.properties) : 'none')
console.log('========================')

// 监听schema变化，初始化表单数据
watch(() => props.schema, (schema) => {
  console.log('=== DynamicForm Schema Changed ===')
  console.log('New schema:', schema)
  console.log('Properties:', schema?.properties)
  console.log('Property keys:', schema?.properties ? Object.keys(schema.properties) : 'none')
  console.log('==================================')
  if (schema?.properties) {
    Object.assign(formData, initFormData(schema))
  }
}, { immediate: true, deep: true })

// 监听modelValue变化，更新表单数据
watch(() => props.modelValue, (newVal) => {
  if (newVal && Object.keys(newVal).length > 0) {
    Object.assign(formData, newVal)
  }
}, { immediate: true, deep: true })

// 监听表单数据变化，触发update:modelValue事件
watch(formData, (newVal) => {
  emit('update:modelValue', { ...newVal })
}, { deep: true })

const validate = () => {
  return formRef.value?.validate()
}

const resetFields = () => {
  formRef.value?.resetFields()
  if (props.schema?.properties) {
    Object.assign(formData, initFormData(props.schema))
  }
}

defineExpose({
  validate,
  resetFields,
  formData
})
</script>

<style scoped>
.dynamic-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.params-container {
  background-color: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 12px;
  transition: all 0.3s ease;
}

.params-container:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.param-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.3s ease;
}

.param-row:last-child {
  border-bottom: none;
}

.param-row:hover {
  background-color: #f5f7fa;
}

.param-label {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 100px;
  flex-shrink: 0;
}

.param-name {
  font-weight: 500;
  color: var(--el-text-color-primary);
  font-size: 12px;
}

.label-icon {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  cursor: help;
}

.param-value {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.current-value-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  white-space: nowrap;
}

.param-input {
  flex: 1;
  min-width: 200px;
}

.param-input :deep(.el-input__wrapper),
.param-input :deep(.el-input-number),
.param-input :deep(.el-select) {
  width: 100%;
}
</style>
