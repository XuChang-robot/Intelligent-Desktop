<template>
  <div class="input-area">
    <div class="input-container">
      <div class="custom-input-wrapper">
        <el-input
          v-model="localMessage"
          type="textarea"
          placeholder="主人尽管吩咐，CosmicNova会尽力完成的哦"
          resize="none"
          class="flex-grow"
          @keydown.enter.prevent="handleEnter"
        />
        <div class="input-actions">
          <el-button
            v-if="loading"
            type="danger"
            :icon="VideoPause"
            circle
            @click="$emit('stop')"
            class="action-button"
          />
          <el-button
            v-else
            type="primary"
            :icon="Promotion"
            circle
            :disabled="!localMessage.trim()"
            @click="send"
            class="action-button"
          />
        </div>
      </div>
    </div>
    <div class="input-tips">
      <span>按 Enter 发送，Ctrl + Enter 换行</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Promotion, VideoPause } from '@element-plus/icons-vue'

interface Props {
  modelValue: string
  loading: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  send: [message: string]
  stop: []
}>()

const localMessage = ref(props.modelValue)

// 同步外部值
watch(() => props.modelValue, (newVal) => {
  localMessage.value = newVal
})

// 同步内部值
watch(localMessage, (newVal) => {
  emit('update:modelValue', newVal)
})

// 发送消息
const send = () => {
  if (localMessage.value.trim() && !props.loading) {
    emit('send', localMessage.value)
    localMessage.value = ''
  }
}

// 处理 Enter 键
const handleEnter = (e: KeyboardEvent) => {
  if (e.ctrlKey) {
    // Ctrl + Enter 换行，手动添加换行符
    const textarea = e.target as HTMLTextAreaElement
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    localMessage.value = localMessage.value.substring(0, start) + '\n' + localMessage.value.substring(end)
    // 移动光标到换行符后面
    setTimeout(() => {
      textarea.selectionStart = textarea.selectionEnd = start + 1
    }, 0)
  } else {
    // Enter 发送
    send()
  }
}
</script>

<style scoped>
.input-area {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.input-container {
  display: flex;
  align-items: stretch;
  flex: 1;
}

.custom-input-wrapper {
  position: relative;
  flex: 1;
  min-height: 60px;
  border: 1px solid var(--el-border-color);
  border-radius: 12px;
  padding: 8px 8px 48px 8px; /* 增加底部padding，为按钮留出更多空间 */
  background-color: var(--el-bg-color);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.flex-grow {
  width: 100%;
  height: 100%;
}

.flex-grow :deep(.el-textarea) {
  height: 100%;
  border: none !important;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: none !important;
  outline: none !important;
  background-color: transparent !important;
}

.flex-grow :deep(.el-textarea__inner) {
  border: none !important;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  line-height: 1.5;
  height: 100%;
  resize: none;
  word-wrap: break-word; /* 确保长文本自动换行 */
  background-color: transparent !important;
  outline: none !important;
}

.flex-grow :deep(.el-textarea__inner:focus) {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  background-color: transparent !important;
}

/* 确保输入框容器也没有边框 */
.flex-grow :deep(.el-input) {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  background-color: transparent !important;
}

.flex-grow :deep(.el-input__wrapper) {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  background-color: transparent !important;
}

/* 确保所有相关元素都没有边框 */
.flex-grow :deep(.el-textarea.is-focus) {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
}

.flex-grow :deep(.el-textarea.is-disabled) {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
}

/* 确保整个输入区域都没有边框 */
.flex-grow * {
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  background-color: transparent !important;
}

.input-actions {
  position: absolute;
  bottom: 8px;
  right: 8px;
  z-index: 1;
}

.action-button {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.input-tips {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-align: center;
}
</style>
