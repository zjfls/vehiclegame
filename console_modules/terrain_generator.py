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
        self.generator_combo: Optional[QtWidgets.QComboBox] = None
        self.base_frequency_edit: Optional[QtWidgets.QLineEdit] = None
        self.octaves_edit: Optional[QtWidgets.QLineEdit] = None
        self.persistence_edit: Optional[QtWidgets.QLineEdit] = None
        self.lacunarity_edit: Optional[QtWidgets.QLineEdit] = None
        self.smooth_sigma_edit: Optional[QtWidgets.QLineEdit] = None
        self.relief_strength_edit: Optional[QtWidgets.QLineEdit] = None
        self.output_edit: Optional[QtWidgets.QLineEdit] = None

        self.track_check: Optional[QtWidgets.QCheckBox] = None
        self.track_csv_edit: Optional[QtWidgets.QLineEdit] = None
        self.track_coord_combo: Optional[QtWidgets.QComboBox] = None
        self.corridor_edit: Optional[QtWidgets.QLineEdit] = None
        self.edge_edit: Optional[QtWidgets.QLineEdit] = None
        self.track_strength_edit: Optional[QtWidgets.QLineEdit] = None
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

        def _tip(widget: Optional[QtWidgets.QWidget], text: str) -> None:
            if widget is not None:
                widget.setToolTip(text)

        def _label(text: str, tip: Optional[str] = None) -> QtWidgets.QLabel:
            w = QtWidgets.QLabel(text)
            if tip:
                w.setToolTip(tip)
            w.setStyleSheet("color: #cfcfcf;")
            return w

        # Main content: params (left) + status/log (right)
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        layout.addLayout(row, 1)

        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left.setMaximumWidth(560)

        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        row.addWidget(left, 0)
        row.addWidget(right, 1)

        # Basic params (match scripts/generate_terrain.py)
        basic = QtWidgets.QGroupBox("基础参数")
        b = QtWidgets.QGridLayout(basic)
        b.setHorizontalSpacing(12)
        b.setVerticalSpacing(10)
        b.setContentsMargins(12, 16, 12, 12)
        b.setColumnStretch(1, 1)
        b.setColumnStretch(3, 1)

        self.width_edit = QtWidgets.QLineEdit("1024")
        self.height_edit = QtWidgets.QLineEdit("1024")
        self.seed_edit = QtWidgets.QLineEdit("42")
        self.generator_combo = QtWidgets.QComboBox()
        self.generator_combo.addItems(["opensimplex", "noise"])
        self.generator_combo.setCurrentText("opensimplex")
        self.output_edit = QtWidgets.QLineEdit("race_base")

        tip_width = "高度图宽度（像素）。越大越清晰，但生成/加载更慢。"
        tip_height = "高度图高度（像素）。越大越清晰，但生成/加载更慢。"
        tip_seed = "随机种子：相同 seed + 相同参数会生成相同地形。"
        tip_gen = "噪声生成器：opensimplex 通常更平滑；noise 需要额外依赖 noise。"
        tip_name = "输出文件名前缀：生成到 res/terrain/<name>.pgm/.npy/.json。"

        b.addWidget(_label("宽度 (px)", tip_width), 0, 0)
        b.addWidget(self.width_edit, 0, 1)
        b.addWidget(_label("高度 (px)", tip_height), 0, 2)
        b.addWidget(self.height_edit, 0, 3)
        b.addWidget(_label("种子", tip_seed), 1, 0)
        b.addWidget(self.seed_edit, 1, 1)
        b.addWidget(_label("生成器", tip_gen), 1, 2)
        b.addWidget(self.generator_combo, 1, 3)
        b.addWidget(_label("输出名称", tip_name), 2, 0)
        b.addWidget(self.output_edit, 2, 1, 1, 3)

        _tip(self.width_edit, tip_width)
        _tip(self.height_edit, tip_height)
        _tip(self.seed_edit, tip_seed)
        _tip(self.generator_combo, tip_gen)
        _tip(self.output_edit, tip_name)
        left_layout.addWidget(basic)

        # Noise params
        noise = QtWidgets.QGroupBox("噪声参数")
        n = QtWidgets.QGridLayout(noise)
        n.setHorizontalSpacing(12)
        n.setVerticalSpacing(10)
        n.setContentsMargins(12, 16, 12, 12)
        n.setColumnStretch(1, 1)
        n.setColumnStretch(3, 1)

        self.base_frequency_edit = QtWidgets.QLineEdit("0.003")
        self.octaves_edit = QtWidgets.QLineEdit("5")
        self.persistence_edit = QtWidgets.QLineEdit("0.5")
        self.lacunarity_edit = QtWidgets.QLineEdit("2.0")

        tip_freq = "基础频率（base_frequency）。越大：细节更密；越小：地形变化更缓。"
        tip_oct = "Octaves：叠加噪声层数。更高更细节，但更慢。"
        tip_pers = "Persistence：每层幅度衰减系数（0..1）。越大细节更明显。"
        tip_lac = "Lacunarity：每层频率增长系数（通常 > 1）。越大细节更密。"

        n.addWidget(_label("基础频率", tip_freq), 0, 0)
        n.addWidget(self.base_frequency_edit, 0, 1)
        n.addWidget(_label("Octaves", tip_oct), 0, 2)
        n.addWidget(self.octaves_edit, 0, 3)
        n.addWidget(_label("Persistence", tip_pers), 1, 0)
        n.addWidget(self.persistence_edit, 1, 1)
        n.addWidget(_label("Lacunarity", tip_lac), 1, 2)
        n.addWidget(self.lacunarity_edit, 1, 3)

        _tip(self.base_frequency_edit, tip_freq)
        _tip(self.octaves_edit, tip_oct)
        _tip(self.persistence_edit, tip_pers)
        _tip(self.lacunarity_edit, tip_lac)
        left_layout.addWidget(noise)

        # Smoothing / relief
        sculpt = QtWidgets.QGroupBox("平滑与起伏")
        sc = QtWidgets.QGridLayout(sculpt)
        sc.setHorizontalSpacing(12)
        sc.setVerticalSpacing(10)
        sc.setContentsMargins(12, 16, 12, 12)
        sc.setColumnStretch(1, 1)
        sc.setColumnStretch(3, 1)

        self.smooth_sigma_edit = QtWidgets.QLineEdit("2.5")
        self.relief_strength_edit = QtWidgets.QLineEdit("0.25")

        tip_sigma = "平滑强度（smooth_sigma）：高斯滤波 σ。越大越平滑。"
        tip_relief = "全局起伏强度（relief_strength，0..1）：越小越平坦。"

        sc.addWidget(_label("平滑 σ", tip_sigma), 0, 0)
        sc.addWidget(self.smooth_sigma_edit, 0, 1)
        sc.addWidget(_label("起伏强度", tip_relief), 0, 2)
        sc.addWidget(self.relief_strength_edit, 0, 3)

        _tip(self.smooth_sigma_edit, tip_sigma)
        _tip(self.relief_strength_edit, tip_relief)
        left_layout.addWidget(sculpt)

        # Track options
        self.track_group = QtWidgets.QGroupBox("轨道走廊（可选）")
        t_layout = QtWidgets.QVBoxLayout(self.track_group)
        t_layout.setContentsMargins(12, 16, 12, 12)
        t_layout.setSpacing(10)

        self.track_check = QtWidgets.QCheckBox("启用轨道走廊刷平")
        tip_track = "启用后会根据 CSV 轨迹将赛道附近区域刷平，并在边缘平滑过渡（需要 scipy 才能生效）。"
        _tip(self.track_check, tip_track)
        self.track_check.stateChanged.connect(self._toggle_track_options)
        t_layout.addWidget(self.track_check)

        tg = QtWidgets.QGridLayout()
        tg.setHorizontalSpacing(12)
        tg.setVerticalSpacing(10)
        tg.setColumnStretch(1, 1)
        tg.setColumnStretch(3, 1)

        self.track_csv_edit = QtWidgets.QLineEdit("scripts/track_example.csv")
        self.track_coord_combo = QtWidgets.QComboBox()
        self.track_coord_combo.addItems(["normalized", "pixel"])
        self.track_coord_combo.setCurrentText("normalized")
        self.corridor_edit = QtWidgets.QLineEdit("90")
        self.edge_edit = QtWidgets.QLineEdit("40")
        self.track_strength_edit = QtWidgets.QLineEdit("0.9")

        tip_track_csv = "赛道中心线点 CSV 路径（相对项目根目录或绝对路径）。示例：scripts/track_example.csv"
        tip_coord = "坐标空间：normalized 表示 0..1；pixel 表示像素坐标。"
        tip_corridor = "走廊宽度（像素，corridor_width_px）：以中心线为中轴的总宽度。"
        tip_edge = "边缘衰减（像素，edge_falloff_px）：从走廊边缘到完全不影响的过渡宽度。"
        tip_strength = "刷平强度（0..1）：越大越接近“刷平 + 平滑”的目标高度。"

        tg.addWidget(_label("赛道 CSV", tip_track_csv), 0, 0)
        tg.addWidget(self.track_csv_edit, 0, 1, 1, 3)
        tg.addWidget(_label("坐标空间", tip_coord), 1, 0)
        tg.addWidget(self.track_coord_combo, 1, 1)
        tg.addWidget(_label("走廊宽度(px)", tip_corridor), 1, 2)
        tg.addWidget(self.corridor_edit, 1, 3)
        tg.addWidget(_label("边缘衰减(px)", tip_edge), 2, 0)
        tg.addWidget(self.edge_edit, 2, 1)
        tg.addWidget(_label("刷平强度", tip_strength), 2, 2)
        tg.addWidget(self.track_strength_edit, 2, 3)

        _tip(self.track_csv_edit, tip_track_csv)
        _tip(self.track_coord_combo, tip_coord)
        _tip(self.corridor_edit, tip_corridor)
        _tip(self.edge_edit, tip_edge)
        _tip(self.track_strength_edit, tip_strength)

        t_layout.addLayout(tg)
        self._set_track_form_enabled(False)
        left_layout.addWidget(self.track_group)

        left_layout.addStretch(1)

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
        right_layout.addWidget(status)

        # Buttons
        btns_box = QtWidgets.QGroupBox("操作")
        btns_box.setContentsMargins(0, 0, 0, 0)
        btns = QtWidgets.QHBoxLayout(btns_box)
        btns.setContentsMargins(12, 12, 12, 12)
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
        right_layout.addWidget(btns_box)

        # Logs
        logs = QtWidgets.QGroupBox("生成日志")
        l = QtWidgets.QVBoxLayout(logs)
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(360)
        l.addWidget(self.log_text)
        right_layout.addWidget(logs, 1)

    def _hline(self) -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #333333;")
        return line

    def _set_track_form_enabled(self, enabled: bool) -> None:
        for w in (self.track_csv_edit, self.track_coord_combo, self.corridor_edit, self.edge_edit, self.track_strength_edit):
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
            seed = int(self.seed_edit.text()) if self.seed_edit else 42
            generator = self.generator_combo.currentText().strip() if self.generator_combo else "opensimplex"
            base_frequency = float(self.base_frequency_edit.text()) if self.base_frequency_edit else 0.003
            octaves = int(self.octaves_edit.text()) if self.octaves_edit else 5
            persistence = float(self.persistence_edit.text()) if self.persistence_edit else 0.5
            lacunarity = float(self.lacunarity_edit.text()) if self.lacunarity_edit else 2.0
            smooth_sigma = float(self.smooth_sigma_edit.text()) if self.smooth_sigma_edit else 2.5
            relief_strength = float(self.relief_strength_edit.text()) if self.relief_strength_edit else 0.25
            output_name = (self.output_edit.text().strip() if self.output_edit else "race_base") or "race_base"
        except ValueError as e:
            self._append_log(f"参数格式错误：{e}", "error")
            return

        args = [
            "scripts/generate_terrain.py",
            f"--width={width}",
            f"--height={height}",
            f"--seed={seed}",
            f"--generator={generator}",
            f"--name={output_name}",
            f"--octaves={octaves}",
            f"--base-frequency={base_frequency}",
            f"--persistence={persistence}",
            f"--lacunarity={lacunarity}",
            f"--smooth-sigma={smooth_sigma}",
            f"--relief-strength={relief_strength}",
        ]

        use_track = self.track_check is not None and self.track_check.isChecked()
        if use_track:
            track_csv = self.track_csv_edit.text().strip() if self.track_csv_edit else "scripts/track_example.csv"
            coord_space = self.track_coord_combo.currentText().strip() if self.track_coord_combo else "normalized"
            try:
                corridor = float(self.corridor_edit.text()) if self.corridor_edit else 90.0
                edge = float(self.edge_edit.text()) if self.edge_edit else 40.0
                strength = float(self.track_strength_edit.text()) if self.track_strength_edit else 0.9
            except ValueError as e:
                self._append_log(f"轨道参数格式错误：{e}", "error")
                return
            if not track_csv:
                self._append_log("已启用轨道走廊，但赛道 CSV 为空", "error")
                return
            args += [
                f"--track-csv={track_csv}",
                f"--track-coord-space={coord_space}",
                f"--corridor-width-px={corridor}",
                f"--edge-falloff-px={edge}",
                f"--track-flatten-strength={strength}",
            ]

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
