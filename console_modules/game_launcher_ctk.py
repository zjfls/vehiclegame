"""
游戏启动模块 - CustomTkinter 版本（支持中文）
"""
import customtkinter as ctk
from typing import List, Dict, Any, Optional
from console_modules.base_module import ConsoleModule


class GameLauncherModule(ConsoleModule):
    """游戏启动模块"""
    
    name = "game_launcher"
    display_name = "启动游戏"
    icon = "🚀"
    description = "启动车辆游戏，支持多车辆配置"
    
    def __init__(self, console_app: Any):
        super().__init__(console_app)
        self.vehicle_configs: List[str] = []
        self.terrain_configs: List[str] = []
        self.selected_vehicle: Optional[str] = None
        self.selected_terrain: Optional[str] = None
        self.is_running: bool = False
        self.game_process_id: Optional[str] = None
        
        # UI 引用
        self.vehicle_combo = None
        self.terrain_combo = None
        self.fullscreen_check = None
        self.debug_check = None
        self.status_label = None
        self.vehicle_info_label = None
        self.start_button = None
        self.stop_button = None
    
    def build_ui(self, parent) -> None:
        """构建 UI"""
        # parent 可能是 ctk.CTkScrollableFrame 或我们的 ScrollableFrame.scrollable_frame
        # 统一作为普通 Frame 处理
        # 标题
        title_label = ctk.CTkLabel(
            parent,
            text="🚀 游戏启动配置",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(20, 10), padx=20, anchor="w")
        
        separator = ctk.CTkFrame(parent, height=2, fg_color="gray")
        separator.pack(fill="x", padx=20, pady=10)
        
        # 车辆配置选择
        vehicle_frame = ctk.CTkFrame(parent, fg_color="transparent")
        vehicle_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            vehicle_frame,
            text="车辆配置:",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=120,
            anchor="w"
        ).pack(side="left")
        
        self.vehicle_combo = ctk.CTkComboBox(
            vehicle_frame,
            values=[],
            width=200,
            command=self._on_vehicle_selected
        )
        self.vehicle_combo.pack(side="left", padx=10)
        
        ctk.CTkButton(
            vehicle_frame,
            text="🔄 刷新",
            width=80,
            command=self._refresh_configs
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            vehicle_frame,
            text="✏️ 编辑",
            width=80,
            command=self._edit_vehicle_config
        ).pack(side="left", padx=5)
        
        # 地形配置选择
        terrain_frame = ctk.CTkFrame(parent, fg_color="transparent")
        terrain_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            terrain_frame,
            text="地形配置:",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=120,
            anchor="w"
        ).pack(side="left")
        
        self.terrain_combo = ctk.CTkComboBox(
            terrain_frame,
            values=[],
            width=200,
            command=self._on_terrain_selected
        )
        self.terrain_combo.pack(side="left", padx=10)
        
        ctk.CTkButton(
            terrain_frame,
            text="🔄 刷新",
            width=80,
            command=self._refresh_configs
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            terrain_frame,
            text="🛠️ 生成",
            width=80,
            command=self._open_terrain_generator
        ).pack(side="left", padx=5)
        
        # 游戏设置
        settings_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        settings_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            settings_frame,
            text="游戏设置:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        self.fullscreen_check = ctk.CTkCheckBox(
            settings_frame,
            text="全屏模式",
            font=ctk.CTkFont(size=14)
        )
        self.fullscreen_check.pack(padx=40, pady=5, anchor="w")
        
        self.debug_check = ctk.CTkCheckBox(
            settings_frame,
            text="调试模式",
            font=ctk.CTkFont(size=14)
        )
        self.debug_check.pack(padx=40, pady=5, anchor="w")
        
        shadows_check = ctk.CTkCheckBox(
            settings_frame,
            text="启用阴影",
            font=ctk.CTkFont(size=14)
        )
        shadows_check.pack(padx=40, pady=5, anchor="w")
        shadows_check.select()  # 默认启用
        
        # 分辨率选择
        resolution_frame = ctk.CTkFrame(parent, fg_color="transparent")
        resolution_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            resolution_frame,
            text="分辨率:",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=120,
            anchor="w"
        ).pack(side="left")
        
        self.resolution_combo = ctk.CTkComboBox(
            resolution_frame,
            values=["1280x720", "1920x1080", "2560x1440", "3840x2160"],
            width=200
        )
        self.resolution_combo.set("1280x720")
        self.resolution_combo.pack(side="left", padx=10)
        
        # 状态显示
        status_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        status_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            status_frame,
            text="状态:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="● 就绪",
            font=ctk.CTkFont(size=18),
            text_color="green"
        )
        self.status_label.pack(padx=40, pady=10, anchor="w")
        
        # 操作按钮
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=20)
        
        self.start_button = ctk.CTkButton(
            button_frame,
            text="▶️ 启动游戏",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=150,
            height=45,
            fg_color="#28a745",
            hover_color="#218838",
            command=self._start_game
        )
        self.start_button.pack(side="left", padx=10)
        
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹️ 停止游戏",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=150,
            height=45,
            fg_color="#dc3545",
            hover_color="#c82333",
            command=self._stop_game,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="📄 查看日志",
            width=120,
            height=45,
            command=self._view_log
        ).pack(side="left", padx=10)
        
        # 车辆预览
        preview_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        preview_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            preview_frame,
            text="车辆预览:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        self.vehicle_info_label = ctk.CTkLabel(
            preview_frame,
            text="请选择一个车辆配置",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.vehicle_info_label.pack(padx=40, pady=10, anchor="w")
        
        # 初始化配置列表
        self._refresh_configs()
    
    def _refresh_configs(self, sender=None) -> None:
        """刷新配置列表"""
        config_mgr = self.get_config_manager()
        if not config_mgr:
            self.log("配置管理器未初始化", "error")
            return
        
        # 加载车辆配置
        self.vehicle_configs = config_mgr.list_configs("vehicles")
        if self.vehicle_combo:
            self.vehicle_combo.configure(values=self.vehicle_configs)
            if self.vehicle_configs and not self.selected_vehicle:
                self.selected_vehicle = self.vehicle_configs[0]
                self.vehicle_combo.set(self.selected_vehicle)
                self._update_vehicle_info()
        
        # 加载地形配置
        self.terrain_configs = config_mgr.list_configs("terrain")
        if self.terrain_combo:
            self.terrain_combo.configure(values=self.terrain_configs)
            if self.terrain_configs and not self.selected_terrain:
                self.selected_terrain = self.terrain_configs[0]
                self.terrain_combo.set(self.selected_terrain)
        
        self.log(f"已加载 {len(self.vehicle_configs)} 个车辆配置", "info")
    
    def _on_vehicle_selected(self, value: str) -> None:
        """车辆选择变更"""
        self.selected_vehicle = value
        self._update_vehicle_info()
    
    def _on_terrain_selected(self, value: str) -> None:
        """地形选择变更"""
        self.selected_terrain = value
    
    def _update_vehicle_info(self) -> None:
        """更新车辆信息预览"""
        if not self.selected_vehicle or not self.vehicle_info_label:
            return
        
        config_mgr = self.get_config_manager()
        if not config_mgr:
            return
        
        try:
            config = config_mgr.load_config("vehicles", self.selected_vehicle)
            name = config.get("name", self.selected_vehicle)
            mass = config.get("vehicle_mass", "N/A")
            max_speed = config.get("physics", {}).get("max_speed", "N/A")
            
            info = f"{name} | 质量：{mass}kg | 最高速度：{max_speed}km/h"
            self.vehicle_info_label.configure(text=info)
        except Exception as e:
            self.vehicle_info_label.configure(text=f"加载失败：{e}")
    
    def _start_game(self) -> None:
        """启动游戏"""
        if self.is_running:
            self.log("游戏已在运行", "warning")
            return
        
        if not self.selected_vehicle:
            self.log("请选择一个车辆配置", "error")
            return
        
        # 构建命令
        cmd_parts = ["python", "main.py"]
        
        if self.selected_vehicle:
            cmd_parts.extend(["--vehicle", self.selected_vehicle])
        
        if self.selected_terrain:
            cmd_parts.extend(["--terrain", self.selected_terrain])
        
        if self.debug_check and self.debug_check.get():
            cmd_parts.append("--debug")
        
        command = " ".join(cmd_parts)
        self.game_process_id = "game_session"
        
        self.log(f"启动游戏：{command}", "info")
        
        if self.status_label:
            self.status_label.configure(text="● 启动中...", text_color="orange")
        
        # 使用进程管理器启动
        process_mgr = self.get_process_manager()
        if process_mgr:
            import subprocess
            
            try:
                self.process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                self.is_running = True
                if self.start_button:
                    self.start_button.configure(state="disabled")
                if self.stop_button:
                    self.stop_button.configure(state="normal")
                if self.status_label:
                    self.status_label.configure(text="● 运行中", text_color="green")
                
                self.log("游戏已启动", "success")
                
                # 启动日志读取线程
                def read_output():
                    for line in self.process.stdout:
                        self.log(f"[游戏] {line.strip()}", "info")
                
                thread = threading.Thread(target=read_output, daemon=True)
                thread.start()
                
            except Exception as e:
                self.log(f"启动失败：{e}", "error")
                if self.status_label:
                    self.status_label.configure(text=f"● 失败：{e}", text_color="red")
        else:
            self.log("进程管理器未初始化", "error")
    
    def _stop_game(self) -> None:
        """停止游戏"""
        if not self.is_running:
            self.log("游戏未运行", "warning")
            return
        
        if hasattr(self, 'process') and self.process:
            self.process.terminate()
            self.log("游戏已停止", "info")
            self.is_running = False
            
            if self.start_button:
                self.start_button.configure(state="normal")
            if self.stop_button:
                self.stop_button.configure(state="disabled")
            if self.status_label:
                self.status_label.configure(text="● 已停止", text_color="gray")
    
    def _edit_vehicle_config(self) -> None:
        """编辑车辆配置"""
        if not self.selected_vehicle:
            self.log("请先选择一个车辆配置", "warning")
            return
        
        self.log(f"编辑配置：{self.selected_vehicle}", "info")
        # TODO: 打开配置编辑器
    
    def _open_terrain_generator(self) -> None:
        """打开地形生成器"""
        self.log("切换到地形生成器", "info")
        if hasattr(self.console_app, 'switch_module'):
            self.console_app.switch_module("terrain_generator")
    
    def _view_log(self) -> None:
        """查看日志"""
        import os
        log_path = "game.log"
        if os.path.exists(log_path):
            self.log(f"日志文件：{log_path}", "info")
            import subprocess
            subprocess.run(["open", log_path])
        else:
            self.log("日志文件不存在", "warning")
    
    def on_show(self) -> None:
        """模块显示时调用"""
        self._refresh_configs()
    
    def cleanup(self) -> None:
        """清理资源"""
        if self.is_running and hasattr(self, 'process'):
            self.process.terminate()
