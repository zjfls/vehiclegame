"""
游戏启动模块 - PySide6 (Qt) 版本
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from typing import Any, List, Optional

from PySide6 import QtCore, QtWidgets

from console_modules.base_module import ConsoleModule
from core.map_config_manager import MapConfigManager


class GameLauncherModule(ConsoleModule):
    name = "game_launcher"
    display_name = "启动游戏"
    icon = "🚀"
    description = "启动车辆游戏，支持多车辆配置"

    def __init__(self, console_app: Any):
        super().__init__(console_app)
        self.vehicle_configs: List[str] = []
        self.map_configs: List[str] = []
        self.selected_vehicle: Optional[str] = None
        self.selected_map: Optional[str] = None

        self.map_config_manager = MapConfigManager()

        self.process: Optional[QtCore.QProcess] = None
        self._game_log_path: Optional[str] = None
        self._log_file = None

        # UI refs
        self.vehicle_combo: Optional[QtWidgets.QComboBox] = None
        self.map_combo: Optional[QtWidgets.QComboBox] = None
        self.debug_check: Optional[QtWidgets.QCheckBox] = None
        self.fullscreen_check: Optional[QtWidgets.QCheckBox] = None
        self.shadows_check: Optional[QtWidgets.QCheckBox] = None
        self.resolution_combo: Optional[QtWidgets.QComboBox] = None
        self.status_label: Optional[QtWidgets.QLabel] = None
        self.vehicle_info_label: Optional[QtWidgets.QLabel] = None
        self.start_button: Optional[QtWidgets.QPushButton] = None
        self.stop_button: Optional[QtWidgets.QPushButton] = None

    def build_ui(self, parent) -> None:
        # parent is QVBoxLayout
        layout: QtWidgets.QVBoxLayout = parent

        title = QtWidgets.QLabel("🚀 游戏启动配置")
        font = title.font()
        font.setPointSize(22)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        layout.addWidget(self._hline())

        layout.addLayout(self._build_config_row("车辆配置:", kind="vehicle"))
        layout.addLayout(self._build_config_row("地图配置:", kind="map"))

        # Settings
        settings = QtWidgets.QGroupBox("游戏设置")
        s_layout = QtWidgets.QVBoxLayout(settings)
        self.fullscreen_check = QtWidgets.QCheckBox("全屏模式")
        self.fullscreen_check.setToolTip("切换全屏显示（可能影响窗口/多显示器布局）。")
        self.debug_check = QtWidgets.QCheckBox("调试模式")
        self.debug_check.setToolTip("启用更详细的调试输出（可能降低性能）。")
        self.shadows_check = QtWidgets.QCheckBox("启用阴影")
        self.shadows_check.setToolTip("启用实时阴影（画面更真实，但更耗性能）。")
        self.shadows_check.setChecked(True)
        s_layout.addWidget(self.fullscreen_check)
        s_layout.addWidget(self.debug_check)
        s_layout.addWidget(self.shadows_check)
        layout.addWidget(settings)

        # Resolution
        res_row = QtWidgets.QHBoxLayout()
        res_row.addWidget(QtWidgets.QLabel("分辨率:"), 0)
        self.resolution_combo = QtWidgets.QComboBox()
        self.resolution_combo.setToolTip("窗口/渲染分辨率（越高越清晰，但更耗性能）。")
        self.resolution_combo.addItems(["1280x720", "1920x1080", "2560x1440", "3840x2160"])
        self.resolution_combo.setCurrentText("1280x720")
        res_row.addWidget(self.resolution_combo, 1)
        res_row.addStretch(2)
        layout.addLayout(res_row)

        # Status
        status_box = QtWidgets.QGroupBox("状态")
        st_layout = QtWidgets.QVBoxLayout(status_box)
        self.status_label = QtWidgets.QLabel("● 就绪")
        self.status_label.setStyleSheet("color: #00ff00; font-size: 16px;")
        st_layout.addWidget(self.status_label)
        layout.addWidget(status_box)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("▶️ 启动游戏")
        self.start_button.setStyleSheet("background-color: #28a745; padding: 10px 14px; border-radius: 10px;")
        self.start_button.clicked.connect(self._start_game)
        self.stop_button = QtWidgets.QPushButton("⏹️ 停止游戏")
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("background-color: #dc3545; padding: 10px 14px; border-radius: 10px;")
        self.stop_button.clicked.connect(self._stop_game)
        view_log = QtWidgets.QPushButton("📄 查看日志")
        view_log.clicked.connect(self._view_log)
        btn_row.addWidget(self.start_button)
        btn_row.addWidget(self.stop_button)
        btn_row.addWidget(view_log)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # Preview
        preview = QtWidgets.QGroupBox("车辆预览")
        p_layout = QtWidgets.QVBoxLayout(preview)
        self.vehicle_info_label = QtWidgets.QLabel("请选择一个车辆配置")
        self.vehicle_info_label.setStyleSheet("color: #aaaaaa;")
        p_layout.addWidget(self.vehicle_info_label)
        layout.addWidget(preview)

        self._refresh_configs()

    def _hline(self) -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #333333;")
        return line

    def _build_config_row(self, label: str, *, kind: str) -> QtWidgets.QHBoxLayout:
        row = QtWidgets.QHBoxLayout()
        label_w = QtWidgets.QLabel(label)
        if kind == "vehicle":
            label_w.setToolTip("从 configs/vehicles 选择车辆配置。")
        elif kind == "map":
            label_w.setToolTip("从 configs/maps 选择地图配置（由“地图生成”模块自动保存）。")
        else:
            label_w.setToolTip("选择配置。")
        row.addWidget(label_w, 0)
        combo = QtWidgets.QComboBox()
        combo.setMinimumWidth(220)
        if kind == "vehicle":
            combo.setToolTip("选择车辆配置（configs/vehicles/*.json）。")
        elif kind == "map":
            combo.setToolTip("选择地图配置（configs/maps/*.json）。")
        else:
            combo.setToolTip("选择配置。")
        row.addWidget(combo, 0)

        refresh = QtWidgets.QPushButton("🔄 刷新")
        refresh.clicked.connect(self._refresh_configs)
        row.addWidget(refresh, 0)

        if kind == "vehicle":
            edit = QtWidgets.QPushButton("✏️ 编辑")
            edit.clicked.connect(self._edit_vehicle_config)
            row.addWidget(edit, 0)
            self.vehicle_combo = combo
            self.vehicle_combo.currentTextChanged.connect(self._on_vehicle_selected)
        elif kind == "map":
            gen = QtWidgets.QPushButton("🗺️ 地图生成")
            gen.setToolTip("打开“地图生成”模块，生成并自动保存地图配置。")
            gen.clicked.connect(self._open_map_generator)
            row.addWidget(gen, 0)
            self.map_combo = combo
            self.map_combo.currentTextChanged.connect(self._on_map_selected)

        row.addStretch(1)
        return row

    def _refresh_configs(self) -> None:
        config_mgr = self.get_config_manager()
        if not config_mgr:
            self.log("配置管理器未初始化", "error")
            return

        self.vehicle_configs = config_mgr.list_configs("vehicles")
        if self.vehicle_combo is not None:
            self.vehicle_combo.blockSignals(True)
            self.vehicle_combo.clear()
            self.vehicle_combo.addItems(self.vehicle_configs)
            self.vehicle_combo.blockSignals(False)
            if self.vehicle_configs:
                if self.selected_vehicle not in self.vehicle_configs:
                    self.selected_vehicle = self.vehicle_configs[0]
                self.vehicle_combo.setCurrentText(self.selected_vehicle)
                self._update_vehicle_info()

        self.map_configs = sorted(self.map_config_manager.list_configs())
        if self.map_combo is not None:
            self.map_combo.blockSignals(True)
            self.map_combo.clear()
            self.map_combo.addItems(self.map_configs)
            self.map_combo.blockSignals(False)
            if self.map_configs:
                if self.selected_map not in self.map_configs:
                    self.selected_map = self.map_configs[0]
                self.map_combo.setCurrentText(self.selected_map)

        self.log(f"已加载 {len(self.vehicle_configs)} 个车辆配置", "info")

    def _on_vehicle_selected(self, value: str) -> None:
        self.selected_vehicle = value or None
        self._update_vehicle_info()

    def _on_map_selected(self, value: str) -> None:
        self.selected_map = value or None

    def _update_vehicle_info(self) -> None:
        if not self.selected_vehicle or self.vehicle_info_label is None:
            return

        config_mgr = self.get_config_manager()
        if not config_mgr:
            return

        try:
            config = config_mgr.load_config("vehicles", self.selected_vehicle)
            name = config.get("name", self.selected_vehicle)
            mass = (
                config.get("chassis", {}).get("mass_kg")
                if isinstance(config.get("chassis"), dict)
                else config.get("vehicle_mass")
            )
            max_speed = (
                config.get("simple_physics", {}).get("max_speed_kmh")
                if isinstance(config.get("simple_physics"), dict)
                else config.get("physics", {}).get("max_speed")
            )
            info = f"{name} | 质量：{mass if mass is not None else 'N/A'}kg | 最高速度：{max_speed if max_speed is not None else 'N/A'}km/h"
            self.vehicle_info_label.setText(info)
        except Exception as e:
            self.vehicle_info_label.setText(f"加载失败：{e}")

    def _start_game(self) -> None:
        if self.process is not None and self.process.state() != QtCore.QProcess.NotRunning:
            self.log("游戏已在运行", "warning")
            return

        if not self.selected_vehicle:
            self.log("请选择一个车辆配置", "error")
            return

        args = ["main.py", "--vehicle", self.selected_vehicle]
        if self.selected_map:
            args += ["--map", self.selected_map]
        if self.debug_check is not None and self.debug_check.isChecked():
            args.append("--debug")
        if self.fullscreen_check is not None and self.fullscreen_check.isChecked():
            args.append("--fullscreen")
        if self.shadows_check is not None and not self.shadows_check.isChecked():
            args.append("--no-shadows")
        if self.resolution_combo is not None and self.resolution_combo.currentText():
            args += ["--resolution", self.resolution_combo.currentText()]

        if hasattr(self.console_app, "get_logs_dir"):
            logs_dir = self.console_app.get_logs_dir()
        else:
            logs_dir = os.path.join(os.getcwd(), "logs")
            os.makedirs(logs_dir, exist_ok=True)

        self._game_log_path = os.path.join(logs_dir, "game.log")

        self.log(f"启动游戏：{sys.executable} {' '.join(args)}", "info")
        if self.status_label is not None:
            self.status_label.setText("● 启动中...")
            self.status_label.setStyleSheet("color: #ffa500; font-size: 16px;")

        self.process = QtCore.QProcess()
        self.process.setWorkingDirectory(self.console_app.project_root if hasattr(self.console_app, "project_root") else os.getcwd())
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_process_output)
        self.process.finished.connect(self._on_process_finished)

        try:
            self._log_file = open(self._game_log_path, "a", encoding="utf-8")
        except Exception:
            self._log_file = None

        if self.start_button is not None:
            self.start_button.setEnabled(False)
        if self.stop_button is not None:
            self.stop_button.setEnabled(True)

        self.process.start(sys.executable, args)
        if not self.process.waitForStarted(3000):
            self.log("启动失败：无法启动进程", "error")
            self._close_log_file()
            if self.start_button is not None:
                self.start_button.setEnabled(True)
            if self.stop_button is not None:
                self.stop_button.setEnabled(False)
            if self.status_label is not None:
                self.status_label.setText("● 失败")
                self.status_label.setStyleSheet("color: #ff4444; font-size: 16px;")
            self.process = None
            return

        if self.status_label is not None:
            self.status_label.setText("● 运行中")
            self.status_label.setStyleSheet("color: #00ff00; font-size: 16px;")
        self.log("游戏已启动", "success")

    def _on_process_output(self) -> None:
        if not self.process:
            return
        data = bytes(self.process.readAllStandardOutput()).decode(errors="replace")
        if not data:
            return
        for line in data.splitlines():
            if self._log_file:
                try:
                    self._log_file.write(line + "\n")
                    self._log_file.flush()
                except Exception:
                    pass
            self.log(f"[游戏] {line}", "info")

    def _on_process_finished(self, exit_code: int, exit_status: QtCore.QProcess.ExitStatus) -> None:
        self._close_log_file()
        if self.start_button is not None:
            self.start_button.setEnabled(True)
        if self.stop_button is not None:
            self.stop_button.setEnabled(False)
        if self.status_label is not None:
            self.status_label.setText("● 已停止")
            self.status_label.setStyleSheet("color: #aaaaaa; font-size: 16px;")
        self.process = None
        self.log(f"游戏进程已退出（code={exit_code}）", "info")

    def _close_log_file(self) -> None:
        if self._log_file:
            try:
                self._log_file.close()
            except Exception:
                pass
        self._log_file = None

    def _stop_game(self) -> None:
        if not self.process or self.process.state() == QtCore.QProcess.NotRunning:
            self.log("游戏未运行", "warning")
            return
        self.process.terminate()
        if not self.process.waitForFinished(2000):
            self.process.kill()
        self.log("游戏已停止", "info")

    def _edit_vehicle_config(self) -> None:
        if not self.selected_vehicle:
            self.log("请先选择一个车辆配置", "warning")
            return
        # Switch to the vehicle editor module and preselect the current vehicle.
        self.log(f"编辑配置：{self.selected_vehicle}", "info")
        if hasattr(self.console_app, "switch_module"):
            setattr(self.console_app, "_vehicle_editor_open_id", self.selected_vehicle)
            self.console_app.switch_module("vehicle_editor")

    def _open_map_generator(self) -> None:
        self.log("切换到地图生成器", "info")
        if hasattr(self.console_app, "switch_module"):
            self.console_app.switch_module("map_generator")

    def _view_log(self) -> None:
        logs_dir = self.console_app.get_logs_dir() if hasattr(self.console_app, "get_logs_dir") else os.path.join(os.getcwd(), "logs")
        log_path = self._game_log_path or os.path.join(logs_dir, "game.log")
        if os.path.exists(log_path):
            self.log(f"日志文件：{log_path}", "info")
            try:
                system = platform.system()
                if system == "Darwin":
                    subprocess.run(["open", log_path])
                elif system == "Windows":
                    os.startfile(log_path)  # type: ignore[attr-defined]
                else:
                    subprocess.run(["xdg-open", log_path])
            except Exception as e:
                self.log(f"打开失败：{e}", "warning")
        else:
            self.log("日志文件不存在", "warning")

    def cleanup(self) -> None:
        if self.process and self.process.state() != QtCore.QProcess.NotRunning:
            self.process.kill()
        self._close_log_file()
