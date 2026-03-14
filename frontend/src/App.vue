<template>
  <div class="app-container" @mousedown="handleGlobalMouseDown">
    <!-- 窗口调整大小区域 -->
    <ResizeHandles @start-resize="startResize" />
    
    <el-container class="main-container">
      <!-- 自定义标题栏 -->
      <TitleBar
        :is-maximized="isMaximized"
        :is-dark-mode="isDarkMode"
        :selected-model="selectedModel"
        :available-models="availableModels"
        @toggle-maximize="toggleMaximize"
        @minimize="minimizeWindow"
        @close="closeWindow"
        @toggle-theme="toggleDarkMode"
        @model-change="handleModelChange"
        @refresh-models="fetchModels"
        @title-bar-mouse-down="handleTitleBarMouseDown"
      />
      
      <!-- 主内容区 -->
      <el-container class="content-area">
        <!-- 左侧：聊天区域 -->
        <el-main class="chat-main">
          <ChatArea
            :messages="messages"
            :loading="loading"
            @confirm="handleConfirm"
            @cancel="handleCancel"
            @fix-params="handleFixParams"
          />
        </el-main>
        
        <!-- 可拉伸分割线 -->
        <div class="resizer" @mousedown="startHorizontalResize" />
        
        <!-- 右侧：任务跟踪和输入区域 -->
        <div class="right-panel" :style="{ width: rightPanelWidth + 'px' }">
          <!-- 任务跟踪区域 -->
          <div class="task-section" :style="{ height: taskSectionRatio + '%' }">
            <TaskPanel :tasks="tasks" />
          </div>
          
          <!-- 可拉伸分割线（垂直方向） -->
          <div class="vertical-resizer" @mousedown="startVerticalResize" />
          
          <!-- 输入区域 -->
          <div class="input-section" :style="{ height: (100 - taskSectionRatio) + '%' }">
            <InputArea
              v-model="inputMessage"
              :loading="loading"
              @send="sendMessage"
              @stop="stopGeneration"
            />
          </div>
        </div>
      </el-container>
      
      <!-- 状态栏 -->
      <StatusBar
        :is-dark-mode="isDarkMode"
        :status-message="statusMessage"
        :is-loading="isLoading"
        :progress="progress"
        :show-progress="showProgress"
        :debug-info="debugInfo"
      />
    </el-container>
    
    <!-- 参数修正对话框 -->
    <ParameterFixDialog
      :visible="showParamDialog"
      :schema="paramSchema"
      :message="paramMessage"
      @confirm="handleParamConfirm"
      @cancel="handleParamCancel"
      @reset="handleParamReset"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import ChatArea from './components/ChatArea.vue'
import InputArea from './components/InputArea.vue'
import TaskPanel from './components/TaskPanel.vue'
import ParameterFixDialog from './components/ParameterFixDialog.vue'
import TitleBar from './components/TitleBar.vue'
import ResizeHandles from './components/ResizeHandles.vue'
import StatusBar from './components/StatusBar.vue'
import { useChat } from './composables/useChat'
import { useTheme } from './composables/useTheme'
import { useWindow } from './composables/useWindow'
import { useLayout } from './composables/useLayout'
import { useModel } from './composables/useModel'
import { useStatus } from './composables/useStatus'
import { usePyWebView } from './composables/usePyWebView'

// ==================== Composables ====================

const {
  isMaximized,
  minimizeWindow,
  toggleMaximize,
  closeWindow,
  handleTitleBarMouseDown,
  startResize,
  handleGlobalMouseDown
} = useWindow()

const {
  rightPanelWidth,
  taskSectionRatio,
  startHorizontalResize,
  startVerticalResize
} = useLayout()

const {
  selectedModel,
  availableModels,
  fetchModels,
  handleModelChange
} = useModel()

const { isDarkMode, toggleDarkMode } = useTheme()

const {
  messages,
  loading,
  tasks,
  inputMessage,
  sendMessage,
  stopGeneration,
  handleConfirm,
  handleCancel,
  handleFixParams
} = useChat()

const {
  statusMessage,
  isLoading,
  debugInfo,
  setStatus,
  setLoading
} = useStatus()

// ==================== 进度条状态 ====================

const progress = ref(0)
const showProgress = ref(false)

const { waitForReady } = usePyWebView()

// ==================== 参数修正对话框 ====================

const showParamDialog = ref(false)
const paramSchema = ref({ properties: {} })
const paramMessage = ref('')

const handleParamConfirm = () => {
  showParamDialog.value = false
  setStatus('参数修正已确认')
}

const handleParamCancel = () => {
  showParamDialog.value = false
  setStatus('参数修正已取消')
}

const handleParamReset = () => {
  setStatus('参数已重置')
}

// ==================== 监听 loading 状态 ====================

watch(loading, (newValue) => {
  setStatus(newValue ? '正在执行...' : '就绪')
})

// ==================== 全局状态管理函数 ====================

// 暴露给全局使用的状态管理函数
window.setStatus = setStatus
window.setLoading = (isLoading: boolean, message?: string) => {
  setLoading(isLoading, message)
}
window.setProgress = (value: number) => {
  progress.value = value
  showProgress.value = true
  // 3秒后隐藏进度条
  setTimeout(() => {
    showProgress.value = false
  }, 3000)
}

// ==================== 初始化 ====================

onMounted(async () => {
  const isReady = await waitForReady()
  if (isReady) {
    await fetchModels()
  }
})
</script>

<style scoped>
/* 全局样式重置 */
:global(body),
:global(html) {
  margin: 0;
  padding: 0;
  overflow: hidden;
  height: 100%;
  width: 100%;
}

.app-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  position: relative;
}

.main-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.content-area {
  background-color: var(--el-bg-color-page);
  display: flex;
  flex-direction: row;
  width: 100%;
  flex: 1;
  overflow: hidden;
}

.chat-main {
  flex: 1;
  padding: 0;
  overflow: hidden;
  min-width: 400px;
}

/* 可拉伸分割线 */
.resizer {
  width: 4px;
  background-color: var(--el-border-color);
  cursor: col-resize;
  transition: background-color 0.2s;
  position: relative;
}

.resizer:hover {
  background-color: var(--el-color-primary);
}

.resizer::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 2px;
  height: 30px;
  background-color: var(--el-border-color-darker);
  border-radius: 1px;
}

/* 右侧面板 */
.right-panel {
  display: flex;
  flex-direction: column;
  background-color: var(--el-bg-color);
  border-left: 1px solid var(--el-border-color);
  min-width: 250px;
  max-width: 600px;
}

/* 任务区域 */
.task-section {
  overflow-y: auto;
  background-color: var(--el-bg-color);
}

/* 垂直方向可拉伸分割线 */
.vertical-resizer {
  height: 4px;
  background-color: var(--el-border-color);
  cursor: row-resize;
  transition: background-color 0.2s;
  position: relative;
  flex-shrink: 0;
}

.vertical-resizer:hover {
  background-color: var(--el-color-primary);
}

.vertical-resizer::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 30px;
  height: 2px;
  background-color: var(--el-border-color-darker);
  border-radius: 1px;
}

/* 输入区域 */
.input-section {
  overflow: hidden;
  background-color: var(--el-bg-color);
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 180px;
}

/* 响应式布局调整 */
@media (max-width: 768px) {
  .chat-main {
    min-width: 300px;
  }
}
</style>
