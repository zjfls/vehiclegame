"""
地图生成模块 - PySide6 (Qt) 版本
支持分步生成、依赖管理、配置保存/加载
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6 import QtCore, QtWidgets

from console_modules.base_module import ConsoleModule
from core.map_config_manager import MapConfigManager, MapConfig, MapModuleConfig
from core.map_generator_orchestrator import MapGeneratorOrchestrator
from generators import (
    TerrainGenerationStep,
    ColorGenerationStep,
    TrackGenerationStep,
    SceneryGenerationStep,
    create_all_steps
)


class MapGeneratorModule(ConsoleModule):
    """地图生成模块"""
    
    name = "map_generator"
    display_name = "地图生成"
    icon = "🗺️"
    description = "生成完整地图配置（地形/颜色/赛道/场景）"
    
    def __init__(self, console_app: Any):
        super().__init__(console_app)
        
        # 管理器
        self.config_manager = MapConfigManager()
        self.orchestrator = MapGeneratorOrchestrator()
        
        # 当前配置
        self.current_config: Optional[MapConfig] = None
        self.current_config_name: Optional[str] = None
        
        # UI 引用
        self.module_group_widgets: Dict[str, QtWidgets.QGroupBox] = {}
        self.module_status_labels: Dict[str, QtWidgets.QLabel] = {}
        self.module_progress_bars: Dict[str, QtWidgets.QProgressBar] = {}
        self.module_generate_buttons: Dict[str, QtWidgets.QPushButton] = {}
        self.module_preview_buttons: Dict[str, QtWidgets.QPushButton] = {}
        
        # 配置输入控件
        self.config_inputs: Dict[str, Dict[str, QtWidgets.QWidget]] = {}
        
        # 日志
        self.log_text: Optional[QtWidgets.QTextEdit] = None
        self.status_label: Optional[QtWidgets.QLabel] = None
        self.overall_progress: Optional[QtWidgets.QProgressBar] = None
        
        # 一键生成按钮
        self.generate_all_button: Optional[QtWidgets.QPushButton] = None
        self.stop_button: Optional[QtWidgets.QPushButton] = None
        
        # 配置管理
        self.config_combo: Optional[QtWidgets.QComboBox] = None
        self.save_button: Optional[QtWidgets.QPushButton] = None
        self.load_button: Optional[QtWidgets.QPushButton] = None
        self.new_button: Optional[QtWidgets.QPushButton] = None
        
        # 异步任务
        self._current_task: Optional[asyncio.Task] = None
        
        # 设置日志回调
        self.orchestrator.log_callback = self._on_orchestrator_log
        self.orchestrator.progress_callback = self._on_orchestrator_progress
    
    def build_ui(self, parent) -> None:
        """构建 UI"""
        layout: QtWidgets.QVBoxLayout = parent
        
        # 标题
        title = QtWidgets.QLabel("🗺️ 地图生成器")
        font = title.font()
        font.setPointSize(22)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        layout.addWidget(self._hline())
        
        # 配置管理工具栏
        toolbar = self._build_toolbar()
        layout.addWidget(toolbar)
        
        # 主内容区（滚动）
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)
        
        # 创建四个模块 UI
        self._create_module_ui(content_layout, "1_terrain", "基础地形", "🏔️", None)
        self._create_module_ui(content_layout, "2_colors", "地图颜色", "🎨", "1_terrain")
        self._create_module_ui(content_layout, "3_track", "赛道数据", "🏁", "1_terrain")
        self._create_module_ui(content_layout, "4_scenery", "场景元素", "🌲", "1_terrain")
        
        content_layout.addStretch(1)
        
        # 日志区域
        log_group = QtWidgets.QGroupBox("📊 生成日志")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QtGui.QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        # 底部状态栏
        bottom_layout = QtWidgets.QHBoxLayout()
        
        self.status_label = QtWidgets.QLabel("● 就绪")
        self.status_label.setStyleSheet("color: #00ff00; font-size: 14px;")
        bottom_layout.addWidget(self.status_label)
        
        self.overall_progress = QtWidgets.QProgressBar()
        self.overall_progress.setMaximum(100)
        self.overall_progress.setValue(0)
        self.overall_progress.setFixedWidth(300)
        bottom_layout.addWidget(self.overall_progress)
        
        # 一键生成按钮
        self.generate_all_button = QtWidgets.QPushButton("▶️ 一键生成所有")
        self.generate_all_button.setStyleSheet(
            "background-color: #28a745; color: white; padding: 10px 20px; "
            "border-radius: 8px; font-size: 14px; font-weight: bold;"
        )
        self.generate_all_button.clicked.connect(self._on_generate_all)
        bottom_layout.addWidget(self.generate_all_button)
        
        self.stop_button = QtWidgets.QPushButton("⏹️ 停止")
        self.stop_button.setStyleSheet(
            "background-color: #dc3545; color: white; padding: 10px 20px; "
            "border-radius: 8px; font-size: 14px;"
        )
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._on_stop)
        bottom_layout.addWidget(self.stop_button)
        
        bottom_layout.addStretch(1)
        log_layout.addLayout(bottom_layout)
        
        layout.addWidget(log_group)
        
        # 初始化默认配置
        self._load_config_list()
        self._create_default_config()
    
    def _build_toolbar(self) -> QtWidgets.QWidget:
        """构建配置管理工具栏"""
        toolbar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 10, 0, 10)
        
        # 配置选择
        layout.addWidget(QtWidgets.QLabel("配置:"))
        
        self.config_combo = QtWidgets.QComboBox()
        self.config_combo.setMinimumWidth(200)
        self.config_combo.currentTextChanged.connect(self._on_config_selected)
        layout.addWidget(self.config_combo)
        
        # 按钮
        self.new_button = QtWidgets.QPushButton("➕ 新建")
        self.new_button.clicked.connect(self._on_new_config)
        layout.addWidget(self.new_button)
        
        self.load_button = QtWidgets.QPushButton("📂 加载")
        self.load_button.clicked.connect(self._on_load_config)
        layout.addWidget(self.load_button)
        
        self.save_button = QtWidgets.QPushButton("💾 保存")
        self.save_button.clicked.connect(self._on_save_config)
        layout.addWidget(self.save_button)
        
        layout.addStretch(1)
        
        return toolbar
    
    def _create_module_ui(self, parent, module_id: str, title: str, icon: str, depends_on: Optional[str]):
        """创建单个模块的 UI"""
        group = QtWidgets.QGroupBox(f"{icon} {title}")
        group_layout = QtWidgets.QVBoxLayout(group)
        group_layout.setContentsMargins(12, 16, 12, 12)
        group_layout.setSpacing(10)
        
        # 状态行
        status_layout = QtWidgets.QHBoxLayout()
        
        status_label = QtWidgets.QLabel("⏸️ 等待中")
        status_label.setStyleSheet("color: #ffa500; font-weight: bold;")
        status_layout.addWidget(status_label)
        self.module_status_labels[module_id] = status_label
        
        progress = QtWidgets.QProgressBar()
        progress.setMaximum(100)
        progress.setValue(0)
        progress.setFixedWidth(200)
        status_layout.addWidget(progress)
        self.module_progress_bars[module_id] = progress
        
        status_layout.addStretch(1)
        group_layout.addLayout(status_layout)
        
        # 依赖提示
        if depends_on:
            dep_label = QtWidgets.QLabel(f"🔗 依赖：{depends_on}")
            dep_label.setStyleSheet("color: #888888; font-size: 11px;")
            group_layout.addWidget(dep_label)
        
        # 配置输入区域（折叠）
        config_widget = self._create_module_inputs(module_id)
        group_layout.addWidget(config_widget)
        
        # 按钮行
        button_layout = QtWidgets.QHBoxLayout()
        
        gen_btn = QtWidgets.QPushButton("⚙️ 生成")
        gen_btn.setStyleSheet("background-color: #1f6aa5; color: white; padding: 8px 16px; border-radius: 6px;")
        gen_btn.clicked.connect(lambda checked=False, mid=module_id: self._on_generate_module(mid))
        group_layout.addWidget(gen_btn)
        self.module_generate_buttons[module_id] = gen_btn
        
        preview_btn = QtWidgets.QPushButton("👁️ 预览")
        preview_btn.setStyleSheet("background-color: #6c757d; color: white; padding: 8px 16px; border-radius: 6px;")
        preview_btn.setEnabled(False)
        group_layout.addWidget(preview_btn)
        self.module_preview_buttons[module_id] = preview_btn
        
        button_layout.addStretch(1)
        group_layout.addLayout(button_layout)
        
        parent.addWidget(group)
        self.module_group_widgets[module_id] = group
    
    def _create_module_inputs(self, module_id: str) -> QtWidgets.QWidget:
        """创建模块配置输入控件"""
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        inputs = {}
        
        if module_id == "1_terrain":
            # 宽度
            layout.addWidget(QtWidgets.QLabel("宽度:"), 0, 0)
            width_edit = QtWidgets.QLineEdit("1024")
            width_edit.setToolTip("高度图宽度（像素）")
            layout.addWidget(width_edit, 0, 1)
            inputs['width'] = width_edit
            
            # 高度
            layout.addWidget(QtWidgets.QLabel("高度:"), 0, 2)
            height_edit = QtWidgets.QLineEdit("1024")
            layout.addWidget(height_edit, 0, 3)
            inputs['height'] = height_edit
            
            # 种子
            layout.addWidget(QtWidgets.QLabel("种子:"), 1, 0)
            seed_edit = QtWidgets.QLineEdit("42")
            layout.addWidget(seed_edit, 1, 1)
            inputs['seed'] = seed_edit
            
            # 输出名称
            layout.addWidget(QtWidgets.QLabel("输出名称:"), 1, 2)
            output_edit = QtWidgets.QLineEdit("race_base")
            layout.addWidget(output_edit, 1, 3)
            inputs['output'] = output_edit
            
            # 基础频率
            layout.addWidget(QtWidgets.QLabel("基础频率:"), 2, 0)
            freq_edit = QtWidgets.QLineEdit("0.003")
            layout.addWidget(freq_edit, 2, 1)
            inputs['base_frequency'] = freq_edit
            
            # Octaves
            layout.addWidget(QtWidgets.QLabel("Octaves:"), 2, 2)
            octaves_edit = QtWidgets.QLineEdit("5")
            layout.addWidget(octaves_edit, 2, 3)
            inputs['octaves'] = octaves_edit
        
        elif module_id == "2_colors":
            layout.addWidget(QtWidgets.QLabel("模式:"), 0, 0)
            mode_combo = QtWidgets.QComboBox()
            mode_combo.addItems(["程序化生成", "纹理混合"])
            layout.addWidget(mode_combo, 0, 1)
            inputs['mode'] = mode_combo
            
            # 草地颜色
            layout.addWidget(QtWidgets.QLabel("草地颜色:"), 1, 0)
            grass_btn = QtWidgets.QPushButton()
            grass_btn.setStyleSheet("background-color: #08a008; min-width: 60px;")
            layout.addWidget(grass_btn, 1, 1)
            inputs['grass_color'] = grass_btn
        
        elif module_id == "3_track":
            layout.addWidget(QtWidgets.QLabel("CSV 路径:"), 0, 0)
            csv_edit = QtWidgets.QLineEdit("configs/tracks/default_track.csv")
            layout.addWidget(csv_edit, 0, 1, 1, 2)
            inputs['csv_path'] = csv_edit
            
            browse_btn = QtWidgets.QPushButton("浏览...")
            browse_btn.clicked.connect(lambda: self._browse_file(csv_edit))
            layout.addWidget(browse_btn, 0, 3)
            
            layout.addWidget(QtWidgets.QLabel("赛道宽度:"), 1, 0)
            width_edit = QtWidgets.QLineEdit("9.0")
            layout.addWidget(width_edit, 1, 1)
            inputs['track_width'] = width_edit
        
        elif module_id == "4_scenery":
            layout.addWidget(QtWidgets.QLabel("树木数量:"), 0, 0)
            trees_edit = QtWidgets.QLineEdit("30")
            layout.addWidget(trees_edit, 0, 1)
            inputs['trees_count'] = trees_edit
            
            layout.addWidget(QtWidgets.QLabel("岩石数量:"), 0, 2)
            rocks_edit = QtWidgets.QLineEdit("40")
            layout.addWidget(rocks_edit, 0, 3)
            inputs['rocks_count'] = rocks_edit
        
        widget.setVisible(False)  # 默认折叠
        self.config_inputs[module_id] = inputs
        
        # 添加折叠/展开功能
        toggle_btn = QtWidgets.QPushButton("📋 展开配置 ▼")
        toggle_btn.setCheckable(True)
        toggle_btn.toggled.connect(lambda checked: widget.setVisible(checked))
        
        # 在创建模块时插入到 group 的顶部
        return widget
    
    def _load_config_list(self):
        """加载配置列表到下拉框"""
        self.config_combo.blockSignals(True)
        self.config_combo.clear()
        
        configs = self.config_manager.list_configs()
        if configs:
            self.config_combo.addItems(configs)
        else:
            self.config_combo.addItem("（无配置）")
        
        self.config_combo.blockSignals(False)
    
    def _create_default_config(self):
        """创建默认配置"""
        if not self.current_config:
            self.current_config = self.config_manager.create_default_config("Default Map")
            self.current_config_name = "Default Map"
            self._populate_ui_from_config()
    
    def _populate_ui_from_config(self):
        """从当前配置填充 UI"""
        if not self.current_config:
            return
        
        # 填充各模块的输入控件
        for module_id, module in self.current_config.modules.items():
            inputs = self.config_inputs.get(module_id, {})
            data = module.data
            
            # 地形
            if module_id == "1_terrain":
                inputs.get('width', QtWidgets.QLineEdit()).setText(str(data.get('width', 1024)))
                inputs.get('height', QtWidgets.QLineEdit()).setText(str(data.get('height', 1024)))
                inputs.get('seed', QtWidgets.QLineEdit()).setText(str(data.get('seed', 42)))
                inputs.get('output', QtWidgets.QLineEdit()).setText(data.get('output', 'race_base'))
                
                noise = data.get('noise', {})
                inputs.get('base_frequency', QtWidgets.QLineEdit()).setText(str(noise.get('base_frequency', 0.003)))
                inputs.get('octaves', QtWidgets.QLineEdit()).setText(str(noise.get('octaves', 5)))
            
            # 更新状态
            self._update_module_status(module_id, module.status)
    
    def _update_module_status(self, module_id: str, status: str):
        """更新模块状态显示"""
        status_label = self.module_status_labels.get(module_id)
        progress_bar = self.module_progress_bars.get(module_id)
        gen_btn = self.module_generate_buttons.get(module_id)
        preview_btn = self.module_preview_buttons.get(module_id)
        
        if not status_label:
            return
        
        status_map = {
            "pending": ("⏸️ 等待中", "#ffa500"),
            "ready": ("✅ 就绪", "#00ff00"),
            "running": ("⚙️ 生成中...", "#1f6aa5"),
            "completed": ("✅ 已完成", "#00ff00"),
            "error": ("❌ 错误", "#ff4444")
        }
        
        text, color = status_map.get(status, ("❓ 未知", "#888888"))
        status_label.setText(text)
        status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        if status == "completed":
            if progress_bar:
                progress_bar.setValue(100)
            if gen_btn:
                gen_btn.setText("🔄 重新生成")
            if preview_btn:
                preview_btn.setEnabled(True)
        elif status == "running":
            if gen_btn:
                gen_btn.setEnabled(False)
        else:
            if gen_btn:
                gen_btn.setEnabled(True)
                gen_btn.setText("⚙️ 生成")
            if preview_btn:
                preview_btn.setEnabled(False)
    
    def _on_generate_module(self, module_id: str):
        """生成单个模块"""
        # 检查依赖
        if self.current_config:
            if not self.config_manager.check_dependencies(self.current_config, module_id):
                self._log(f"⚠️ {module_id} 依赖未满足", "warning")
                QtWidgets.QMessageBox.warning(
                    None, "依赖未满足",
                    f"请先生成依赖模块"
                )
                return
        
        # 获取配置数据
        config_data = self._collect_module_config(module_id)
        
        # 创建步骤
        step = self._create_step(module_id, config_data)
        if not step:
            return
        
        # 添加到编排器
        self.orchestrator.add_step(step)
        
        # 异步执行
        self._run_async(self._execute_step(module_id, step))
    
    def _create_step(self, module_id: str, config_data: Dict[str, Any]):
        """创建生成步骤"""
        if module_id == "1_terrain":
            return TerrainGenerationStep(config_data)
        elif module_id == "2_colors":
            return ColorGenerationStep(config_data)
        elif module_id == "3_track":
            return TrackGenerationStep(config_data)
        elif module_id == "4_scenery":
            return SceneryGenerationStep(config_data)
        return None
    
    def _collect_module_config(self, module_id: str) -> Dict[str, Any]:
        """从 UI 收集模块配置"""
        inputs = self.config_inputs.get(module_id, {})
        config = {}
        
        if module_id == "1_terrain":
            config = {
                'width': int(inputs.get('width', QtWidgets.QLineEdit()).text() or 1024),
                'height': int(inputs.get('height', QtWidgets.QLineEdit()).text() or 1024),
                'seed': int(inputs.get('seed', QtWidgets.QLineEdit()).text() or 42),
                'output': inputs.get('output', QtWidgets.QLineEdit()).text() or 'race_base',
                'noise': {
                    'base_frequency': float(inputs.get('base_frequency', QtWidgets.QLineEdit()).text() or 0.003),
                    'octaves': int(inputs.get('octaves', QtWidgets.QLineEdit()).text() or 5)
                },
                'sculpt': {}
            }
        
        return config
    
    async def _execute_step(self, module_id: str, step):
        """执行步骤"""
        self._update_module_status(module_id, "running")
        
        success, message = await self.orchestrator.execute_step(module_id)
        
        if success:
            self._update_module_status(module_id, "completed")
            if self.current_config:
                self.config_manager.update_module_status(
                    self.current_config,
                    module_id,
                    "completed",
                    step.generated_files
                )
        else:
            self._update_module_status(module_id, "error")
        
        self._log(f"{module_id}: {message}", "info" if success else "error")
    
    def _on_generate_all(self):
        """一键生成所有"""
        if not self.current_config:
            self._log("❌ 请先加载或创建配置", "error")
            return
        
        # 初始化编排器
        self.orchestrator.reset_all()
        
        for module_id, module in self.current_config.modules.items():
            if not module.enabled:
                continue
            
            config_data = self._collect_module_config(module_id)
            step = self._create_step(module_id, config_data)
            if step:
                self.orchestrator.add_step(step)
        
        # 运行
        self.generate_all_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        self._run_async(self._execute_generate_all())
    
    async def _execute_generate_all(self):
        """执行一键生成"""
        success, message = await self.orchestrator.generate_all()
        
        self.generate_all_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        self._log(f"{'✅' if success else '❌'} {message}", "success" if success else "error")
        
        if success:
            self.overall_progress.setValue(100)
    
    def _on_stop(self):
        """停止生成"""
        if self._current_task:
            self._current_task.cancel()
            self._log("⏹️ 用户停止生成", "warning")
            self.generate_all_button.setEnabled(True)
            self.stop_button.setEnabled(False)
    
    def _on_config_selected(self, name: str):
        """配置选择"""
        if name and name != "（无配置）":
            try:
                self.current_config = self.config_manager.load_config(name)
                self.current_config_name = name
                self._populate_ui_from_config()
                self._log(f"📂 已加载配置：{name}", "info")
            except Exception as e:
                self._log(f"❌ 加载配置失败：{e}", "error")
    
    def _on_new_config(self):
        """新建配置"""
        name, ok = QtWidgets.QInputDialog.getText(
            None, "新建配置", "配置名称:"
        )
        if ok and name:
            self.current_config = self.config_manager.create_default_config(name)
            self.current_config_name = name
            self._populate_ui_from_config()
            self._load_config_list()
            self.config_combo.setCurrentText(name)
            self._log(f"➕ 已创建新配置：{name}", "info")
    
    def _on_load_config(self):
        """加载配置"""
        self._on_config_selected(self.config_combo.currentText())
    
    def _on_save_config(self):
        """保存配置"""
        if not self.current_config:
            self._log("❌ 没有可保存的配置", "error")
            return
        
        # 从 UI 更新配置数据
        for module_id in self.current_config.modules.keys():
            config_data = self._collect_module_config(module_id)
            self.current_config.modules[module_id].data = config_data
        
        try:
            path = self.config_manager.save_config(self.current_config)
            self._load_config_list()
            self._log(f"💾 配置已保存：{path}", "success")
        except Exception as e:
            self._log(f"❌ 保存失败：{e}", "error")
    
    def _on_orchestrator_log(self, message: str, level: str):
        """编排器日志回调"""
        self._log(message, level)
    
    def _on_orchestrator_progress(self, step_name: str, progress: float):
        """编排器进度回调"""
        progress_bar = self.module_progress_bars.get(step_name)
        if progress_bar:
            progress_bar.setValue(int(progress * 100))
        
        if step_name == "4_scenery":
            self.overall_progress.setValue(int(progress * 100))
    
    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        super().log(message, level)
        
        if self.log_text:
            timestamp = QtCore.QTime.currentTime().toString("HH:mm:ss")
            color_map = {
                "info": "#00ff00",
                "warning": "#ffa500",
                "error": "#ff4444",
                "success": "#00ff00"
            }
            color = color_map.get(level, "#ffffff")
            
            self.log_text.append(
                f'<span style="color: {color};">[{timestamp}] {message}</span>'
            )
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
    
    def _hline(self) -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #333333;")
        return line
    
    def _browse_file(self, line_edit: QtWidgets.QLineEdit):
        """浏览文件"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "选择文件", "configs/tracks", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            rel_path = os.path.relpath(file_path, os.getcwd())
            line_edit.setText(rel_path)
    
    def _run_async(self, coro):
        """运行异步任务"""
        loop = asyncio.get_event_loop()
        self._current_task = loop.create_task(coro)
    
    def cleanup(self):
        """清理"""
        if self._current_task:
            self._current_task.cancel()
