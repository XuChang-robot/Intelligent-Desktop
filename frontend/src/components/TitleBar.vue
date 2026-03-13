<template>
  <div 
    class="custom-titlebar pywebview-drag-region" 
    @mousedown="$emit('titleBarMouseDown', $event)"
    @dblclick="$emit('toggleMaximize')"
  >
    <div class="titlebar-left">
      <img class="app-icon" :src="SpaceIcon" alt="CosmicNova" />
      <span class="app-title">寰星  CosmicNova</span>
    </div>
    
    <div class="titlebar-center" />
    
    <div class="titlebar-right">
      <!-- 模型选择器 -->
      <div class="model-selector">
        <el-select 
          :model-value="selectedModel" 
          placeholder="选择模型" 
          @change="$emit('modelChange', $event)"
          size="small" 
          style="width: 144px"
        >
          <el-option 
            v-for="model in availableModels" 
            :key="model.value" 
            :label="model.label" 
            :value="model.value" 
          />
        </el-select>
        <el-button 
          :icon="Refresh" 
          text 
          size="small" 
          @click="$emit('refreshModels')" 
          class="titlebar-btn model-refresh-btn" 
          title="刷新模型" 
        />
      </div>
      
      <div class="titlebar-right-spacer" />
      
      <!-- 主题切换 -->
      <el-button 
        :icon="isDarkMode ? Sunny : Moon" 
        text 
        size="small" 
        @click="$emit('toggleTheme')" 
        class="titlebar-btn" 
        :title="isDarkMode ? '浅色模式' : '暗色模式'" 
      />
      
      <!-- 设置按钮 -->
      <el-button 
        :icon="Setting" 
        text 
        size="small" 
        class="titlebar-btn" 
        title="设置" 
      />
      
      <!-- 窗口控制 -->
      <div class="window-controls">
        <el-button 
          :icon="Minus" 
          text 
          size="small" 
          @click="$emit('minimize')" 
          class="window-btn minimize" 
          title="最小化" 
        />
        <el-button 
          text 
          size="small" 
          @click="$emit('toggleMaximize')" 
          class="window-btn maximize" 
          :title="isMaximized ? '还原' : '最大化'"
        >
          <el-icon v-if="!isMaximized" class="is-fullscreen">
            <FullScreen />
          </el-icon>
          <div v-else class="custom-icon" v-html="Box2Fill" />
        </el-button>
        <el-button 
          :icon="Close" 
          text 
          size="small" 
          @click="$emit('close')" 
          class="window-btn close" 
          title="关闭" 
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { 
  Setting, 
  Moon, 
  Sunny, 
  Refresh, 
  Minus, 
  FullScreen, 
  Close 
} from '@element-plus/icons-vue'
import SpaceIcon from '../assets/pictures/icons8-space-96.png'
import Box2Fill from '../assets/icons/box-2-fill.svg?raw'
import type { ModelOption } from '../types'

interface Props {
  isMaximized: boolean
  isDarkMode: boolean
  selectedModel: string
  availableModels: ModelOption[]
}

defineProps<Props>()

defineEmits<{
  minimize: []
  toggleMaximize: []
  close: []
  toggleTheme: []
  modelChange: [model: string]
  refreshModels: []
  titleBarMouseDown: [event: MouseEvent]
}>()
</script>

<style scoped>
.custom-titlebar {
  height: 40px;
  background: linear-gradient(135deg, #000000 0%, #3c3838e6 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  user-select: none;
  border-bottom: 1px solid #3a3a3a;
}

.titlebar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.app-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.app-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.titlebar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.titlebar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.titlebar-btn {
  color: rgba(255, 255, 255, 0.9) !important;
  border-radius: 4px;
  padding: 4px 8px;
}

.titlebar-btn:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: white !important;
}

.window-controls {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-left: 8px;
  border-left: 1px solid rgba(255, 255, 255, 0.2);
  padding-left: 8px;
}

.window-btn {
  color: rgba(255, 255, 255, 0.9) !important;
  border-radius: 4px;
  padding: 4px 8px;
  transition: all 0.2s;
}

.window-btn:hover {
  color: white !important;
}

.window-btn.minimize:hover,
.window-btn.maximize:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
}

.window-btn.close:hover {
  background-color: #ff5f57 !important;
}

.custom-icon {
  width: 12px;
  height: 12px;
  color: currentColor;
}

.custom-icon svg {
  width: 100%;
  height: 100%;
  fill: currentColor;
}

.model-selector {
  display: flex;
  align-items: center;
  gap: 4px;
}

.model-refresh-btn {
  padding: 4px 6px !important;
  margin: 0 !important;
}

.titlebar-right-spacer {
  width: 28px;
}

.model-selector :deep(.el-select .el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  box-shadow: none;
}

.model-selector :deep(.el-select .el-input__inner) {
  color: #ffffff !important;
  font-size: 13px;
}

.model-selector :deep(.el-select .el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.5) !important;
}

.model-selector :deep(.el-select .el-select__caret),
.model-selector :deep(.el-select .el-input__suffix) {
  color: rgba(255, 255, 255, 0.8);
}
</style>
