"""
游戏控制台主应用 - 基于 PySide6 (Qt)

说明：
- macOS 触控板双指滚动由 Qt 原生滚动机制处理（QScrollArea），无需手工绑定 MouseWheel
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import sys
import threading
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from core.config_manager import ConfigManager
from core.process_manager import ProcessManager
from console_modules.base_module import ConsoleModule


class ConsoleApp:
    """控制台应用主类（Qt 实现）"""

    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.config_manager = ConfigManager()
        self.process_manager = ProcessManager()

        self.modules: Dict[str, ConsoleModule] = {}
        self.current_module: Optional[ConsoleModule] = None

        self.running = False
        self.async_loop: Optional[asyncio.AbstractEventLoop] = None
        self.async_thread: Optional[threading.Thread] = None

        self.log_messages: List[str] = []
        self.logger: Optional[logging.Logger] = None

        # Qt refs
        self.app: Optional[QtWidgets.QApplication] = None
        self.window: Optional[QtWidgets.QMainWindow] = None
        self.module_buttons: Dict[str, QtWidgets.QPushButton] = {}
        self.status_bar_label: Optional[QtWidgets.QLabel] = None
        self.content_layout: Optional[QtWidgets.QVBoxLayout] = None
        self.content_container: Optional[QtWidgets.QWidget] = None
        self.scroll_area: Optional[QtWidgets.QScrollArea] = None

    def get_logs_dir(self) -> str:
        logs_dir = os.path.join(self.project_root, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir

    def _setup_logging(self) -> None:
        logs_dir = self.get_logs_dir()
        log_path = os.path.join(logs_dir, "console.log")

        logger = logging.getLogger("vehicle_console")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if not any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", "") == log_path for h in logger.handlers):
            handler = RotatingFileHandler(
                log_path,
                maxBytes=2 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(handler)

        self.logger = logger

    def initialize(self) -> None:
        """初始化应用"""
        print("[Console] 初始化中...")
        self._register_modules()
        self._start_async_loop()
        self._setup_logging()
        print("[Console] 初始化完成!")

    def _register_modules(self) -> None:
        from console_modules.game_launcher import GameLauncherModule
        from console_modules.terrain_generator import TerrainGeneratorModule

        self.modules["game_launcher"] = GameLauncherModule(self)
        self.modules["terrain_generator"] = TerrainGeneratorModule(self)
        print(f"[Console] 已注册 {len(self.modules)} 个模块")

    def _start_async_loop(self) -> None:
        """启动异步事件循环线程（保留给 ProcessManager 使用）"""

        def run_loop():
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)
            self.async_loop.run_forever()

        self.async_thread = threading.Thread(target=run_loop, daemon=True)
        self.async_thread.start()
        print("[Console] 异步循环已启动")

    def run_async(self, coro) -> None:
        if self.async_loop:
            asyncio.run_coroutine_threadsafe(coro, self.async_loop)

    def run(self) -> None:
        """运行应用（Qt event loop）"""
        print("[Console] 启动中...")
        self.running = True

        if QtWidgets.QApplication.instance() is None:
            self.app = QtWidgets.QApplication(sys.argv)
        else:
            self.app = QtWidgets.QApplication.instance()

        # 强制使用 Fusion 样式，确保深色主题、ComboBox 弹层、Checkbox 等在 macOS 下可控
        try:
            self.app.setStyle("Fusion")
            palette = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.Window, QtGui.QColor("#1a1a1a"))
            palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor("#e6e6e6"))
            palette.setColor(QtGui.QPalette.Base, QtGui.QColor("#242424"))
            palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#1f1f1f"))
            palette.setColor(QtGui.QPalette.Text, QtGui.QColor("#e6e6e6"))
            palette.setColor(QtGui.QPalette.Button, QtGui.QColor("#262626"))
            palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor("#e6e6e6"))
            palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor("#2b2b2b"))
            palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor("#e6e6e6"))
            palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#1f6aa5"))
            palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#ffffff"))
            self.app.setPalette(palette)
        except Exception:
            pass

        self.window = QtWidgets.QMainWindow()
        self.window.setWindowTitle("🎮 Vehicle Game Console - 赛车游戏控制台")
        self.window.resize(1200, 800)

        self._apply_dark_theme(self.window)
        self._build_main_window(self.window)

        # 默认显示第一个模块
        if self.modules:
            first_module = list(self.modules.keys())[0]
            self._switch_module(first_module)

        self.window.show()
        exit_code = self.app.exec()
        self.running = False
        print("[Console] 已退出")
        sys.exit(exit_code)

    def _apply_dark_theme(self, window: QtWidgets.QWidget) -> None:
        window.setStyleSheet(
            """
            QWidget { background-color: #1a1a1a; color: #e6e6e6; font-size: 13px; }
            QFrame#Sidebar { background-color: #141414; border-radius: 12px; }
            QLabel#Title { color: #e6e6e6; font-size: 18px; font-weight: 700; }

            /* Buttons */
            QPushButton {
                background-color: #262626;
                border: 1px solid #3a3a3a;
                border-radius: 10px;
                padding: 8px 12px;
            }
            QPushButton:hover { background-color: #2f2f2f; border: 1px solid #4a4a4a; }
            QPushButton:pressed { background-color: #222222; }
            QPushButton:disabled { color: #7a7a7a; background-color: #1f1f1f; border-color: #2a2a2a; }

            QPushButton#NavBtn {
                text-align: left;
                padding: 12px 14px;
                border-radius: 10px;
                background-color: transparent;
                border: 1px solid transparent;
            }
            QPushButton#NavBtn:hover { background-color: #2a2a2a; }
            QPushButton#NavBtn[active="true"] { background-color: #1f6aa5; }

            /* Scrollbar */
            QScrollArea { border: none; }
            QScrollBar:vertical {
                background: #1a1a1a;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3a3a3a;
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover { background: #4a4a4a; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

            /* Inputs */
            QLineEdit, QTextEdit {
                background-color: #242424;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 7px 10px;
                selection-background-color: #1f6aa5;
            }

            QComboBox {
                background-color: #242424;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 7px 10px;
                padding-right: 30px;
                combobox-popup: 0;
            }
            QComboBox:hover { border: 1px solid #4a4a4a; }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left: 1px solid #3a3a3a;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background: #242424;
            }
            QComboBox::down-arrow { width: 10px; height: 10px; }
            QComboBox QAbstractItemView {
                background-color: #242424;
                color: #e6e6e6;
                selection-background-color: #1f6aa5;
                selection-color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                outline: 0;
            }
            QComboBox QAbstractItemView::item { padding: 8px 10px; }

            /* Checkbox */
            QCheckBox { spacing: 10px; }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #6a6a6a;
                background-color: #1f1f1f;
            }
            QCheckBox::indicator:hover { border: 1px solid #a0a0a0; }
            QCheckBox::indicator:checked {
                background-color: #1f6aa5;
                border: 1px solid #1f6aa5;
            }
            QCheckBox::indicator:checked:hover { background-color: #2580c8; }

            /* Group box */
            QGroupBox {
                border: 1px solid #2f2f2f;
                border-radius: 12px;
                margin-top: 18px;
                padding: 14px;
                background-color: #202020;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #e6e6e6;
            }

            /* Tooltip */
            QToolTip {
                background-color: #2b2b2b;
                color: #e6e6e6;
                border: 1px solid #3a3a3a;
                padding: 6px 8px;
                border-radius: 8px;
            }
            """
        )

    def _build_main_window(self, window: QtWidgets.QMainWindow) -> None:
        central = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(central)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        top = QtWidgets.QWidget()
        top_layout = QtWidgets.QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        # Sidebar
        sidebar = QtWidgets.QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(10)

        title = QtWidgets.QLabel("🎮 Vehicle Console")
        title.setObjectName("Title")
        sidebar_layout.addWidget(title)

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #333333;")
        sidebar_layout.addWidget(line)

        nav = QtWidgets.QWidget()
        nav_layout = QtWidgets.QVBoxLayout(nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)

        for module_name, module in self.modules.items():
            btn = QtWidgets.QPushButton(f"{module.icon} {module.display_name}")
            btn.setObjectName("NavBtn")
            btn.setProperty("active", False)
            btn.clicked.connect(lambda checked=False, name=module_name: self._switch_module(name))
            self.module_buttons[module_name] = btn
            nav_layout.addWidget(btn)

        nav_layout.addStretch(1)
        sidebar_layout.addWidget(nav, 1)

        # Status (sidebar)
        status_box = QtWidgets.QGroupBox("状态")
        status_layout = QtWidgets.QVBoxLayout(status_box)
        self.status_bar_label = QtWidgets.QLabel("就绪")
        self.status_bar_label.setStyleSheet("color: #00ff00;")
        status_layout.addWidget(self.status_bar_label)
        sidebar_layout.addWidget(status_box)

        version = QtWidgets.QLabel("v0.2.1 | Python 3.13")
        version.setStyleSheet("color: #777777; font-size: 11px;")
        sidebar_layout.addWidget(version)

        # Content (scroll)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.content_container = QtWidgets.QWidget()
        self.content_layout = QtWidgets.QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(18, 18, 18, 18)
        self.content_layout.setSpacing(14)
        self.content_layout.addStretch(1)

        self.scroll_area.setWidget(self.content_container)

        top_layout.addWidget(sidebar)
        top_layout.addWidget(self.scroll_area, 1)

        # Bottom status bar
        bottom = QtWidgets.QFrame()
        bottom.setFixedHeight(44)
        bottom_layout = QtWidgets.QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(14, 8, 14, 8)
        bottom_layout.setSpacing(8)
        self.bottom_status = QtWidgets.QLabel("就绪")
        bottom_layout.addWidget(self.bottom_status, 1)

        root_layout.addWidget(top, 1)
        root_layout.addWidget(bottom, 0)

        window.setCentralWidget(central)

    def _clear_layout(self, layout: QtWidgets.QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def _switch_module(self, module_name: str) -> None:
        if module_name not in self.modules:
            self.log_message(f"模块不存在：{module_name}", "error")
            return

        if self.current_module:
            self.current_module.on_hide()

        for name, btn in self.module_buttons.items():
            btn.setProperty("active", name == module_name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.current_module = self.modules[module_name]

        if not self.content_layout or not self.content_container:
            return

        self._clear_layout(self.content_layout)
        # 重新加 stretch，确保内容贴顶且可滚动
        self.current_module.build_ui(self.content_layout)
        self.content_layout.addStretch(1)

        self.current_module.on_show()
        self.log_message(f"切换到：{self.current_module.display_name}", "info")

        try:
            if self.scroll_area:
                self.scroll_area.verticalScrollBar().setValue(0)
        except Exception:
            pass

    def switch_module(self, module_name: str) -> None:
        if self.app:
            QtCore.QTimer.singleShot(0, lambda: self._switch_module(module_name))
        else:
            self._switch_module(module_name)

    def log_message(self, message: str, level: str = "info") -> None:
        import datetime

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        self.log_messages.append(log_entry)
        if len(self.log_messages) > 200:
            self.log_messages = self.log_messages[-200:]

        color_map = {
            "info": "#00ff00",
            "warning": "#ffa500",
            "error": "#ff4444",
            "success": "#00ff00",
        }

        if self.bottom_status:
            self.bottom_status.setText(f"状态：{message[:80]}")

        if self.status_bar_label:
            self.status_bar_label.setText(f"● {message[:40]}")
            self.status_bar_label.setStyleSheet(f"color: {color_map.get(level, '#ffffff')};")

        if self.logger:
            level_map = {
                "info": logging.INFO,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "success": logging.INFO,
            }
            try:
                self.logger.log(level_map.get(level, logging.INFO), message)
            except Exception:
                pass

        print(log_entry)

    def _exit_app(self) -> None:
        self.log_message("正在退出...", "info")

        for module in self.modules.values():
            try:
                module.cleanup()
            except Exception:
                pass

        if self.async_loop:
            try:
                self.async_loop.call_soon_threadsafe(self.async_loop.stop)
            except Exception:
                pass

        self.running = False
        if self.app:
            self.app.quit()


def main() -> None:
    try:
        import PySide6  # noqa: F401
    except ImportError:
        print("错误：PySide6 未安装")
        print("请运行：pip install PySide6")
        sys.exit(1)

    # macOS: 提升字体渲染一致性
    if platform.system() == "Darwin":
        QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = ConsoleApp()
    app.initialize()
    app.run()


if __name__ == "__main__":
    main()
