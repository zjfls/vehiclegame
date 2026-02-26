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
        self.config_widgets: Dict[str, QtWidgets.QWidget] = {}
        self.toggle_buttons: Dict[str, QtWidgets.QPushButton] = {}
        
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
        
        # 折叠/展开按钮
        toggle_btn = QtWidgets.QPushButton("📋 展开配置 ▼")
        toggle_btn.setCheckable(True)
        toggle_btn.setStyleSheet("background-color: #2d2d2d; color: #a0a0a0; padding: 6px 12px; border-radius: 4px; font-size: 11px;")
        toggle_btn.toggled.connect(lambda checked, mid=module_id: self._on_toggle_inputs(mid, checked))
        group_layout.addWidget(toggle_btn)
        self.toggle_buttons[module_id] = toggle_btn
        
        # 配置输入区域（折叠）
        config_widget = self._create_module_inputs(module_id)
        group_layout.addWidget(config_widget)
        
        # 分隔线
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #333333;")
        group_layout.addWidget(line)
        
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
            # 第 0 行：宽度和高度
            layout.addWidget(QtWidgets.QLabel("宽度:"), 0, 0)
            width_edit = QtWidgets.QLineEdit("1024")
            width_edit.setToolTip(
                "高度图宽度（像素）\n\n"
                "• 推荐值：512, 1024, 2048\n"
                "• 越大分辨率越高，地形细节越丰富\n"
                "• 生成时间和内存占用也会增加\n"
                "• 建议从 1024 开始测试"
            )
            width_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(width_edit, 0, 1)
            inputs['width'] = width_edit
            
            layout.addWidget(QtWidgets.QLabel("高度:"), 0, 2)
            height_edit = QtWidgets.QLineEdit("1024")
            height_edit.setToolTip(
                "高度图高度（像素）\n\n"
                "• 通常与宽度相同，保持正方形\n"
                "• 越大分辨率越高，细节越丰富\n"
                "• 建议与宽度保持一致"
            )
            height_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(height_edit, 0, 3)
            inputs['height'] = height_edit
            
            # 第 1 行：种子和输出名称
            layout.addWidget(QtWidgets.QLabel("种子:"), 1, 0)
            seed_edit = QtWidgets.QLineEdit("42")
            seed_edit.setToolTip(
                "随机种子（整数）\n\n"
                "• 相同种子 + 相同参数 = 相同地形\n"
                "• 改变种子会生成完全不同的地形\n"
                "• 发现喜欢的地形？记住种子值！\n"
                "• 示例：42, 12345, 2024"
            )
            seed_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(seed_edit, 1, 1)
            inputs['seed'] = seed_edit
            
            layout.addWidget(QtWidgets.QLabel("输出名称:"), 1, 2)
            output_edit = QtWidgets.QLineEdit("race_base")
            output_edit.setToolTip(
                "输出文件前缀名\n\n"
                "• 生成文件：res/terrain/{名称}.npy/.pgm/.json\n"
                "• 使用英文、数字和下划线\n"
                "• 避免特殊字符和空格\n"
                "• 示例：race_base, mountain_01, track_alpha"
            )
            output_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(output_edit, 1, 3)
            inputs['output'] = output_edit
            
            # 第 2 行：基础频率和 Octaves
            layout.addWidget(QtWidgets.QLabel("基础频率:"), 2, 0)
            freq_edit = QtWidgets.QLineEdit("0.003")
            freq_edit.setToolTip(
                "噪声基础频率（base_frequency）\n\n"
                "• 控制地形宏观特征的尺度\n"
                "• 越大：细节越密集，地形更破碎\n"
                "• 越小：地形变化更平缓，山脉更大\n"
                "• 推荐范围：0.001 - 0.01\n"
                "• 默认 0.003 适合中等规模地形"
            )
            freq_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(freq_edit, 2, 1)
            inputs['base_frequency'] = freq_edit
            
            layout.addWidget(QtWidgets.QLabel("Octaves:"), 2, 2)
            octaves_edit = QtWidgets.QLineEdit("5")
            octaves_edit.setToolTip(
                "噪声叠加层数（Octaves）\n\n"
                "• 每层叠加更细的细节\n"
                "• 越高：地形细节越丰富，越真实\n"
                "• 越低：地形更平滑，但可能单调\n"
                "• 推荐范围：3-8\n"
                "• 默认 5 层平衡质量和性能"
            )
            octaves_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(octaves_edit, 2, 3)
            inputs['octaves'] = octaves_edit
            
            # 第 3 行：Persistence 和 Lacunarity
            layout.addWidget(QtWidgets.QLabel("Persistence:"), 3, 0)
            pers_edit = QtWidgets.QLineEdit("0.5")
            pers_edit.setToolTip(
                "持久性系数（Persistence, 0..1）\n\n"
                "• 控制每层噪声的幅度衰减\n"
                "• 越大（接近 1）：细节层更明显，地形更粗糙\n"
                "• 越小（接近 0）：细节层更弱，地形更平滑\n"
                "• 推荐范围：0.3 - 0.7\n"
                "• 默认 0.5 是经典值"
            )
            pers_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(pers_edit, 3, 1)
            inputs['persistence'] = pers_edit
            
            layout.addWidget(QtWidgets.QLabel("Lacunarity:"), 3, 2)
            lac_edit = QtWidgets.QLineEdit("2.0")
            lac_edit.setToolTip(
                " lacunarity（频率增长系数）\n\n"
                "• 控制每层噪声频率的增长速度\n"
                "• 越大：细节层频率增长快，纹理更密\n"
                "• 越小：细节层频率增长慢，纹理更疏\n"
                "• 推荐范围：1.5 - 3.0\n"
                "• 默认 2.0 是经典倍频程"
            )
            lac_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(lac_edit, 3, 3)
            inputs['lacunarity'] = lac_edit
            
            # 第 4 行：平滑和起伏
            layout.addWidget(QtWidgets.QLabel("平滑 σ:"), 4, 0)
            smooth_edit = QtWidgets.QLineEdit("2.5")
            smooth_edit.setToolTip(
                "高斯平滑强度（Smooth Sigma）\n\n"
                "• 对生成后的高度图进行高斯模糊\n"
                "• 越大：地形越平滑，山峰更圆润\n"
                "• 越小：保留更多原始噪声细节\n"
                "• 0 = 不平滑\n"
                "• 推荐范围：1.0 - 5.0\n"
                "• 默认 2.5 适度平滑"
            )
            smooth_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(smooth_edit, 4, 1)
            inputs['smooth_sigma'] = smooth_edit
            
            layout.addWidget(QtWidgets.QLabel("起伏强度:"), 4, 2)
            relief_edit = QtWidgets.QLineEdit("0.25")
            relief_edit.setToolTip(
                "全局起伏强度（Relief Strength, 0..1）\n\n"
                "• 控制整体高度变化的幅度\n"
                "• 越大：地形起伏更剧烈，山峰更高\n"
                "• 越小：地形更平坦，适合赛道\n"
                "• 0 = 完全平坦\n"
                "• 1 = 最大起伏\n"
                "• 默认 0.25 适合赛车地形"
            )
            relief_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(relief_edit, 4, 3)
            inputs['relief_strength'] = relief_edit
        
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
            csv_edit.setToolTip(
                "赛道中心线 CSV 文件路径\n\n"
                "• 格式：每行 x,y 坐标（归一化 0-1 或世界坐标）\n"
                "• 至少需要 2 个点形成赛道\n"
                "• 第一个点通常是发车位置\n"
                "• 点击 '浏览...' 选择文件\n"
                "• 留空则使用默认椭圆赛道"
            )
            csv_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(csv_edit, 0, 1, 1, 2)
            inputs['csv_path'] = csv_edit
            
            browse_btn = QtWidgets.QPushButton("浏览...")
            browse_btn.setToolTip("选择赛道 CSV 文件")
            browse_btn.clicked.connect(lambda: self._browse_file(csv_edit))
            layout.addWidget(browse_btn, 0, 3)
            
            layout.addWidget(QtWidgets.QLabel("赛道宽度:"), 1, 0)
            width_edit = QtWidgets.QLineEdit("9.0")
            width_edit.setToolTip(
                "赛道表面宽度（世界单位：米）\n\n"
                "• 控制赛道的横向范围\n"
                "• 越大：赛道越宽，更容易驾驶\n"
                "• 越小：赛道越窄，更具挑战性\n"
                "• 推荐范围：6.0 - 15.0\n"
                "• 默认 9.0 适合标准赛道"
            )
            width_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(width_edit, 1, 1)
            inputs['track_width'] = width_edit
        
        elif module_id == "4_scenery":
            layout.addWidget(QtWidgets.QLabel("树木数量:"), 0, 0)
            trees_edit = QtWidgets.QLineEdit("30")
            trees_edit.setToolTip(
                "树木生成数量\n\n"
                "• 在赛道周围随机分布\n"
                "• 越多：场景更丰富，但影响性能\n"
                "• 越少：性能更好，但场景单调\n"
                "• 推荐范围：20-100\n"
                "• 默认 30 平衡效果和性能"
            )
            trees_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(trees_edit, 0, 1)
            inputs['trees_count'] = trees_edit
            
            layout.addWidget(QtWidgets.QLabel("岩石数量:"), 0, 2)
            rocks_edit = QtWidgets.QLineEdit("40")
            rocks_edit.setToolTip(
                "岩石生成数量\n\n"
                "• 在赛道周围和山坡随机分布\n"
                "• 越多：场景更自然，但可能阻碍赛道\n"
                "• 越少：赛道更干净，驾驶更安全\n"
                "• 推荐范围：20-80\n"
                "• 默认 40 适度点缀"
            )
            rocks_edit.setStyleSheet("background-color: #2d2d2d; color: white;")
            layout.addWidget(rocks_edit, 0, 3)
            inputs['rocks_count'] = rocks_edit
        
        widget.setVisible(False)  # 默认折叠
        widget.setStyleSheet("background-color: #1a1a1a; padding: 10px; border-radius: 6px;")
        self.config_inputs[module_id] = inputs
        self.config_widgets[module_id] = widget
        
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
        
        # 辅助方法：安全设置 QLineEdit 的值
        def set_line_edit(inputs_dict, key, value, default=""):
            widget = inputs_dict.get(key)
            if widget and isinstance(widget, QtWidgets.QLineEdit):
                widget.setText(str(value) if value is not None else default)
        
        # 填充各模块的输入控件
        for module_id, module in self.current_config.modules.items():
            inputs = self.config_inputs.get(module_id, {})
            data = module.data
            
            if module_id == "1_terrain":
                # 基础参数
                set_line_edit(inputs, 'width', data.get('width', 1024))
                set_line_edit(inputs, 'height', data.get('height', 1024))
                set_line_edit(inputs, 'seed', data.get('seed', 42))
                set_line_edit(inputs, 'output', data.get('output', 'race_base'))
                
                # 噪声参数
                noise = data.get('noise', {})
                set_line_edit(inputs, 'base_frequency', noise.get('base_frequency', 0.003))
                set_line_edit(inputs, 'octaves', noise.get('octaves', 5))
                set_line_edit(inputs, 'persistence', noise.get('persistence', 0.5))
                set_line_edit(inputs, 'lacunarity', noise.get('lacunarity', 2.0))
                
                # 雕刻参数
                sculpt = data.get('sculpt', {})
                set_line_edit(inputs, 'smooth_sigma', sculpt.get('smooth_sigma', 2.5))
                set_line_edit(inputs, 'relief_strength', sculpt.get('relief_strength', 0.25))
            
            elif module_id == "3_track":
                set_line_edit(inputs, 'csv_path', data.get('csv_path', 'configs/tracks/default_track.csv'))
                geom = data.get('geometry', {})
                set_line_edit(inputs, 'track_width', geom.get('track_width', 9.0))
            
            elif module_id == "4_scenery":
                trees = data.get('trees', {})
                set_line_edit(inputs, 'trees_count', trees.get('count', 30))
                rocks = data.get('rocks', {})
                set_line_edit(inputs, 'rocks_count', rocks.get('count', 40))
            
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
            def get_int(key, default):
                widget = inputs.get(key)
                if widget and isinstance(widget, QtWidgets.QLineEdit):
                    try:
                        return int(widget.text())
                    except:
                        return default
                return default
            
            def get_float(key, default):
                widget = inputs.get(key)
                if widget and isinstance(widget, QtWidgets.QLineEdit):
                    try:
                        return float(widget.text())
                    except:
                        return default
                return default
            
            def get_text(key, default):
                widget = inputs.get(key)
                if widget and isinstance(widget, QtWidgets.QLineEdit):
                    return widget.text() or default
                return default
            
            config = {
                'width': get_int('width', 1024),
                'height': get_int('height', 1024),
                'seed': get_int('seed', 42),
                'output': get_text('output', 'race_base'),
                'noise': {
                    'base_frequency': get_float('base_frequency', 0.003),
                    'octaves': get_int('octaves', 5),
                    'persistence': get_float('persistence', 0.5),
                    'lacunarity': get_float('lacunarity', 2.0)
                },
                'sculpt': {
                    'smooth_sigma': get_float('smooth_sigma', 2.5),
                    'relief_strength': get_float('relief_strength', 0.25)
                }
            }
        
        elif module_id == "2_colors":
            config = {
                'mode': 'procedural',
                'procedural': {}
            }
        
        elif module_id == "3_track":
            csv_widget = inputs.get('csv_path')
            csv_path = csv_widget.text() if csv_widget else 'configs/tracks/default_track.csv'
            
            width_widget = inputs.get('track_width')
            track_width = 9.0
            if width_widget and isinstance(width_widget, QtWidgets.QLineEdit):
                try:
                    track_width = float(width_widget.text())
                except:
                    pass
            
            config = {
                'csv_path': csv_path,
                'coord_space': 'normalized',
                'geometry': {
                    'track_width': track_width,
                    'border_width': 0.8,
                    'samples_per_segment': 8
                }
            }
        
        elif module_id == "4_scenery":
            trees_widget = inputs.get('trees_count')
            trees_count = 30
            if trees_widget and isinstance(trees_widget, QtWidgets.QLineEdit):
                try:
                    trees_count = int(trees_widget.text())
                except:
                    pass
            
            rocks_widget = inputs.get('rocks_count')
            rocks_count = 40
            if rocks_widget and isinstance(rocks_widget, QtWidgets.QLineEdit):
                try:
                    rocks_count = int(rocks_widget.text())
                except:
                    pass
            
            config = {
                'trees': {'count': trees_count, 'enabled': True},
                'rocks': {'count': rocks_count, 'enabled': True}
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
    
    def _on_toggle_inputs(self, module_id: str, expanded: bool):
        """切换配置输入区域的展开/折叠状态"""
        widget = self.config_widgets.get(module_id)
        toggle_btn = self.toggle_buttons.get(module_id)
        
        if widget:
            widget.setVisible(expanded)
        
        if toggle_btn:
            if expanded:
                toggle_btn.setText("📋 收起配置 ▲")
                toggle_btn.setStyleSheet(
                    "background-color: #1f6aa5; color: white; padding: 6px 12px; "
                    "border-radius: 4px; font-size: 11px;"
                )
            else:
                toggle_btn.setText("📋 展开配置 ▼")
                toggle_btn.setStyleSheet(
                    "background-color: #2d2d2d; color: #a0a0a0; padding: 6px 12px; "
                    "border-radius: 4px; font-size: 11px;"
                )
    
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
        # 兼容 Python 3.14+：使用 get_running_loop() 或创建新 loop
        try:
            loop = asyncio.get_running_loop()
            # 如果在运行中的事件循环里（不可能，因为这是同步调用）
            self._current_task = loop.create_task(coro)
        except RuntimeError:
            # 没有运行中的循环，使用 console_app 的主循环
            if hasattr(self.console_app, 'async_loop') and self.console_app.async_loop:
                self._current_task = asyncio.run_coroutine_threadsafe(
                    coro, self.console_app.async_loop
                )
            else:
                # 后备方案：创建新线程运行 loop
                import threading
                def run_loop():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    new_loop.run_forever()
                
                thread = threading.Thread(target=run_loop, daemon=True)
                thread.start()
                self.console_app.async_loop = new_loop if 'new_loop' in locals() else None
                if self.console_app.async_loop:
                    self._current_task = asyncio.run_coroutine_threadsafe(
                        coro, self.console_app.async_loop
                    )
    
    def cleanup(self):
        """清理"""
        if self._current_task:
            self._current_task.cancel()
