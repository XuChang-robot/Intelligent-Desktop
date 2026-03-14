declare global {
  interface Window {
    pywebview?: {
      api: {
        send_message: (message: string) => Promise<any>
        get_models: () => Promise<any>
        get_history: (limit: number) => Promise<any>
        confirm_elicitation: (message: string, content: any, confirmed: boolean) => Promise<any>
        fix_parameters: (action: string, params?: any) => Promise<any>
        get_system_info: () => Promise<any>
        minimize_window: () => void
        maximize_window: () => void
        restore_window: () => void
        restore_and_resize: (newWidth?: number, newHeight?: number, newX?: number, newY?: number) => Promise<any>
        close_window: () => void
        move_window: (x: number, y: number) => Promise<any>
        resize_window_with_fixpoint: (width: number, height: number, fixPoint: string) => Promise<any>
        get_window_position: () => Promise<{x: number, y: number}>
        get_window_rect: () => Promise<{x: number, y: number, width: number, height: number}>
        toggle_fullscreen: () => void
        interrupt: () => Promise<any>
        set_model: (model: string) => Promise<any>
        register_callback?: (name: string, callback: (event_type: string, data: any) => void) => void
      }
    }
    setStatus?: (message: string) => void
    setLoading?: (isLoading: boolean, message?: string) => void
    setProgress?: (value: number) => void
  }
}

export {}
