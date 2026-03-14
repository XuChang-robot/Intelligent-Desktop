<template>
  <div class="chat-area" ref="chatContainer">
    <div class="messages-container">
      <div
        v-for="message in messages"
        :key="message.id"
        :class="['message-wrapper', message.role]"
      >
        <!-- 用户消息 -->
        <template v-if="message.role === 'user'">
          <div class="message user-message">
            <div class="message-header">
              <div class="message-sender">主人</div>
            </div>
            <div class="message-content">{{ message.content }}</div>
            <div v-if="message.thinking" class="thinking-container">
              <el-collapse>
                <el-collapse-item title="💭 查看思考过程">
                  <div class="thinking-content">{{ message.thinking }}</div>
                </el-collapse-item>
              </el-collapse>
            </div>
            <div class="message-time">{{ formatTime(message.timestamp) }}</div>
          </div>
        </template>
        
        <!-- 助手消息 -->
        <template v-else-if="message.role === 'assistant'">
          <div class="avatar assistant-avatar">
            <img :src="UniverseAvatar" alt="CosmicNova" />
          </div>
          <div class="message assistant-message">
            <div class="message-header">
              <div class="message-sender">CosmicNova</div>
            </div>
            <div class="message-content" v-html="renderContent(message.content)" />
            <div v-if="message.thinking" class="thinking-container">
              <el-collapse>
                <el-collapse-item title="💭 查看思考过程">
                  <div class="thinking-content">{{ message.thinking }}</div>
                </el-collapse-item>
              </el-collapse>
            </div>
            <div class="message-time">{{ formatTime(message.timestamp) }}</div>
          </div>
        </template>
        
        <!-- 系统消息 -->
        <template v-else-if="message.role === 'system'">
          <div class="avatar assistant-avatar">
            <img :src="UniverseAvatar" alt="CosmicNova" />
          </div>
          <div class="message assistant-message">
            <div class="message-header">
              <div class="message-sender">CosmicNova</div>
            </div>
            
            <!-- 确认对话框（无 schema） -->
            <SystemConfirm
              v-if="message.type === 'confirm' && !hasSchema(message)"
              :message="message"
              @confirm="$emit('confirm', true, message.metadata)"
              @cancel="$emit('cancel', message.metadata)"
            />
            
            <!-- 参数修正（parameter_fix 类型） -->
            <ParameterFixDialog
              v-else-if="message.type === 'parameter_fix'"
              :visible="true"
              :message="message"
              @confirm="handleParameterFixConfirm"
              @cancel="handleParameterFixCancel"
            />
            
            <!-- 参数确认（带 schema 的 confirm 类型） -->
            <ParameterConfirm
              v-else-if="message.type === 'confirm' && hasSchema(message)"
              :message="message"
              @confirm="handleParameterConfirm"
              @cancel="handleParameterCancel"
            />
            
            <!-- 普通系统消息 -->
            <div v-else class="system-message-content">
              <div class="message-content">{{ message.content }}</div>
            </div>
            
            <div class="message-time">{{ formatTime(message.timestamp) }}</div>
          </div>
        </template>
      </div>
      
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-indicator">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>CosmicNova正在努力工作</span>
      </div>
      
      <!-- 底部留白 -->
      <div class="bottom-spacer" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import UniverseAvatar from '../assets/pictures/universe_style1.jpg'
import SystemConfirm from './SystemConfirm.vue'
import ParameterConfirm from './ParameterConfirm.vue'
import ParameterFixDialog from './ParameterFixDialog.vue'
import type { Message } from '../types'
import { hasSchema as checkHasSchema } from '../utils/messageUtils'

interface Props {
  messages: Message[]
  loading: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  confirm: [confirmed: boolean, metadata: any]
  cancel: [metadata: any]
  fixParams: [action: string, params?: any]
}>()

const chatContainer = ref<HTMLElement>()

const formatTime = (date: Date) => {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

const renderContent = (content: string) => {
  if (!content) return ''
  return content
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/(https?:\/\/[^\s]+?\.(jpg|jpeg|png|gif|webp|svg))/gi, '<img src="$1" alt="" onerror="this.onerror=null;this.src=\'/src/assets/pictures/picture_load_fail.png\'">')
    .replace(/\n/g, '<br>')
}

const hasSchema = (message: Message): boolean => {
  return checkHasSchema(message)
}

const handleParameterConfirm = (formData: Record<string, any>) => {
  emit('fixParams', 'confirm', formData)
}

const handleParameterCancel = () => {
  emit('fixParams', 'cancel')
}

const handleParameterFixConfirm = (formData: Record<string, any>) => {
  emit('fixParams', 'confirm', formData)
}

const handleParameterFixCancel = () => {
  emit('fixParams', 'cancel')
}

// 自动滚动到底部
watch(() => props.messages.length, () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
})
</script>

<style scoped>
.chat-area {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  background-color: var(--el-bg-color-page);
}

.messages-container {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-wrapper {
  display: flex;
  gap: 12px;
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-wrapper.assistant {
  justify-content: flex-start;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--el-color-primary);
  color: white;
  flex-shrink: 0;
  margin-top: 4px;
}

.assistant-avatar {
  background-color: var(--el-color-success);
  padding: 0;
  overflow: hidden;
}

.assistant-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.message {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  position: relative;
}

.user-message {
  background-color: var(--el-color-primary);
  color: white;
  border-bottom-right-radius: 4px;
}

.assistant-message {
  background-color: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-bottom-left-radius: 4px;
}

.system-message-content {
  margin-bottom: 8px;
}

.message-header {
  margin-bottom: 4px;
}

.message-sender {
  font-weight: bold;
  font-size: 12px;
  opacity: 0.8;
}

.message-content {
  line-height: 1.6;
  word-wrap: break-word;
  margin-bottom: 8px;
}

.message-content :deep(pre) {
  background-color: var(--el-fill-color);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-content :deep(code) {
  background-color: var(--el-fill-color);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.message-content :deep(img) {
  max-width: 16px;
  max-height: 16px;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  margin: 0 4px;
  object-fit: contain;
  vertical-align: middle;
}

.message-time {
  font-size: 11px;
  opacity: 0.7;
  margin-top: 4px;
  text-align: right;
}

.thinking-container {
  margin-top: 8px;
  font-size: 12px;
}

.thinking-content {
  padding: 8px;
  background-color: var(--el-fill-color-light);
  border-radius: 5px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
  white-space: pre-wrap;
}

.loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  color: var(--el-text-color-secondary);
}

.user-message .message-sender {
  color: rgba(255, 255, 255, 0.8);
}

.user-message .message-time {
  color: rgba(255, 255, 255, 0.6);
}

.system-message .message-sender {
  color: var(--el-color-success);
}

.bottom-spacer {
  height: 80px;
}
</style>
