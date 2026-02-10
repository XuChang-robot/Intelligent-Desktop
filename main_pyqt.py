# 智能桌面系统主入口 (PyQt6版本)

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.pyqt_app import App

if __name__ == "__main__":
    app = App()
    app.run()
