"""
地形生成模块 - CustomTkinter 版本（支持中文）
"""
import customtkinter as ctk
from typing import Optional, List, Any
from console_modules.base_module import ConsoleModule


class TerrainGeneratorModule(ConsoleModule):
    """地形生成模块"""
    
    name = "terrain_generator"
    display_name = "地形生成"
    icon = "🛠️"
    description = "生成程序化地形高度图"
    
    def __init__(self, console_app: Any):
        super().__init__(console_app)
        self.is_generating = False
        
        # 参数
        self.width = 1024
        self.height = 1024
        self.seed = 12345
        self.noise_scale = 0.05
        self.octaves = 5
        self.persistence = 0.5
        self.lacunarity = 2.0
        self.height_scale = 20.0
        
        # 轨道参数
        self.use_track = False
        self.track_csv = "scripts/track_example.csv"
        self.corridor_width = 120
        self.edge_falloff = 50
        
        # 输出
        self.output_name = "generated_terrain"
        
        # UI 引用
        self.status_label = None
        self.progress_bar = None
        self.generate_button = None
        self.log_text = None
        self.log_messages: List[str] = []
        
        # 输入控件引用
        self.width_entry = None
        self.height_entry = None
        self.seed_entry = None
        self.track_check = None
        self.track_frame = None
    
    def build_ui(self, parent) -> None:
        """构建 UI"""
        # parent 可能是 ctk.CTkScrollableFrame 或我们的 ScrollableFrame.scrollable_frame
        # 标题
        title_label = ctk.CTkLabel(
            parent,
            text="🛠️ 地形参数配置",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(20, 10), padx=20, anchor="w")
        
        separator = ctk.CTkFrame(parent, height=2, fg_color="gray")
        separator.pack(fill="x", padx=20, pady=10)
        
        # ===== 基本参数 =====
        basic_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        basic_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            basic_frame,
            text="基本参数:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        params_frame = ctk.CTkFrame(basic_frame, fg_color="transparent")
        params_frame.pack(fill="x", padx=20, pady=10)
        
        # 宽度
        width_frame = ctk.CTkFrame(params_frame, fg_color="transparent")
        width_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(
            width_frame,
            text="宽度 (px):",
            width=120,
            anchor="w"
        ).pack(side="left")
        self.width_entry = ctk.CTkEntry(
            width_frame,
            width=120,
            textvariable=ctk.StringVar(value=str(self.width))
        )
        self.width_entry.pack(side="left", padx=10)
        
        # 高度
        height_frame = ctk.CTkFrame(params_frame, fg_color="transparent")
        height_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(
            height_frame,
            text="高度 (px):",
            width=120,
            anchor="w"
        ).pack(side="left")
        self.height_entry = ctk.CTkEntry(
            height_frame,
            width=120,
            textvariable=ctk.StringVar(value=str(self.height))
        )
        self.height_entry.pack(side="left", padx=10)
        
        # 种子
        seed_frame = ctk.CTkFrame(params_frame, fg_color="transparent")
        seed_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(
            seed_frame,
            text="种子:",
            width=120,
            anchor="w"
        ).pack(side="left")
        self.seed_entry = ctk.CTkEntry(
            seed_frame,
            width=120,
            textvariable=ctk.StringVar(value=str(self.seed))
        )
        self.seed_entry.pack(side="left", padx=10)
        
        # ===== 噪声参数 =====
        noise_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        noise_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            noise_frame,
            text="噪声参数:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        noise_params = ctk.CTkFrame(noise_frame, fg_color="transparent")
        noise_params.pack(fill="x", padx=20, pady=10)
        
        # 噪声缩放
        scale_frame = ctk.CTkFrame(noise_params, fg_color="transparent")
        scale_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(
            scale_frame,
            text="噪声缩放:",
            width=120,
            anchor="w"
        ).pack(side="left")
        self.noise_scale_entry = ctk.CTkEntry(
            scale_frame,
            width=120,
            textvariable=ctk.StringVar(value=str(self.noise_scale))
        )
        self.noise_scale_entry.pack(side="left", padx=10)
        
        # 八度音
        octaves_frame = ctk.CTkFrame(noise_params, fg_color="transparent")
        octaves_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(
            octaves_frame,
            text="八度音:",
            width=120,
            anchor="w"
        ).pack(side="left")
        self.octaves_entry = ctk.CTkEntry(
            octaves_frame,
            width=120,
            textvariable=ctk.StringVar(value=str(self.octaves))
        )
        self.octaves_entry.pack(side="left", padx=10)
        
        # 持久性
        pers_frame = ctk.CTkFrame(noise_params, fg_color="transparent")
        pers_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(
            pers_frame,
            text="持久性:",
            width=120,
            anchor="w"
        ).pack(side="left")
        self.persistence_entry = ctk.CTkEntry(
            pers_frame,
            width=120,
            textvariable=ctk.StringVar(value=str(self.persistence))
        )
        self.persistence_entry.pack(side="left", padx=10)
        
        # ===== 高度参数 =====
        height_param_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        height_param_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            height_param_frame,
            text="高度参数:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        height_scale_f = ctk.CTkFrame(height_param_frame, fg_color="transparent")
        height_scale_f.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            height_scale_f,
            text="高度缩放:",
            width=120,
            anchor="w"
        ).pack(side="left")
        self.height_scale_entry = ctk.CTkEntry(
            height_scale_f,
            width=120,
            textvariable=ctk.StringVar(value=str(self.height_scale))
        )
        self.height_scale_entry.pack(side="left", padx=10)
        
        # ===== 轨道走廊选项 =====
        track_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        track_frame.pack(fill="x", padx=20, pady=15)
        
        self.track_check = ctk.CTkCheckBox(
            track_frame,
            text="启用赛道走廊刷平",
            font=ctk.CTkFont(size=16),
            command=self._toggle_track_options
        )
        self.track_check.pack(padx=20, pady=15, anchor="w")
        
        # 轨道参数（默认禁用）
        self.track_frame = ctk.CTkFrame(track_frame, fg_color="transparent")
        self.track_frame.pack(fill="x", padx=40, pady=10)
        self.track_frame.pack_forget()  # 初始隐藏
        
        # CSV 文件
        csv_f = ctk.CTkFrame(self.track_frame, fg_color="transparent")
        csv_f.pack(fill="x", pady=5)
        ctk.CTkLabel(
            csv_f,
            text="CSV 文件:",
            width=120,
            anchor="w"
        ).pack(side="left")
        self.track_csv_entry = ctk.CTkEntry(
            csv_f,
            width=300,
            textvariable=ctk.StringVar(value=self.track_csv)
        )
        self.track_csv_entry.pack(side="left", padx=10)
        
        # 走廊宽度
        corridor_f = ctk.CTkFrame(self.track_frame, fg_color="transparent")
        corridor_f.pack(fill="x", pady=5)
        ctk.CTkLabel(
            corridor_f,
            text="走廊宽度 (px):",
            width=120,
            anchor="w"
        ).pack(side="left")
        self.corridor_entry = ctk.CTkEntry(
            corridor_f,
            width=120,
            textvariable=ctk.StringVar(value=str(self.corridor_width))
        )
        self.corridor_entry.pack(side="left", padx=10)
        
        # 边缘衰减
        edge_f = ctk.CTkFrame(self.track_frame, fg_color="transparent")
        edge_f.pack(fill="x", pady=5)
        ctk.CTkLabel(
            edge_f,
            text="边缘衰减 (px):",
            width=120,
            anchor="w"
        ).pack(side="left")
        self.edge_entry = ctk.CTkEntry(
            edge_f,
            width=120,
            textvariable=ctk.StringVar(value=str(self.edge_falloff))
        )
        self.edge_entry.pack(side="left", padx=10)
        
        # ===== 输出文件名 =====
        output_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        output_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            output_frame,
            text="输出文件名:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        output_f = ctk.CTkFrame(output_frame, fg_color="transparent")
        output_f.pack(fill="x", padx=20, pady=10)
        
        self.output_entry = ctk.CTkEntry(
            output_f,
            width=300,
            textvariable=ctk.StringVar(value=self.output_name)
        )
        self.output_entry.pack(side="left", padx=10)
        ctk.CTkLabel(
            output_f,
            text="（不含扩展名）",
            text_color="gray"
        ).pack(side="left")
        
        # ===== 状态显示 =====
        status_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        status_frame.pack(fill="x", padx=20, pady=15)
        
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
        
        self.progress_bar = ctk.CTkProgressBar(
            status_frame,
            mode="determinate"
        )
        self.progress_bar.pack(padx=40, pady=10, fill="x")
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()  # 初始隐藏
        
        # ===== 操作按钮 =====
        button_frame = ctk.CTkFrame(parent, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=20)
        
        self.generate_button = ctk.CTkButton(
            button_frame,
            text="▶️ 生成地形",
            font=ctk.CTkFont(size=16, weight="bold"),
            width=150,
            height=45,
            fg_color="#28a745",
            hover_color="#218838",
            command=self._generate_terrain
        )
        self.generate_button.pack(side="left", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="📁 打开输出目录",
            width=150,
            height=45,
            command=self._open_output_dir
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="📖 查看文档",
            width=120,
            height=45,
            command=self._view_docs
        ).pack(side="left", padx=10)
        
        # ===== 日志区域 =====
        log_frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=10)
        log_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        ctk.CTkLabel(
            log_frame,
            text="生成日志:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=20, pady=(15, 10), anchor="w")
        
        self.log_text = ctk.CTkTextbox(
            log_frame,
            height=150,
            font=ctk.CTkFont(family="Courier", size=12)
        )
        self.log_text.pack(fill="both", expand=True, padx=20, pady=10)
    
    def _toggle_track_options(self) -> None:
        """切换轨道选项显示"""
        self.use_track = self.track_check.get()
        if self.use_track:
            self.track_frame.pack(fill="x", padx=40, pady=10, after=self.track_check.master.master)
        else:
            self.track_frame.pack_forget()
    
    def _generate_terrain(self) -> None:
        """生成地形"""
        if self.is_generating:
            self.log("地形正在生成中", "warning")
            return
        
        # 获取参数
        try:
            self.width = int(self.width_entry.get())
            self.height = int(self.height_entry.get())
            self.seed = int(self.seed_entry.get())
            self.noise_scale = float(self.noise_scale_entry.get())
            self.octaves = int(self.octaves_entry.get())
            self.persistence = float(self.persistence_entry.get())
            self.height_scale = float(self.height_scale_entry.get())
            self.output_name = self.output_entry.get()
        except ValueError as e:
            self.log(f"参数格式错误：{e}", "error")
            return
        
        if not self.output_name:
            self.log("请输入输出文件名", "error")
            return
        
        self.is_generating = True
        if self.generate_button:
            self.generate_button.configure(state="disabled")
        if self.status_label:
            self.status_label.configure(text="● 生成中...", text_color="orange")
        if self.progress_bar:
            self.progress_bar.pack(padx=40, pady=10, fill="x")
            self.progress_bar.set(0)
        
        # 构建命令
        cmd_parts = [
            "python", "scripts/generate_terrain.py",
            f"--width={self.width}",
            f"--height={self.height}",
            f"--seed={self.seed}",
            f"--name={self.output_name}",
            f"--noise-scale={self.noise_scale}",
            f"--octaves={self.octaves}",
            f"--persistence={self.persistence}",
            f"--lacunarity={self.lacunarity}",
            f"--height-scale={self.height_scale}",
        ]
        
        if self.use_track:
            self.track_csv = self.track_csv_entry.get()
            self.corridor_width = int(self.corridor_entry.get())
            self.edge_falloff = int(self.edge_entry.get())
            
            cmd_parts.extend([
                f"--track-csv={self.track_csv}",
                f"--corridor-width-px={self.corridor_width}",
                f"--edge-falloff-px={self.edge_falloff}",
            ])
        
        command = " ".join(cmd_parts)
        self.log(f"命令：{command}", "info")
        
        # 执行命令
        import subprocess
        
        def run_command():
            try:
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                for line in proc.stdout:
                    self.log(line.strip(), "info")
                
                proc.wait()
                
                if proc.returncode == 0:
                    self.log("地形生成完成！", "success")
                    if self.status_label:
                        self.status_label.configure(text="● 成功", text_color="green")
                    if self.progress_bar:
                        self.progress_bar.set(1.0)
                else:
                    self.log(f"生成失败，退出码：{proc.returncode}", "error")
                    if self.status_label:
                        self.status_label.configure(text="● 失败", text_color="red")
                
            except Exception as e:
                self.log(f"生成失败：{e}", "error")
                if self.status_label:
                    self.status_label.configure(text=f"● 错误：{e}", text_color="red")
            finally:
                self.is_generating = False
                if self.generate_button:
                    self.generate_button.configure(state="normal")
        
        # 在新线程中运行
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
    
    def _open_output_dir(self) -> None:
        """打开输出目录"""
        import subprocess
        import os
        output_dir = "res/terrain"
        if os.path.exists(output_dir):
            subprocess.run(["open", output_dir])
            self.log(f"已打开目录：{output_dir}", "info")
        else:
            self.log(f"目录不存在：{output_dir}", "warning")
    
    def _view_docs(self) -> None:
        """查看文档"""
        self.log("查看 README.md 了解地形生成文档", "info")
    
    def log(self, message: str, level: str = "info") -> None:
        """记录日志到 UI"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{level.upper()}] {message}"
        self.log_messages.append(log_entry)
        
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]
        
        if self.log_text:
            self.log_text.insert("end", log_entry + "\n")
            self.log_text.see("end")
        
        # 调用父类日志
        super().log(message, level)
    
    def cleanup(self) -> None:
        """清理资源"""
        if self.is_generating:
            process_mgr = self.get_process_manager()
            if process_mgr:
                import asyncio
                async def cancel():
                    await process_mgr.kill_process("terrain_gen")
                if hasattr(self.console_app, 'run_async'):
                    self.console_app.run_async(cancel())
