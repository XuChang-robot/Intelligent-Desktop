<template>
  <div class="task-panel">
    <div class="panel-header">
      <el-icon><List /></el-icon>
      <span>任务跟踪</span>
    </div>
    
    <div class="task-list">
      <div
        v-for="task in tasks"
        :key="task.id"
        :class="['task-item', task.status]"
      >
        <div class="task-info">
          <div class="task-name">{{ task.name }}</div>
          <div 
            class="task-description" 
            v-if="task.description" 
            v-html="formatDescription(task.description, task.latestLog)"
          />
        </div>
        
        <div class="task-status">
          <el-icon v-if="task.status === 'completed'"><CircleCheck /></el-icon>
          <el-icon v-else-if="task.status === 'failed'"><CircleClose /></el-icon>
          <el-icon v-else-if="task.status === 'running'" class="is-loading"><Loading /></el-icon>
          <el-icon v-else><Timer /></el-icon>
        </div>
        
        <el-progress
          v-if="task.status === 'running'"
          :percentage="task.progress"
          :stroke-width="4"
        />
      </div>
    </div>
    
    <div v-if="tasks.length === 0" class="empty-tasks">
      <el-icon><Document /></el-icon>
      <span>暂无任务</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { List, CircleCheck, CircleClose, Loading, Timer, Document } from '@element-plus/icons-vue'
import type { Task } from '../types'

interface Props {
  tasks: Task[]
}

defineProps<Props>()

const formatDescription = (description: string, latestLog?: string): string => {
  if (!description) return ''
  
  const lines = description.split('\n')
  if (!latestLog || lines.length === 0) {
    return description.replace(/\n/g, '<br>')
  }
  
  // 找到最新的日志消息并高亮显示
  return lines.map(line => {
    if (line === latestLog) {
      return `<span class="latest-log">${line}</span>`
    }
    return line
  }).join('<br>')
}
</script>

<style scoped>
.task-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  font-size: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color);
  margin-bottom: 16px;
}

.task-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-item {
  padding: 12px;
  border-radius: 8px;
  background-color: var(--el-fill-color-light);
  border-left: 4px solid var(--el-border-color);
}

.task-item.pending {
  border-left-color: var(--el-text-color-secondary);
}

.task-item.running {
  border-left-color: var(--el-color-primary);
}

.task-item.completed {
  border-left-color: var(--el-color-success);
}

.task-item.failed {
  border-left-color: var(--el-color-danger);
}

.task-info {
  margin-bottom: 8px;
}

.task-name {
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-description {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

:deep(.latest-log) {
  color: var(--el-color-primary);
  font-weight: 500;
  animation: highlight 1s ease-in-out;
}

@keyframes highlight {
  0% {
    background-color: rgba(64, 158, 255, 0.2);
  }
  100% {
    background-color: transparent;
  }
}

.task-status {
  float: right;
  margin-top: -24px;
}

.empty-tasks {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
  gap: 8px;
}

.empty-tasks .el-icon {
  font-size: 32px;
}
</style>
