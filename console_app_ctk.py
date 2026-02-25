"""
游戏控制台主应用 - 基于 CustomTkinter (macOS 触控板完美支持)
"""
import customtkinter as ctk
import tkinter as tk
from typing import Optional, Dict, Any, List
import asyncio
import threading
import os
import sys
import platform

from core.config_manager import ConfigManager
from core.process_manager import ProcessManager
from console_modules.base_module import ConsoleModule


class ScrollableFrame(ctk.CTkFrame):
    """
    自定义可滚动框架，完美支持 macOS 触控板
    使用原生 Tkinter Canvas + Mousewheel 绑定
    """
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._scroll_bind_ids: Dict[str, str] = {}
        
        # 创建 Canvas 和 Scrollbar
        self.canvas = tk.Canvas(
            self,
            bg=self._apply_appearance_mode(self._bg_color),
            highlightthickness=0,
            relief='flat',
            borderwidth=0
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # 滚动条
        self.scrollbar = ctk.CTkScrollbar(
            self,
            command=self.canvas.yview,
            fg_color="transparent"
        )
        self.scrollbar.pack(side="right", fill="y")
        
        # 配置 Canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 内部框架（放置内容的地方）
        self.scrollable_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")
        
        # 在 Canvas 中创建窗口
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )
        
        # 绑定配置事件
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure, add="+")
        self.canvas.bind("<Configure>", self._on_canvas_configure, add="+")
        
        # 滚动支持（macOS 触控板 / 鼠标滚轮 / Linux Button-4/5）
        self._enable_scroll()
    
    def _enable_scroll(self) -> None:
        """
        绑定滚动事件到 toplevel（而不是逐个子控件绑定）。
        这样可以兼容 CustomTkinter 内部封装的真实 Tk 控件（例如 CTkEntry/CTkTextbox）。
        """
        try:
            toplevel = self.winfo_toplevel()
        except Exception:
            return

        # 使用 toplevel 绑定，便于 unbind（比 bind_all 更可控）
        self._scroll_bind_ids["<MouseWheel>"] = toplevel.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self._scroll_bind_ids["<Button-4>"] = toplevel.bind("<Button-4>", self._on_button_scroll, add="+")
        self._scroll_bind_ids["<Button-5>"] = toplevel.bind("<Button-5>", self._on_button_scroll, add="+")
    
    def _event_targets_self(self, event) -> bool:
        """仅当指针位于本 ScrollableFrame 内部时才处理滚动（避免影响其它区域）。"""
        try:
            x_root = event.x_root
            y_root = event.y_root
        except Exception:
            return False
        
        # 优先用几何命中测试（对 CustomTkinter 内部嵌套的真实 Tk 控件更稳）
        try:
            left = self.winfo_rootx()
            top = self.winfo_rooty()
            right = left + self.winfo_width()
            bottom = top + self.winfo_height()
            if left <= x_root <= right and top <= y_root <= bottom:
                return True
        except Exception:
            pass

        # 兜底：用 widget master 链判断
        try:
            toplevel = self.winfo_toplevel()
            widget = toplevel.winfo_containing(x_root, y_root)
        except Exception:
            return False

        while widget is not None:
            if widget == self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def destroy(self) -> None:
        """销毁时解除滚动绑定，避免重复绑定造成加速滚动。"""
        try:
            toplevel = self.winfo_toplevel()
            for sequence, bind_id in list(self._scroll_bind_ids.items()):
                try:
                    toplevel.unbind(sequence, bind_id)
                except Exception:
                    pass
        finally:
            self._scroll_bind_ids.clear()
            super().destroy()
    
    def _on_mousewheel(self, event):
        """处理鼠标滚轮/触控板事件"""
        if not self._event_targets_self(event):
            return None

        # 如果指针在可独立滚动的控件上（例如 Text），优先让它自己处理，避免双滚动
        try:
            if isinstance(event.widget, tk.Text) and event.widget is not self.canvas:
                return None
        except Exception:
            pass

        delta_raw = getattr(event, "delta", 0)
        if not delta_raw:
            return None

        system = platform.system()
        if system == "Darwin":
            # macOS: delta 可能是较小的整数（或带惯性的较大值），不要除以 120
            units = int(-round(float(delta_raw)))
            if units == 0:
                units = -1 if delta_raw > 0 else 1
        else:
            # Windows: delta 通常是 120 的倍数；其它平台也尽量按这个逻辑降速
            units = int(-round(float(delta_raw) / 120.0))

        if units:
            self.canvas.yview_scroll(units, "units")
            return "break"
        return None
    
    def _on_button_scroll(self, event):
        """处理 Button-4/Button-5 事件（旧式滚轮）"""
        if not self._event_targets_self(event):
            return None

        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        return "break"
    
    def _on_frame_configure(self, event):
        """框架大小改变时更新 Canvas 滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        """Canvas 大小改变时调整内部框架宽度"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def yview_moveto(self, value):
        """滚动到指定位置（0-1）"""
        self.canvas.yview_moveto(value)
    
    def yview_scroll(self, number, what):
        """滚动指定单位"""
        self.canvas.yview_scroll(number, what)


class ConsoleApp:
    """控制台应用主类"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.process_manager = ProcessManager()
        self.modules: Dict[str, ConsoleModule] = {}
        self.current_module: Optional[ConsoleModule] = None
        self.running = False
        self.async_loop: Optional[asyncio.AbstractEventLoop] = None
        self.async_thread: Optional[threading.Thread] = None
        
        # UI 引用
        self.module_buttons: Dict[str, ctk.CTkButton] = {}
        self.module_content_frame = None
        self.status_label = None
        self.log_messages: List[str] = []
        self.is_macos = platform.system() == "Darwin"
    
    def initialize(self) -> None:
        """初始化应用"""
        print("[Console] 初始化中...")
        self._register_modules()
        self._start_async_loop()
        print("[Console] 初始化完成!")
    
    def _register_modules(self) -> None:
        """注册功能模块"""
        from console_modules.game_launcher_ctk import GameLauncherModule
        from console_modules.terrain_generator_ctk import TerrainGeneratorModule
        
        self.modules["game_launcher"] = GameLauncherModule(self)
        self.modules["terrain_generator"] = TerrainGeneratorModule(self)
        
        print(f"[Console] 已注册 {len(self.modules)} 个模块")
    
    def _start_async_loop(self) -> None:
        """启动异步事件循环线程"""
        def run_loop():
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)
            self.async_loop.run_forever()
        
        self.async_thread = threading.Thread(target=run_loop, daemon=True)
        self.async_thread.start()
        print("[Console] 异步循环已启动")
    
    def run(self) -> None:
        """运行应用"""
        print("[Console] 启动中...")
        
        # 创建主窗口
        self.root = ctk.CTk()
        self.root.title("🎮 Vehicle Game Console - 赛车游戏控制台")
        self.root.geometry("1100x750")
        
        # macOS 优化
        if self.is_macos:
            # 启用 macOS 原生外观
            self.root.configure(bg="#1a1a1a")
        
        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 构建界面
        self._build_main_window()
        
        self.running = True
        
        # 默认显示第一个模块
        if self.modules:
            first_module = list(self.modules.keys())[0]
            self._switch_module(first_module)
        
        # 启动主循环
        self.root.mainloop()
        
        print("[Console] 已退出")
    
    def _build_main_window(self) -> None:
        """构建主窗口"""
        # 配置网格布局
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # ===== 左侧导航面板 =====
        self.sidebar_frame = ctk.CTkFrame(self.root, width=220, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)
        
        # 标题
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="🎮 Vehicle Console",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))
        
        # 分隔线
        separator = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="gray40")
        separator.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        
        # 模块按钮区域
        self.button_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        
        # 创建模块按钮
        for idx, (module_name, module) in enumerate(self.modules.items()):
            btn = ctk.CTkButton(
                self.button_frame,
                text=f"{module.icon} {module.display_name}",
                font=ctk.CTkFont(size=14),
                height=50,
                corner_radius=10,
                command=lambda name=module_name: self._switch_module(name),
                anchor="w",
                hover_color="#3b3b3b"
            )
            btn.grid(row=idx, column=0, padx=5, pady=5, sticky="ew")
            self.module_buttons[module_name] = btn
        
        # 底部状态区域
        self.status_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.status_frame.grid(row=3, column=0, padx=20, pady=(20, 20), sticky="ew")
        
        ctk.CTkLabel(
            self.status_frame,
            text="状态：",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        ).pack(anchor="w")
        
        self.status_text = ctk.CTkLabel(
            self.status_frame,
            text="● 就绪",
            font=ctk.CTkFont(size=12),
            text_color="#00ff00"
        )
        self.status_text.pack(anchor="w", pady=(5, 0))
        
        # 版本信息
        ctk.CTkLabel(
            self.sidebar_frame,
            text="v0.2.1 | Python 3.13",
            font=ctk.CTkFont(size=10),
            text_color="gray50"
        ).grid(row=4, column=0, padx=20, pady=(0, 20), sticky="sw")
        
        # ===== 右侧内容区域（使用自定义滚动框架）=====
        self.content_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        # 使用自定义 ScrollableFrame（支持 macOS 触控板）
        self.module_content_frame = ScrollableFrame(
            self.content_frame,
            corner_radius=10,
            fg_color="#2b2b2b"
        )
        self.module_content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ===== 底部状态栏 =====
        self.status_bar = ctk.CTkFrame(self.root, height=40, corner_radius=0, fg_color="#1a1a1a")
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_bar.grid_propagate(False)
        
        self.status_bar_label = ctk.CTkLabel(
            self.status_bar,
            text="就绪",
            font=ctk.CTkFont(size=12),
            text_color="white"
        )
        self.status_bar_label.pack(side="left", padx=20, pady=10)
    
    def _switch_module(self, module_name: str) -> None:
        """切换模块"""
        if module_name not in self.modules:
            self.log_message(f"模块不存在：{module_name}", "error")
            return
        
        # 隐藏当前模块
        if self.current_module:
            self.current_module.on_hide()
        
        # 更新按钮状态
        for name, btn in self.module_buttons.items():
            if name == module_name:
                btn.configure(fg_color="#1f6aa5")
            else:
                btn.configure(fg_color="transparent", hover_color="#3b3b3b")
        
        # 切换到新模块
        self.current_module = self.modules[module_name]
        
        # 清空内容区
        for widget in self.module_content_frame.scrollable_frame.winfo_children():
            widget.destroy()
        
        # 构建新模块 UI
        self.current_module.build_ui(self.module_content_frame.scrollable_frame)
        self.current_module.on_show()
        
        self.log_message(f"切换到：{self.current_module.display_name}", "info")
    
    def switch_module(self, module_name: str) -> None:
        """外部调用的模块切换方法"""
        self.root.after(0, lambda: self._switch_module(module_name))
    
    def log_message(self, message: str, level: str = "info") -> None:
        """记录日志"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        self.log_messages.append(log_entry)
        
        if len(self.log_messages) > 100:
            self.log_messages = self.log_messages[-100:]
        
        color_map = {
            "info": "#00ff00",
            "warning": "#ffa500",
            "error": "#ff4444",
            "success": "#00ff00",
        }
        
        if hasattr(self, 'status_bar_label'):
            self.status_bar_label.configure(
                text=f"状态：{message[:60]}",
                text_color=color_map.get(level, "white")
            )
        
        print(log_entry)
    
    def run_async(self, coro) -> None:
        """运行异步协程"""
        if self.async_loop:
            asyncio.run_coroutine_threadsafe(coro, self.async_loop)
    
    def _exit_app(self) -> None:
        """退出应用"""
        self.log_message("正在退出...", "info")
        
        for module in self.modules.values():
            module.cleanup()
        
        if self.async_loop:
            self.async_loop.call_soon_threadsafe(self.async_loop.stop)
        
        self.running = False
        self.root.quit()
        self.root.destroy()


def main():
    """入口函数"""
    try:
        import customtkinter
    except ImportError:
        print("错误：CustomTkinter 未安装")
        print("请运行：pip install customtkinter")
        sys.exit(1)
    
    app = ConsoleApp()
    app.initialize()
    app.run()


if __name__ == "__main__":
    main()
