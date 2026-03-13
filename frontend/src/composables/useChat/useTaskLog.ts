import { ref } from 'vue'
import type { Task } from '../../types'

export function useTaskLog() {
  const tasks = ref<Task[]>([])

  const handleTaskLog = (description: string) => {
    const existingLogTask = tasks.value.find(
    (task: Task) => task.name === '系统日志' && task.status === 'completed'
  )
    
    if (existingLogTask) {
      const existingDesc = existingLogTask.description || ''
      existingLogTask.description = existingDesc 
        ? `${existingDesc}\n${description}` 
        : description
      existingLogTask.latestLog = description
    } else {
      tasks.value.push({
        id: `log_${Date.now()}`,
        name: '系统日志',
        status: 'completed',
        progress: 100,
        description,
        latestLog: description
      })
    }
  }

  const clearTasks = () => {
    tasks.value = []
  }

  const addTask = (task: Task) => {
    tasks.value.push(task)
  }

  const updateTask = (id: string, updates: Partial<Task>) => {
    const task = tasks.value.find((t: Task) => t.id === id)
    if (task) {
      Object.assign(task, updates)
    }
  }

  return {
    tasks,
    handleTaskLog,
    clearTasks,
    addTask,
    updateTask
  }
}
