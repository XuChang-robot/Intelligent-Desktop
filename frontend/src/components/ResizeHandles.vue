<template>
  <div class="resize-handles">
    <div class="resize-handle resize-top" @mousedown="$emit('startResize', 'top', $event)" />
    <div class="resize-handle resize-bottom" @mousedown="$emit('startResize', 'bottom', $event)" />
    <div class="resize-handle resize-left" @mousedown="$emit('startResize', 'left', $event)" />
    <div class="resize-handle resize-right" @mousedown="$emit('startResize', 'right', $event)" />
    <div class="resize-handle resize-topleft" @mousedown="$emit('startResize', 'topleft', $event)" />
    <div class="resize-handle resize-topright" @mousedown="$emit('startResize', 'topright', $event)" />
    <div class="resize-handle resize-bottomleft" @mousedown="$emit('startResize', 'bottomleft', $event)" />
    <div class="resize-handle resize-bottomright" @mousedown="$emit('startResize', 'bottomright', $event)" />
  </div>
</template>

<script setup lang="ts">
import type { ResizeDirection } from '../types'

defineEmits<{
  startResize: [direction: ResizeDirection, event: MouseEvent]
}>()
</script>

<style scoped>
.resize-handles {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 9999;
}

.resize-handle {
  position: absolute;
  pointer-events: auto;
  background: transparent;
  transition: background-color 0.2s;
}

.resize-handle:hover {
  background-color: var(--el-color-primary-light-5);
}

.resize-top {
  top: 0;
  left: 10px;
  right: 10px;
  height: 5px;
  cursor: ns-resize;
}

.resize-bottom {
  bottom: 0;
  left: 10px;
  right: 10px;
  height: 5px;
  cursor: ns-resize;
}

.resize-left {
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 5px;
  cursor: ew-resize;
}

.resize-right {
  right: 0;
  top: 10px;
  bottom: 10px;
  width: 5px;
  cursor: ew-resize;
}

.resize-topleft {
  top: 0;
  left: 0;
  width: 10px;
  height: 10px;
  cursor: nwse-resize;
}

.resize-topright {
  top: 0;
  right: 0;
  width: 10px;
  height: 10px;
  cursor: nesw-resize;
}

.resize-bottomleft {
  bottom: 0;
  left: 0;
  width: 10px;
  height: 10px;
  cursor: nesw-resize;
}

.resize-bottomright {
  bottom: 0;
  right: 0;
  width: 10px;
  height: 10px;
  cursor: nwse-resize;
}
</style>
