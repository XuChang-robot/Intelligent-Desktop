<template>
  <div :class="['system-confirm', { processed: message.isProcessed }]">
    <div class="confirm-header">
      <el-icon><Warning /></el-icon>
      <span>⚠️ 系统确认</span>
    </div>
    <div class="confirm-content">{{ message.content }}</div>
    <div v-if="!message.isProcessed" class="confirm-actions">
      <el-button type="primary" @click="$emit('confirm')">
        ✅ 确认执行
      </el-button>
      <el-button @click="$emit('cancel')">
        ❌ 取消执行
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Warning } from '@element-plus/icons-vue'
import type { Message } from '../types'

interface Props {
  message: Message
}

defineProps<Props>()

defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<style scoped>
.system-confirm {
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

.system-confirm.processed {
  background-color: var(--el-color-success-light-9);
  border-color: var(--el-color-success);
  border-left-color: var(--el-color-success);
  padding: 8px 16px;
  margin: 4px auto;
}

.confirm-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  color: var(--el-color-warning);
  margin-bottom: 12px;
}

.confirm-content {
  margin-bottom: 16px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.confirm-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
}
</style>
