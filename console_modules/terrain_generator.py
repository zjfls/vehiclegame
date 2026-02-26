"""
地形生成模块 - PySide6 (Qt) 版本
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from typing import Any, Optional

from PySide6 import QtCore, QtWidgets

from console_modules.base_module import ConsoleModule


class TerrainGeneratorModule(ConsoleModule):
    name = "terrain_generator"
    display_name = "地形生成"
    icon = "🛠️"
    description = "生成程序化地形高度图"

    def __init__(self, console_app: Any):
        super().__init__(console_app)
        self.process: Optional[QtCore.QProcess] = None

        # UI refs
        self.width_edit: Optional[QtWidgets.QLineEdit] = None
        self.height_edit: Optional[QtWidgets.QLineEdit] = None
        self.seed_edit: Optional[QtWidgets.QLineEdit] = None
        self.noise_scale_edit: Optional[QtWidgets.QLineEdit] = None
        self.octaves_edit: Optional[QtWidgets.QLineEdit] = None
        self.persistence_edit: Optional[QtWidgets.QLineEdit] = None
        self.lacunarity_edit: Optional[QtWidgets.QLineEdit] = None
        self.height_scale_edit: Optional[QtWidgets.QLineEdit] = None
        self.output_edit: Optional[QtWidgets.QLineEdit] = None

        self.track_check: Optional[QtWidgets.QCheckBox] = None
        self.track_csv_edit: Optional[QtWidgets.QLineEdit] = None
        self.corridor_edit: Optional[QtWidgets.QLineEdit] = None
        self.edge_edit: Optional[QtWidgets.QLineEdit] = None
        self.track_group: Optional[QtWidgets.QGroupBox] = None

        self.log_text: Optional[QtWidgets.QTextEdit] = None
        self.status_label: Optional[QtWidgets.QLabel] = None
        self.progress_bar: Optional[QtWidgets.QProgressBar] = None
        self.generate_button: Optional[QtWidgets.QPushButton] = None

        self._log_file = None

    def build_ui(self, parent) -> None:
        layout: QtWidgets.QVBoxLayout = parent

        title = QtWidgets.QLabel("🛠️ 地形参数配置")
        font = title.font()
        font.setPointSize(22)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        layout.addWidget(self._hline())

        # Basic params
        basic = QtWidgets.QGroupBox("基本参数")
        b = QtWidgets.QFormLayout(basic)
        b.setLabelAlignment(QtCore.Qt.AlignLeft)
        self.width_edit = QtWidgets.QLineEdit("1024")
        self.height_edit = QtWidgets.QLineEdit("1024")
        self.seed_edit = QtWidgets.QLineEdit("12345")
        b.addRow("宽度 (px):", self.width_edit)
        b.addRow("高度 (px):", self.height_edit)
        b.addRow("种子:", self.seed_edit)
        layout.addWidget(basic)

        noise = QtWidgets.QGroupBox("噪声参数")
        n = QtWidgets.QFormLayout(noise)
        self.noise_scale_edit = QtWidgets.QLineEdit("0.05")
        self.octaves_edit = QtWidgets.QLineEdit("5")
        self.persistence_edit = QtWidgets.QLineEdit("0.5")
        self.lacunarity_edit = QtWidgets.QLineEdit("2.0")
        n.addRow("噪声缩放:", self.noise_scale_edit)
        n.addRow("八度音:", self.octaves_edit)
        n.addRow("持久性:", self.persistence_edit)
        n.addRow("Lacunarity:", self.lacunarity_edit)
        layout.addWidget(noise)

        height = QtWidgets.QGroupBox("高度参数")
        h = QtWidgets.QFormLayout(height)
        self.height_scale_edit = QtWidgets.QLineEdit("20.0")
        h.addRow("高度缩放:", self.height_scale_edit)
        layout.addWidget(height)

        out = QtWidgets.QGroupBox("输出")
        o = QtWidgets.QFormLayout(out)
        self.output_edit = QtWidgets.QLineEdit("generated_terrain")
        o.addRow("输出文件名:", self.output_edit)
        layout.addWidget(out)

        # Track options
        self.track_group = QtWidgets.QGroupBox("轨道走廊（可选）")
        t_layout = QtWidgets.QVBoxLayout(self.track_group)
        self.track_check = QtWidgets.QCheckBox("启用轨道走廊刷平")
        self.track_check.stateChanged.connect(self._toggle_track_options)
        t_layout.addWidget(self.track_check)

        form = QtWidgets.QFormLayout()
        self.track_csv_edit = QtWidgets.QLineEdit("scripts/track_example.csv")
        self.corridor_edit = QtWidgets.QLineEdit("120")
        self.edge_edit = QtWidgets.QLineEdit("50")
        form.addRow("赛道 CSV:", self.track_csv_edit)
        form.addRow("走廊宽度(px):", self.corridor_edit)
        form.addRow("边缘衰减(px):", self.edge_edit)
        t_layout.addLayout(form)
        self._set_track_form_enabled(False)
        layout.addWidget(self.track_group)

        # Status
        status = QtWidgets.QGroupBox("状态")
        s = QtWidgets.QHBoxLayout(status)
        self.status_label = QtWidgets.QLabel("● 就绪")
        self.status_label.setStyleSheet("color: #00ff00; font-size: 16px;")
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        s.addWidget(self.status_label, 0)
        s.addWidget(self.progress_bar, 1)
        layout.addWidget(status)

        # Buttons
        btns = QtWidgets.QHBoxLayout()
        self.generate_button = QtWidgets.QPushButton("🛠️ 生成地形")
        self.generate_button.setStyleSheet("background-color: #28a745; padding: 10px 14px; border-radius: 10px;")
        self.generate_button.clicked.connect(self._generate_terrain)
        open_dir = QtWidgets.QPushButton("📁 打开输出目录")
        open_dir.clicked.connect(self._open_output_dir)
        docs = QtWidgets.QPushButton("📖 查看文档")
        docs.clicked.connect(self._view_docs)
        btns.addWidget(self.generate_button)
        btns.addWidget(open_dir)
        btns.addWidget(docs)
        btns.addStretch(1)
        layout.addLayout(btns)

        # Logs
        logs = QtWidgets.QGroupBox("生成日志")
        l = QtWidgets.QVBoxLayout(logs)
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(180)
        l.addWidget(self.log_text)
        layout.addWidget(logs)

    def _hline(self) -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #333333;")
        return line

    def _set_track_form_enabled(self, enabled: bool) -> None:
        for w in (self.track_csv_edit, self.corridor_edit, self.edge_edit):
            if w is not None:
                w.setEnabled(enabled)

    def _toggle_track_options(self) -> None:
        enabled = self.track_check is not None and self.track_check.isChecked()
        self._set_track_form_enabled(enabled)

    def _append_log(self, message: str, level: str = "info") -> None:
        import datetime

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] [{level.upper()}] {message}"
        if self.log_text is not None:
            self.log_text.append(line)
        super().log(message, level)

    def _generate_terrain(self) -> None:
        if self.process is not None and self.process.state() != QtCore.QProcess.NotRunning:
            self._append_log("地形正在生成中", "warning")
            return

        try:
            width = int(self.width_edit.text()) if self.width_edit else 1024
            height = int(self.height_edit.text()) if self.height_edit else 1024
            seed = int(self.seed_edit.text()) if self.seed_edit else 12345
            noise_scale = float(self.noise_scale_edit.text()) if self.noise_scale_edit else 0.05
            octaves = int(self.octaves_edit.text()) if self.octaves_edit else 5
            persistence = float(self.persistence_edit.text()) if self.persistence_edit else 0.5
            lacunarity = float(self.lacunarity_edit.text()) if self.lacunarity_edit else 2.0
            height_scale = float(self.height_scale_edit.text()) if self.height_scale_edit else 20.0
            output_name = (self.output_edit.text().strip() if self.output_edit else "generated_terrain") or "generated_terrain"
        except ValueError as e:
            self._append_log(f"参数格式错误：{e}", "error")
            return

        args = [
            "scripts/generate_terrain.py",
            f"--width={width}",
            f"--height={height}",
            f"--seed={seed}",
            f"--name={output_name}",
            f"--noise-scale={noise_scale}",
            f"--octaves={octaves}",
            f"--persistence={persistence}",
            f"--lacunarity={lacunarity}",
            f"--height-scale={height_scale}",
        ]

        use_track = self.track_check is not None and self.track_check.isChecked()
        if use_track:
            track_csv = self.track_csv_edit.text().strip() if self.track_csv_edit else "scripts/track_example.csv"
            try:
                corridor = int(self.corridor_edit.text()) if self.corridor_edit else 120
                edge = int(self.edge_edit.text()) if self.edge_edit else 50
            except ValueError as e:
                self._append_log(f"轨道参数格式错误：{e}", "error")
                return
            args += [f"--track-csv={track_csv}", f"--corridor-width-px={corridor}", f"--edge-falloff-px={edge}"]

        self._append_log(f"命令：{sys.executable} {' '.join(args)}", "info")

        if self.status_label is not None:
            self.status_label.setText("● 生成中...")
            self.status_label.setStyleSheet("color: #ffa500; font-size: 16px;")
        if self.progress_bar is not None:
            self.progress_bar.setRange(0, 0)  # busy
        if self.generate_button is not None:
            self.generate_button.setEnabled(False)

        logs_dir = self.console_app.get_logs_dir() if hasattr(self.console_app, "get_logs_dir") else os.path.join(os.getcwd(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, "terrain_gen.log")
        try:
            self._log_file = open(log_path, "a", encoding="utf-8")
        except Exception:
            self._log_file = None

        self.process = QtCore.QProcess()
        self.process.setWorkingDirectory(self.console_app.project_root if hasattr(self.console_app, "project_root") else os.getcwd())
        self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._on_output)
        self.process.finished.connect(self._on_finished)
        self.process.start(sys.executable, args)

    def _on_output(self) -> None:
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
            self._append_log(line, "info")

    def _on_finished(self, exit_code: int, exit_status: QtCore.QProcess.ExitStatus) -> None:
        if self._log_file:
            try:
                self._log_file.close()
            except Exception:
                pass
        self._log_file = None

        if self.generate_button is not None:
            self.generate_button.setEnabled(True)
        if self.progress_bar is not None:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(1 if exit_code == 0 else 0)

        if exit_code == 0:
            self._append_log("地形生成完成！", "success")
            if self.status_label is not None:
                self.status_label.setText("● 成功")
                self.status_label.setStyleSheet("color: #00ff00; font-size: 16px;")
        else:
            self._append_log(f"生成失败，退出码：{exit_code}", "error")
            if self.status_label is not None:
                self.status_label.setText("● 失败")
                self.status_label.setStyleSheet("color: #ff4444; font-size: 16px;")

        self.process = None

    def _open_output_dir(self) -> None:
        output_dir = os.path.join(self.console_app.project_root if hasattr(self.console_app, "project_root") else os.getcwd(), "res", "terrain")
        if os.path.exists(output_dir):
            try:
                system = platform.system()
                if system == "Darwin":
                    subprocess.run(["open", output_dir])
                elif system == "Windows":
                    os.startfile(output_dir)  # type: ignore[attr-defined]
                else:
                    subprocess.run(["xdg-open", output_dir])
                self._append_log(f"已打开目录：{output_dir}", "info")
            except Exception as e:
                self._append_log(f"打开目录失败：{e}", "warning")
        else:
            self._append_log(f"目录不存在：{output_dir}", "warning")

    def _view_docs(self) -> None:
        self._append_log("查看 README.md 了解地形生成文档", "info")

    def cleanup(self) -> None:
        if self.process and self.process.state() != QtCore.QProcess.NotRunning:
            self.process.kill()
        if self._log_file:
            try:
                self._log_file.close()
            except Exception:
                pass
        self._log_file = None

