<template>
  <div class="status-bar" :class="{ 'dark': isDarkMode }">
    <!-- 左侧：状态消息 -->
    <div class="status-message" :class="{ 'loading': isLoading }">
      <el-icon v-if="isLoading" class="is-loading"><Loading /></el-icon>
      {{ displayMessage }}
    </div>
    
    <!-- 右侧：进度条和调试信息 -->
    <div class="status-right">
      <!-- 进度条 -->
      <el-progress
        v-if="showProgress"
        :percentage="progress"
        :format="() => ''"
        :stroke-width="4"
        :show-text="false"
        class="status-progress"
      />
      
      <!-- 调试信息按钮 -->
      <el-popover
        v-if="hasDebugInfo"
        placement="top"
        width="300"
        trigger="click"
      >
        <template #reference>
          <el-button type="text" size="small" class="debug-button">
            <el-icon><WarningFilled /></el-icon>
          </el-button>
        </template>
        <div class="debug-info">
          <pre>{{ debugInfo }}</pre>
        </div>
      </el-popover>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Loading, WarningFilled } from '@element-plus/icons-vue'

// Props
const props = defineProps({
  isDarkMode: {
    type: Boolean,
    default: false
  },
  statusMessage: {
    type: String,
    default: '就绪'
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  progress: {
    type: Number,
    default: 0
  },
  showProgress: {
    type: Boolean,
    default: false
  },
  debugInfo: {
    type: String,
    default: ''
  }
})

// 计算属性
const displayMessage = computed(() => {
  return props.statusMessage || '就绪'
})

const hasDebugInfo = computed(() => {
  return props.debugInfo && props.debugInfo.length > 0
})
</script>

<style scoped>
.status-bar {
  height: 28px;
  background-color: var(--el-bg-color-secondary);
  border-top: 1px solid var(--el-border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}

.status-bar.dark {
  background-color: var(--el-bg-color-dark);
  border-top-color: var(--el-border-color-dark);
  color: var(--el-text-color-secondary);
}

.status-message {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-message.loading {
  color: var(--el-color-primary);
}

.status-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-progress {
  width: 120px;
  margin: 0;
}

.debug-button {
  color: var(--el-text-color-secondary);
  padding: 0;
  margin: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.debug-info {
  max-height: 200px;
  overflow-y: auto;
}

.debug-info pre {
  margin: 0;
  font-size: 11px;
  line-height: 1.4;
  color: var(--el-text-color-regular);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .status-bar {
    padding: 0 8px;
    font-size: 11px;
  }
  
  .status-progress {
    width: 80px;
  }
}
</style>