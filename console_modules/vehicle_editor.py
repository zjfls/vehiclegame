"""Vehicle config editor module (v2 schema).

This is a pragmatic editor for tweaking the new v2 vehicle configs stored under
`configs/vehicles/*.json`.

The module intentionally focuses on the most impactful parameters:
- Chassis mass/geometry
- Powertrain (engine torque curve, gearbox, clutch, differential)
- Wheels / tires / suspension per-wheel params

The simulation core will evolve, but keeping configs in one schema and editable
from the console is the top priority.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from console_modules.base_module import ConsoleModule
from core.vehicle_config_loader import VehicleConfigError, normalize_v2, validate_v2


def _fmt_float(x: object, default: float = 0.0) -> str:
    try:
        return str(float(x))
    except Exception:
        return str(float(default))


class VehicleEditorModule(ConsoleModule):
    name = "vehicle_editor"
    display_name = "车辆配置"
    icon = "\U0001f697"  # car
    description = "编辑车辆配置（v2 schema）"

    def __init__(self, console_app: Any):
        super().__init__(console_app)
        self._cfg_id: Optional[str] = None
        self._cfg: Optional[Dict[str, Any]] = None

        # UI refs
        self.config_combo: Optional[QtWidgets.QComboBox] = None
        self.validation_label: Optional[QtWidgets.QLabel] = None
        self.json_text: Optional[QtWidgets.QTextEdit] = None

        # Basics
        self.name_edit: Optional[QtWidgets.QLineEdit] = None
        self.spawn_x: Optional[QtWidgets.QDoubleSpinBox] = None
        self.spawn_y: Optional[QtWidgets.QDoubleSpinBox] = None
        self.spawn_z: Optional[QtWidgets.QDoubleSpinBox] = None
        self.spawn_heading: Optional[QtWidgets.QDoubleSpinBox] = None

        self.mass_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.cg_h_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.wheelbase_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.track_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.iz_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.steer_max_spin: Optional[QtWidgets.QDoubleSpinBox] = None

        # Powertrain
        self.engine_idle_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.engine_max_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.engine_moi_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.torque_table: Optional[QtWidgets.QTableWidget] = None

        self.gear_ratios_edit: Optional[QtWidgets.QLineEdit] = None
        self.final_drive_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.reverse_ratio_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.auto_shift_check: Optional[QtWidgets.QCheckBox] = None
        self.shift_time_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.shift_up_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.shift_down_spin: Optional[QtWidgets.QDoubleSpinBox] = None

        self.clutch_strength_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.clutch_engage_spin: Optional[QtWidgets.QDoubleSpinBox] = None

        self.diff_type_combo: Optional[QtWidgets.QComboBox] = None
        self.diff_layout_combo: Optional[QtWidgets.QComboBox] = None
        self.diff_split_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.diff_front_bias_spin: Optional[QtWidgets.QDoubleSpinBox] = None
        self.diff_rear_bias_spin: Optional[QtWidgets.QDoubleSpinBox] = None

        # Per-wheel tables
        self.wheels_table: Optional[QtWidgets.QTableWidget] = None
        self.tires_table: Optional[QtWidgets.QTableWidget] = None
        self.susp_table: Optional[QtWidgets.QTableWidget] = None

    def _hline(self) -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #333333;")
        return line

    def build_ui(self, parent) -> None:
        layout: QtWidgets.QVBoxLayout = parent

        title = QtWidgets.QLabel("\U0001f697 车辆配置编辑")
        font = title.font()
        font.setPointSize(22)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        layout.addWidget(self._hline())

        # Toolbar
        tb = QtWidgets.QHBoxLayout()
        tb.addWidget(QtWidgets.QLabel("车辆:"), 0)

        self.config_combo = QtWidgets.QComboBox()
        self.config_combo.setMinimumWidth(260)
        self.config_combo.currentTextChanged.connect(self._on_select_vehicle)
        tb.addWidget(self.config_combo, 0)

        refresh = QtWidgets.QPushButton("\U0001f504 刷新")
        refresh.clicked.connect(self._refresh_list)
        tb.addWidget(refresh, 0)

        new_btn = QtWidgets.QPushButton("\u2795 新建")
        new_btn.clicked.connect(self._on_new)
        tb.addWidget(new_btn, 0)

        copy_btn = QtWidgets.QPushButton("\u29c9 复制")
        copy_btn.clicked.connect(self._on_duplicate)
        tb.addWidget(copy_btn, 0)

        save_btn = QtWidgets.QPushButton("\U0001f4be 保存")
        save_btn.setStyleSheet("background-color: #28a745; padding: 8px 12px; border-radius: 8px;")
        save_btn.clicked.connect(self._on_save)
        tb.addWidget(save_btn, 0)

        save_as_btn = QtWidgets.QPushButton("\U0001f4be 另存为")
        save_as_btn.clicked.connect(self._on_save_as)
        tb.addWidget(save_as_btn, 0)

        delete_btn = QtWidgets.QPushButton("\U0001f5d1 删除")
        delete_btn.clicked.connect(self._on_delete)
        tb.addWidget(delete_btn, 0)

        tb.addStretch(1)
        layout.addLayout(tb)

        # Main: tabs + validation panel
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(14)
        layout.addLayout(row, 1)

        tabs = QtWidgets.QTabWidget()
        tabs.setDocumentMode(True)
        row.addWidget(tabs, 1)

        # Right side: validation + JSON
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right.setMaximumWidth(420)
        row.addWidget(right, 0)

        val_group = QtWidgets.QGroupBox("校验")
        val_layout = QtWidgets.QVBoxLayout(val_group)
        self.validation_label = QtWidgets.QLabel("请选择一个车辆配置")
        self.validation_label.setWordWrap(True)
        self.validation_label.setStyleSheet("color: #aaaaaa;")
        val_layout.addWidget(self.validation_label)
        right_layout.addWidget(val_group)

        json_group = QtWidgets.QGroupBox("配置 JSON")
        j_layout = QtWidgets.QVBoxLayout(json_group)
        self.json_text = QtWidgets.QTextEdit()
        self.json_text.setFont(QtGui.QFont("Consolas", 9))
        self.json_text.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        j_layout.addWidget(self.json_text, 1)
        apply_json = QtWidgets.QPushButton("\u2714 应用 JSON")
        apply_json.clicked.connect(self._on_apply_json)
        j_layout.addWidget(apply_json, 0)
        right_layout.addWidget(json_group, 1)

        # Tabs content
        tabs.addTab(self._build_tab_basic(), "基础")
        tabs.addTab(self._build_tab_powertrain(), "动力系统")
        tabs.addTab(self._build_tab_wheels(), "车轮")
        tabs.addTab(self._build_tab_tires(), "轮胎")
        tabs.addTab(self._build_tab_suspension(), "悬挂")

        self._refresh_list()

    def on_show(self) -> None:
        # If another module asked to open a specific vehicle, honor it.
        target = getattr(self.console_app, "_vehicle_editor_open_id", None)
        if isinstance(target, str) and target:
            setattr(self.console_app, "_vehicle_editor_open_id", None)
            if self.config_combo is not None:
                self.config_combo.setCurrentText(target)

    # ---------- UI builders ----------

    def _build_tab_basic(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        g = QtWidgets.QGroupBox("Spawn / Chassis")
        grid = QtWidgets.QGridLayout(g)
        grid.setContentsMargins(12, 16, 12, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self.name_edit = QtWidgets.QLineEdit()
        grid.addWidget(QtWidgets.QLabel("名称"), 0, 0)
        grid.addWidget(self.name_edit, 0, 1, 1, 3)

        self.spawn_x = self._spin(-100000, 100000, 2, 0.0)
        self.spawn_y = self._spin(-100000, 100000, 2, 0.0)
        self.spawn_z = self._spin(-100000, 100000, 2, 12.0)
        self.spawn_heading = self._spin(-3600, 3600, 2, 0.0)
        grid.addWidget(QtWidgets.QLabel("出生 X/Y/Z"), 1, 0)
        pos_row = QtWidgets.QHBoxLayout()
        pos_row.addWidget(self.spawn_x)
        pos_row.addWidget(self.spawn_y)
        pos_row.addWidget(self.spawn_z)
        grid.addLayout(pos_row, 1, 1, 1, 3)
        grid.addWidget(QtWidgets.QLabel("朝向 H(deg)"), 2, 0)
        grid.addWidget(self.spawn_heading, 2, 1)

        self.mass_spin = self._spin(1, 50000, 1, 1500.0)
        self.cg_h_spin = self._spin(0.05, 5.0, 3, 0.55)
        self.wheelbase_spin = self._spin(0.5, 10.0, 3, 2.6)
        self.track_spin = self._spin(0.5, 10.0, 3, 1.8)
        self.iz_spin = self._spin(1, 1e9, 1, 2000.0)
        self.steer_max_spin = self._spin(1, 90, 1, 35.0)

        grid.addWidget(QtWidgets.QLabel("质量 (kg)"), 3, 0)
        grid.addWidget(self.mass_spin, 3, 1)
        grid.addWidget(QtWidgets.QLabel("CG高度 (m)"), 3, 2)
        grid.addWidget(self.cg_h_spin, 3, 3)

        grid.addWidget(QtWidgets.QLabel("轴距 (m)"), 4, 0)
        grid.addWidget(self.wheelbase_spin, 4, 1)
        grid.addWidget(QtWidgets.QLabel("轮距 (m)"), 4, 2)
        grid.addWidget(self.track_spin, 4, 3)

        grid.addWidget(QtWidgets.QLabel("Yaw惯量 Iz"), 5, 0)
        grid.addWidget(self.iz_spin, 5, 1)
        grid.addWidget(QtWidgets.QLabel("最大转向 (deg)"), 5, 2)
        grid.addWidget(self.steer_max_spin, 5, 3)

        layout.addWidget(g)
        layout.addStretch(1)
        return w

    def _build_tab_powertrain(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Engine
        engine = QtWidgets.QGroupBox("Engine")
        grid = QtWidgets.QGridLayout(engine)
        grid.setContentsMargins(12, 16, 12, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self.engine_idle_spin = self._spin(0, 20000, 0, 800)
        self.engine_max_spin = self._spin(500, 30000, 0, 6000)
        self.engine_moi_spin = self._spin(0.01, 100.0, 3, 1.0)
        grid.addWidget(QtWidgets.QLabel("Idle RPM"), 0, 0)
        grid.addWidget(self.engine_idle_spin, 0, 1)
        grid.addWidget(QtWidgets.QLabel("Max RPM"), 0, 2)
        grid.addWidget(self.engine_max_spin, 0, 3)
        grid.addWidget(QtWidgets.QLabel("MOI (kgm2)"), 1, 0)
        grid.addWidget(self.engine_moi_spin, 1, 1)

        self.torque_table = QtWidgets.QTableWidget(0, 2)
        self.torque_table.setHorizontalHeaderLabels(["RPM", "Torque (Nm)"])
        self.torque_table.horizontalHeader().setStretchLastSection(True)
        self.torque_table.verticalHeader().setVisible(False)
        self.torque_table.setMinimumHeight(180)
        grid.addWidget(QtWidgets.QLabel("Torque Curve"), 2, 0)
        grid.addWidget(self.torque_table, 2, 1, 1, 3)

        btns = QtWidgets.QHBoxLayout()
        add_pt = QtWidgets.QPushButton("+ 点")
        add_pt.clicked.connect(self._on_add_torque_point)
        rm_pt = QtWidgets.QPushButton("- 点")
        rm_pt.clicked.connect(self._on_remove_torque_point)
        sort_pt = QtWidgets.QPushButton("排序")
        sort_pt.clicked.connect(self._on_sort_torque)
        btns.addWidget(add_pt)
        btns.addWidget(rm_pt)
        btns.addWidget(sort_pt)
        btns.addStretch(1)
        grid.addLayout(btns, 3, 1, 1, 3)

        layout.addWidget(engine)

        # Gearbox / clutch / diff
        pt = QtWidgets.QGroupBox("Gearbox / Clutch / Differential")
        g2 = QtWidgets.QGridLayout(pt)
        g2.setContentsMargins(12, 16, 12, 12)
        g2.setHorizontalSpacing(12)
        g2.setVerticalSpacing(10)

        self.gear_ratios_edit = QtWidgets.QLineEdit()
        self.gear_ratios_edit.setPlaceholderText("e.g. 0, 3.5, 2.5, 1.8, 1.4, 1.0")
        g2.addWidget(QtWidgets.QLabel("Gear ratios"), 0, 0)
        g2.addWidget(self.gear_ratios_edit, 0, 1, 1, 3)

        self.final_drive_spin = self._spin(0.1, 20.0, 3, 3.5)
        self.reverse_ratio_spin = self._spin(-20.0, -0.01, 3, -3.5)
        g2.addWidget(QtWidgets.QLabel("Final drive"), 1, 0)
        g2.addWidget(self.final_drive_spin, 1, 1)
        g2.addWidget(QtWidgets.QLabel("Reverse ratio"), 1, 2)
        g2.addWidget(self.reverse_ratio_spin, 1, 3)

        self.auto_shift_check = QtWidgets.QCheckBox("Auto shift")
        self.auto_shift_check.setChecked(True)
        self.shift_time_spin = self._spin(0.0, 3.0, 3, 0.3)
        self.shift_up_spin = self._spin(0.1, 1.0, 2, 0.85)
        self.shift_down_spin = self._spin(0.1, 1.0, 2, 0.35)
        g2.addWidget(self.auto_shift_check, 2, 0)
        g2.addWidget(QtWidgets.QLabel("Shift time (s)"), 2, 1)
        g2.addWidget(self.shift_time_spin, 2, 2)
        g2.addWidget(QtWidgets.QLabel("Up/Down ratio"), 3, 0)
        updown = QtWidgets.QHBoxLayout()
        updown.addWidget(self.shift_up_spin)
        updown.addWidget(self.shift_down_spin)
        g2.addLayout(updown, 3, 1, 1, 3)

        self.clutch_strength_spin = self._spin(0.1, 1000.0, 2, 10.0)
        self.clutch_engage_spin = self._spin(0.01, 2.0, 3, 0.2)
        g2.addWidget(QtWidgets.QLabel("Clutch strength"), 4, 0)
        g2.addWidget(self.clutch_strength_spin, 4, 1)
        g2.addWidget(QtWidgets.QLabel("Clutch engage (s)"), 4, 2)
        g2.addWidget(self.clutch_engage_spin, 4, 3)

        self.diff_type_combo = QtWidgets.QComboBox()
        self.diff_type_combo.addItems(["open", "limited_slip"])
        self.diff_layout_combo = QtWidgets.QComboBox()
        self.diff_layout_combo.addItems(["FWD", "RWD", "AWD"])
        self.diff_split_spin = self._spin(0.0, 1.0, 3, 0.5)
        self.diff_front_bias_spin = self._spin(1.0, 10.0, 2, 1.5)
        self.diff_rear_bias_spin = self._spin(1.0, 10.0, 2, 2.0)
        g2.addWidget(QtWidgets.QLabel("Diff type"), 5, 0)
        g2.addWidget(self.diff_type_combo, 5, 1)
        g2.addWidget(QtWidgets.QLabel("Layout"), 5, 2)
        g2.addWidget(self.diff_layout_combo, 5, 3)
        g2.addWidget(QtWidgets.QLabel("Front/Rear split"), 6, 0)
        g2.addWidget(self.diff_split_spin, 6, 1)
        g2.addWidget(QtWidgets.QLabel("Bias F/R"), 6, 2)
        bias = QtWidgets.QHBoxLayout()
        bias.addWidget(self.diff_front_bias_spin)
        bias.addWidget(self.diff_rear_bias_spin)
        g2.addLayout(bias, 6, 3)

        layout.addWidget(pt)
        layout.addStretch(1)
        return w

    def _build_tab_wheels(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        self.wheels_table = QtWidgets.QTableWidget(0, 8)
        self.wheels_table.setHorizontalHeaderLabels(
            ["X", "Y", "Z", "Radius", "Inertia", "BrakeMax", "Steer", "Driven"]
        )
        self.wheels_table.horizontalHeader().setStretchLastSection(True)
        self.wheels_table.verticalHeader().setVisible(False)
        layout.addWidget(self.wheels_table, 1)

        tip = QtWidgets.QLabel("坐标系: Panda3D (X右, Y前, Z上)。Wheel pos 是车辆局部坐标。")
        tip.setStyleSheet("color: #888888;")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        return w

    def _build_tab_tires(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tires_table = QtWidgets.QTableWidget(0, 4)
        self.tires_table.setHorizontalHeaderLabels(["Mu", "Long stiff", "Lat stiff", "Lat stiff max load"])
        self.tires_table.horizontalHeader().setStretchLastSection(True)
        self.tires_table.verticalHeader().setVisible(False)
        layout.addWidget(self.tires_table, 1)
        return w

    def _build_tab_suspension(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        self.susp_table = QtWidgets.QTableWidget(0, 8)
        self.susp_table.setHorizontalHeaderLabels(
            ["X", "Y", "Z", "Freq (Hz)", "Damping", "RestLen", "MaxComp", "MaxDroop"]
        )
        self.susp_table.horizontalHeader().setStretchLastSection(True)
        self.susp_table.verticalHeader().setVisible(False)
        layout.addWidget(self.susp_table, 1)
        return w

    def _spin(self, lo: float, hi: float, decimals: int, value: float) -> QtWidgets.QDoubleSpinBox:
        s = QtWidgets.QDoubleSpinBox()
        s.setRange(float(lo), float(hi))
        s.setDecimals(int(decimals))
        s.setValue(float(value))
        s.setSingleStep(0.1 if decimals >= 1 else 1.0)
        s.setKeyboardTracking(False)
        return s

    # ---------- Data binding ----------

    def _refresh_list(self) -> None:
        cfg_mgr = self.get_config_manager()
        if not cfg_mgr or self.config_combo is None:
            return
        ids = cfg_mgr.list_configs("vehicles")
        self.config_combo.blockSignals(True)
        self.config_combo.clear()
        self.config_combo.addItems(ids)
        self.config_combo.blockSignals(False)
        if ids and self._cfg_id not in ids:
            self.config_combo.setCurrentText(ids[0])

    def _on_select_vehicle(self, vehicle_id: str) -> None:
        if not vehicle_id:
            return
        self._load_vehicle(vehicle_id)

    def _load_vehicle(self, vehicle_id: str) -> None:
        cfg_mgr = self.get_config_manager()
        if not cfg_mgr:
            self._set_validation(["ConfigManager not available"], is_error=True)
            return

        try:
            raw = cfg_mgr.load_config("vehicles", vehicle_id)
            cfg = normalize_v2(raw)
            errs = validate_v2(cfg)
            if errs:
                self._set_validation(errs, is_error=True)
            else:
                self._set_validation(["OK"], is_error=False)
            self._cfg_id = vehicle_id
            self._cfg = cfg
            self._populate_ui(cfg)
            self._render_json(cfg)
        except Exception as e:
            self._set_validation([str(e)], is_error=True)

    def _populate_ui(self, cfg: Dict[str, Any]) -> None:
        if self.name_edit is not None:
            self.name_edit.setText(str(cfg.get("name") or ""))

        spawn = cfg.get("spawn") if isinstance(cfg.get("spawn"), dict) else {}
        pos = spawn.get("position_m")
        if not (isinstance(pos, (list, tuple)) and len(pos) >= 3):
            pos = [0.0, 0.0, 12.0]
        if self.spawn_x is not None:
            self.spawn_x.setValue(float(pos[0]))
        if self.spawn_y is not None:
            self.spawn_y.setValue(float(pos[1]))
        if self.spawn_z is not None:
            self.spawn_z.setValue(float(pos[2]))
        if self.spawn_heading is not None:
            self.spawn_heading.setValue(float(spawn.get("heading_deg", 0.0) or 0.0))

        chassis = cfg.get("chassis") if isinstance(cfg.get("chassis"), dict) else {}
        if self.mass_spin is not None:
            self.mass_spin.setValue(float(chassis.get("mass_kg", 1500.0) or 1500.0))
        if self.cg_h_spin is not None:
            self.cg_h_spin.setValue(float(chassis.get("cg_height_m", 0.55) or 0.55))
        if self.wheelbase_spin is not None:
            self.wheelbase_spin.setValue(float(chassis.get("wheelbase_m", 2.6) or 2.6))
        if self.track_spin is not None:
            self.track_spin.setValue(float(chassis.get("track_width_m", 1.8) or 1.8))
        if self.iz_spin is not None:
            self.iz_spin.setValue(float(chassis.get("yaw_inertia_kgm2", 2000.0) or 2000.0))

        controls = cfg.get("controls") if isinstance(cfg.get("controls"), dict) else {}
        if self.steer_max_spin is not None:
            self.steer_max_spin.setValue(float(controls.get("steer_max_deg", 35.0) or 35.0))

        pt = cfg.get("powertrain") if isinstance(cfg.get("powertrain"), dict) else {}
        engine = pt.get("engine") if isinstance(pt.get("engine"), dict) else {}
        if self.engine_idle_spin is not None:
            self.engine_idle_spin.setValue(float(engine.get("idle_rpm", 800.0) or 800.0))
        if self.engine_max_spin is not None:
            self.engine_max_spin.setValue(float(engine.get("max_rpm", 6000.0) or 6000.0))
        if self.engine_moi_spin is not None:
            self.engine_moi_spin.setValue(float(engine.get("moi_kgm2", 1.0) or 1.0))
        self._fill_torque_table(engine.get("torque_curve_nm") or [])

        gearbox = pt.get("gearbox") if isinstance(pt.get("gearbox"), dict) else {}
        if self.gear_ratios_edit is not None:
            ratios = gearbox.get("ratios")
            if isinstance(ratios, list):
                self.gear_ratios_edit.setText(", ".join(_fmt_float(x) for x in ratios))
            else:
                self.gear_ratios_edit.setText("0, 3.5, 2.5, 1.8, 1.4, 1.0")
        if self.final_drive_spin is not None:
            self.final_drive_spin.setValue(float(gearbox.get("final_drive", 3.5) or 3.5))
        if self.reverse_ratio_spin is not None:
            self.reverse_ratio_spin.setValue(float(gearbox.get("reverse_ratio", -3.5) or -3.5))
        if self.auto_shift_check is not None:
            self.auto_shift_check.setChecked(bool(gearbox.get("auto_shift", True)))
        if self.shift_time_spin is not None:
            self.shift_time_spin.setValue(float(gearbox.get("shift_time_s", 0.3) or 0.3))
        if self.shift_up_spin is not None:
            self.shift_up_spin.setValue(float(gearbox.get("shift_rpm_up_ratio", 0.85) or 0.85))
        if self.shift_down_spin is not None:
            self.shift_down_spin.setValue(float(gearbox.get("shift_rpm_down_ratio", 0.35) or 0.35))

        clutch = pt.get("clutch") if isinstance(pt.get("clutch"), dict) else {}
        if self.clutch_strength_spin is not None:
            self.clutch_strength_spin.setValue(float(clutch.get("strength", 10.0) or 10.0))
        if self.clutch_engage_spin is not None:
            self.clutch_engage_spin.setValue(float(clutch.get("engage_time_s", 0.2) or 0.2))

        diff = pt.get("differential") if isinstance(pt.get("differential"), dict) else {}
        if self.diff_type_combo is not None:
            self.diff_type_combo.setCurrentText(str(diff.get("type") or "limited_slip"))
        if self.diff_layout_combo is not None:
            self.diff_layout_combo.setCurrentText(str(diff.get("layout") or "AWD"))
        if self.diff_split_spin is not None:
            self.diff_split_spin.setValue(float(diff.get("front_rear_split", 0.5) or 0.5))
        if self.diff_front_bias_spin is not None:
            self.diff_front_bias_spin.setValue(float(diff.get("front_bias", 1.5) or 1.5))
        if self.diff_rear_bias_spin is not None:
            self.diff_rear_bias_spin.setValue(float(diff.get("rear_bias", 2.0) or 2.0))

        self._fill_wheels_table(cfg.get("wheels") or [])
        self._fill_tires_table(cfg.get("tires") or [])
        susp = cfg.get("suspension") if isinstance(cfg.get("suspension"), dict) else {}
        self._fill_susp_table(susp.get("wheels") or [])

    def _gather_ui(self) -> Dict[str, Any]:
        cfg = dict(self._cfg or {})
        cfg["version"] = 2
        cfg["name"] = self.name_edit.text().strip() if self.name_edit is not None else cfg.get("name")

        spawn = dict(cfg.get("spawn") or {})
        spawn["position_m"] = [
            float(self.spawn_x.value()) if self.spawn_x is not None else 0.0,
            float(self.spawn_y.value()) if self.spawn_y is not None else 0.0,
            float(self.spawn_z.value()) if self.spawn_z is not None else 12.0,
        ]
        spawn["heading_deg"] = float(self.spawn_heading.value()) if self.spawn_heading is not None else 0.0
        cfg["spawn"] = spawn

        chassis = dict(cfg.get("chassis") or {})
        chassis["mass_kg"] = float(self.mass_spin.value()) if self.mass_spin is not None else float(chassis.get("mass_kg", 1500.0) or 1500.0)
        chassis["cg_height_m"] = float(self.cg_h_spin.value()) if self.cg_h_spin is not None else float(chassis.get("cg_height_m", 0.55) or 0.55)
        chassis["wheelbase_m"] = float(self.wheelbase_spin.value()) if self.wheelbase_spin is not None else float(chassis.get("wheelbase_m", 2.6) or 2.6)
        chassis["track_width_m"] = float(self.track_spin.value()) if self.track_spin is not None else float(chassis.get("track_width_m", 1.8) or 1.8)
        chassis["yaw_inertia_kgm2"] = float(self.iz_spin.value()) if self.iz_spin is not None else float(chassis.get("yaw_inertia_kgm2", 2000.0) or 2000.0)
        cfg["chassis"] = chassis

        controls = dict(cfg.get("controls") or {})
        controls["steer_max_deg"] = float(self.steer_max_spin.value()) if self.steer_max_spin is not None else float(controls.get("steer_max_deg", 35.0) or 35.0)
        cfg["controls"] = controls

        pt = dict(cfg.get("powertrain") or {})
        engine = dict(pt.get("engine") or {})
        if self.engine_idle_spin is not None:
            engine["idle_rpm"] = float(self.engine_idle_spin.value())
        if self.engine_max_spin is not None:
            engine["max_rpm"] = float(self.engine_max_spin.value())
        if self.engine_moi_spin is not None:
            engine["moi_kgm2"] = float(self.engine_moi_spin.value())
        engine["torque_curve_nm"] = self._read_torque_table()
        pt["engine"] = engine

        gearbox = dict(pt.get("gearbox") or {})
        if self.gear_ratios_edit is not None:
            gearbox["ratios"] = self._parse_csv_floats(self.gear_ratios_edit.text(), default=[0.0, 3.5, 2.5, 1.8, 1.4, 1.0])
        if self.final_drive_spin is not None:
            gearbox["final_drive"] = float(self.final_drive_spin.value())
        if self.reverse_ratio_spin is not None:
            gearbox["reverse_ratio"] = float(self.reverse_ratio_spin.value())
        if self.auto_shift_check is not None:
            gearbox["auto_shift"] = bool(self.auto_shift_check.isChecked())
        if self.shift_time_spin is not None:
            gearbox["shift_time_s"] = float(self.shift_time_spin.value())
        if self.shift_up_spin is not None:
            gearbox["shift_rpm_up_ratio"] = float(self.shift_up_spin.value())
        if self.shift_down_spin is not None:
            gearbox["shift_rpm_down_ratio"] = float(self.shift_down_spin.value())
        pt["gearbox"] = gearbox

        clutch = dict(pt.get("clutch") or {})
        if self.clutch_strength_spin is not None:
            clutch["strength"] = float(self.clutch_strength_spin.value())
        if self.clutch_engage_spin is not None:
            clutch["engage_time_s"] = float(self.clutch_engage_spin.value())
        pt["clutch"] = clutch

        diff = dict(pt.get("differential") or {})
        if self.diff_type_combo is not None:
            diff["type"] = str(self.diff_type_combo.currentText())
        if self.diff_layout_combo is not None:
            diff["layout"] = str(self.diff_layout_combo.currentText())
        if self.diff_split_spin is not None:
            diff["front_rear_split"] = float(self.diff_split_spin.value())
        if self.diff_front_bias_spin is not None:
            diff["front_bias"] = float(self.diff_front_bias_spin.value())
        if self.diff_rear_bias_spin is not None:
            diff["rear_bias"] = float(self.diff_rear_bias_spin.value())
        pt["differential"] = diff

        cfg["powertrain"] = pt

        cfg["wheels"] = self._read_wheels_table()
        cfg["tires"] = self._read_tires_table()
        suspension = dict(cfg.get("suspension") or {})
        suspension["wheels"] = self._read_susp_table()
        cfg["suspension"] = suspension

        # Keep JSON view in sync.
        cfg = normalize_v2(cfg)
        return cfg

    # ---------- Actions ----------

    def _on_save(self) -> None:
        if not self._cfg_id:
            self.log("请选择一个车辆配置", "warning")
            return
        cfg_mgr = self.get_config_manager()
        if not cfg_mgr:
            return
        cfg = self._gather_ui()
        errs = validate_v2(cfg)
        if errs:
            self._set_validation(errs, is_error=True)
            self.log("配置校验失败，无法保存", "error")
            return
        cfg_mgr.save_config("vehicles", self._cfg_id, cfg)
        self._cfg = cfg
        self._set_validation(["Saved"], is_error=False)
        self._render_json(cfg)
        self.log(f"已保存车辆配置: {self._cfg_id}", "success")

    def _on_save_as(self) -> None:
        if not self._cfg:
            self.log("没有可保存的配置", "warning")
            return
        cfg_mgr = self.get_config_manager()
        if not cfg_mgr:
            return
        text, ok = QtWidgets.QInputDialog.getText(None, "另存为", "新配置 ID (文件名):")
        if not ok:
            return
        new_id = (text or "").strip()
        if not new_id:
            return
        cfg = self._gather_ui()
        errs = validate_v2(cfg)
        if errs:
            self._set_validation(errs, is_error=True)
            self.log("配置校验失败，无法另存", "error")
            return
        cfg_mgr.save_config("vehicles", new_id, cfg)
        self._refresh_list()
        if self.config_combo is not None:
            self.config_combo.setCurrentText(new_id)
        self.log(f"已另存为车辆配置: {new_id}", "success")

    def _on_new(self) -> None:
        cfg_mgr = self.get_config_manager()
        if not cfg_mgr:
            return
        text, ok = QtWidgets.QInputDialog.getText(None, "新建车辆", "新配置 ID (文件名):")
        if not ok:
            return
        new_id = (text or "").strip()
        if not new_id:
            return
        # Use sports_car as a starter template.
        try:
            base = cfg_mgr.load_config("vehicles", "sports_car")
        except Exception:
            base = {
                "version": 2,
                "name": "New Vehicle",
                "spawn": {"position_m": [0.0, 0.0, 12.0], "heading_deg": 0.0},
                "chassis": {"mass_kg": 1500.0, "cg_height_m": 0.55, "wheelbase_m": 2.6, "track_width_m": 1.8, "yaw_inertia_kgm2": 2000.0},
                "controls": {"steer_max_deg": 35.0, "input_smoothing": {}},
                "aero": {"cd": 0.35, "frontal_area_m2": 2.2, "rolling_resistance": 0.016},
                "simple_physics": {},
                "powertrain": {},
                "wheels": [],
                "tires": [],
                "suspension": {"wheels": []},
            }
        cfg = normalize_v2(base)
        cfg["name"] = f"{cfg.get('name', 'Vehicle')} (copy)"
        cfg_mgr.save_config("vehicles", new_id, cfg)
        self._refresh_list()
        if self.config_combo is not None:
            self.config_combo.setCurrentText(new_id)
        self.log(f"已新建车辆配置: {new_id}", "success")

    def _on_duplicate(self) -> None:
        if not self._cfg_id or not self._cfg:
            self.log("请先选择一个车辆配置", "warning")
            return
        text, ok = QtWidgets.QInputDialog.getText(None, "复制车辆", "新配置 ID (文件名):")
        if not ok:
            return
        new_id = (text or "").strip()
        if not new_id:
            return
        cfg_mgr = self.get_config_manager()
        if not cfg_mgr:
            return
        cfg = self._gather_ui()
        errs = validate_v2(cfg)
        if errs:
            self._set_validation(errs, is_error=True)
            self.log("配置校验失败，无法复制", "error")
            return
        cfg_mgr.save_config("vehicles", new_id, cfg)
        self._refresh_list()
        if self.config_combo is not None:
            self.config_combo.setCurrentText(new_id)
        self.log(f"已复制车辆配置: {self._cfg_id} -> {new_id}", "success")

    def _on_delete(self) -> None:
        if not self._cfg_id:
            return
        cfg_mgr = self.get_config_manager()
        if not cfg_mgr:
            return
        reply = QtWidgets.QMessageBox.question(
            None,
            "删除车辆配置",
            f"确定删除 '{self._cfg_id}'?\n这将删除 configs/vehicles/{self._cfg_id}.json",
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        ok = cfg_mgr.delete_config("vehicles", self._cfg_id)
        if ok:
            self.log(f"已删除车辆配置: {self._cfg_id}", "success")
            self._cfg_id = None
            self._cfg = None
            self._refresh_list()
        else:
            self.log("删除失败", "error")

    def _on_apply_json(self) -> None:
        if self.json_text is None:
            return
        try:
            data = json.loads(self.json_text.toPlainText())
            cfg = normalize_v2(data)
            errs = validate_v2(cfg)
            if errs:
                self._set_validation(errs, is_error=True)
                return
            self._cfg = cfg
            self._populate_ui(cfg)
            self._set_validation(["JSON applied"], is_error=False)
        except Exception as e:
            self._set_validation([str(e)], is_error=True)

    # ---------- Helpers ----------

    def _set_validation(self, messages: List[str], *, is_error: bool) -> None:
        if self.validation_label is None:
            return
        if not messages:
            messages = ["OK"]
        text = "\n".join(messages)
        self.validation_label.setText(text)
        self.validation_label.setStyleSheet("color: #ff7777;" if is_error else "color: #88ff88;")

    def _render_json(self, cfg: Dict[str, Any]) -> None:
        if self.json_text is None:
            return
        self.json_text.blockSignals(True)
        self.json_text.setPlainText(json.dumps(cfg, indent=2, ensure_ascii=False))
        self.json_text.blockSignals(False)

    def _parse_csv_floats(self, text: str, *, default: List[float]) -> List[float]:
        parts = [p.strip() for p in (text or "").split(",") if p.strip()]
        out: List[float] = []
        for p in parts:
            try:
                out.append(float(p))
            except Exception:
                pass
        return out if out else list(default)

    # Torque curve table
    def _fill_torque_table(self, curve: List[Any]) -> None:
        if self.torque_table is None:
            return
        pts = []
        for p in curve:
            if isinstance(p, (list, tuple)) and len(p) >= 2:
                try:
                    pts.append((float(p[0]), float(p[1])))
                except Exception:
                    pass
        pts.sort(key=lambda x: x[0])
        self.torque_table.setRowCount(len(pts))
        for i, (rpm, tq) in enumerate(pts):
            self.torque_table.setItem(i, 0, QtWidgets.QTableWidgetItem(str(int(rpm))))
            self.torque_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(float(tq))))

    def _read_torque_table(self) -> List[List[float]]:
        if self.torque_table is None:
            return []
        pts: List[Tuple[float, float]] = []
        for i in range(self.torque_table.rowCount()):
            rpm_item = self.torque_table.item(i, 0)
            tq_item = self.torque_table.item(i, 1)
            try:
                rpm = float(rpm_item.text()) if rpm_item else 0.0
                tq = float(tq_item.text()) if tq_item else 0.0
                pts.append((rpm, tq))
            except Exception:
                pass
        pts.sort(key=lambda x: x[0])
        return [[rpm, tq] for rpm, tq in pts]

    def _on_add_torque_point(self) -> None:
        if self.torque_table is None:
            return
        r = self.torque_table.rowCount()
        self.torque_table.insertRow(r)
        self.torque_table.setItem(r, 0, QtWidgets.QTableWidgetItem("0"))
        self.torque_table.setItem(r, 1, QtWidgets.QTableWidgetItem("0"))

    def _on_remove_torque_point(self) -> None:
        if self.torque_table is None:
            return
        rows = {i.row() for i in self.torque_table.selectedIndexes()}
        for r in sorted(rows, reverse=True):
            self.torque_table.removeRow(r)

    def _on_sort_torque(self) -> None:
        self._fill_torque_table(self._read_torque_table())

    # Wheels table
    def _fill_wheels_table(self, wheels: List[Any]) -> None:
        if self.wheels_table is None:
            return
        self.wheels_table.setRowCount(len(wheels))
        for i, w in enumerate(wheels):
            if not isinstance(w, dict):
                w = {}
            pos = w.get("position_local_m")
            if not (isinstance(pos, (list, tuple)) and len(pos) >= 3):
                pos = [0.0, 0.0, 0.0]
            vals = [
                float(pos[0]),
                float(pos[1]),
                float(pos[2]),
                float(w.get("radius_m", 0.35) or 0.35),
                float(w.get("inertia_kgm2", 1.0) or 1.0),
                float(w.get("brake_max_torque_nm", 1000.0) or 1000.0),
            ]
            for c, v in enumerate(vals):
                self.wheels_table.setItem(i, c, QtWidgets.QTableWidgetItem(_fmt_float(v)))

            steer_item = QtWidgets.QTableWidgetItem("")
            steer_item.setFlags(steer_item.flags() | QtCore.Qt.ItemIsUserCheckable)
            steer_item.setCheckState(QtCore.Qt.Checked if bool(w.get("can_steer")) else QtCore.Qt.Unchecked)
            self.wheels_table.setItem(i, 6, steer_item)

            driven_item = QtWidgets.QTableWidgetItem("")
            driven_item.setFlags(driven_item.flags() | QtCore.Qt.ItemIsUserCheckable)
            driven_item.setCheckState(QtCore.Qt.Checked if bool(w.get("is_driven")) else QtCore.Qt.Unchecked)
            self.wheels_table.setItem(i, 7, driven_item)

    def _read_wheels_table(self) -> List[Dict[str, Any]]:
        if self.wheels_table is None:
            return []
        out: List[Dict[str, Any]] = []
        for i in range(self.wheels_table.rowCount()):
            def getf(col: int, default: float = 0.0) -> float:
                item = self.wheels_table.item(i, col)
                try:
                    return float(item.text()) if item else float(default)
                except Exception:
                    return float(default)

            steer_item = self.wheels_table.item(i, 6)
            driven_item = self.wheels_table.item(i, 7)

            out.append(
                {
                    "position_local_m": [getf(0), getf(1), getf(2)],
                    "radius_m": max(0.05, getf(3, 0.35)),
                    "inertia_kgm2": max(1e-6, getf(4, 1.0)),
                    "brake_max_torque_nm": max(0.0, getf(5, 1000.0)),
                    "can_steer": bool(steer_item.checkState() == QtCore.Qt.Checked) if steer_item else False,
                    "is_driven": bool(driven_item.checkState() == QtCore.Qt.Checked) if driven_item else False,
                }
            )
        return out

    # Tires table
    def _fill_tires_table(self, tires: List[Any]) -> None:
        if self.tires_table is None:
            return
        self.tires_table.setRowCount(len(tires))
        for i, t in enumerate(tires):
            if not isinstance(t, dict):
                t = {}
            vals = [
                float(t.get("mu", 1.0) or 1.0),
                float(t.get("long_stiff", 1000.0) or 1000.0),
                float(t.get("lat_stiff", 17.0) or 17.0),
                float(t.get("lat_stiff_max_load", 2.0) or 2.0),
            ]
            for c, v in enumerate(vals):
                self.tires_table.setItem(i, c, QtWidgets.QTableWidgetItem(_fmt_float(v)))

    def _read_tires_table(self) -> List[Dict[str, Any]]:
        if self.tires_table is None:
            return []
        out: List[Dict[str, Any]] = []
        for i in range(self.tires_table.rowCount()):
            def getf(col: int, default: float) -> float:
                item = self.tires_table.item(i, col)
                try:
                    return float(item.text()) if item else float(default)
                except Exception:
                    return float(default)

            out.append(
                {
                    "mu": getf(0, 1.0),
                    "long_stiff": getf(1, 1000.0),
                    "lat_stiff": getf(2, 17.0),
                    "lat_stiff_max_load": getf(3, 2.0),
                }
            )
        return out

    # Suspension table
    def _fill_susp_table(self, wheels: List[Any]) -> None:
        if self.susp_table is None:
            return
        self.susp_table.setRowCount(len(wheels))
        for i, sw in enumerate(wheels):
            if not isinstance(sw, dict):
                sw = {}
            pos = sw.get("position_local_m")
            if not (isinstance(pos, (list, tuple)) and len(pos) >= 3):
                pos = [0.0, 0.0, 0.0]
            vals = [
                float(pos[0]),
                float(pos[1]),
                float(pos[2]),
                float(sw.get("natural_frequency_hz", 7.0) or 7.0),
                float(sw.get("damping_ratio", 1.0) or 1.0),
                float(sw.get("rest_length_m", 0.3) or 0.3),
                float(sw.get("max_compression_m", 0.1) or 0.1),
                float(sw.get("max_droop_m", 0.1) or 0.1),
            ]
            for c, v in enumerate(vals):
                self.susp_table.setItem(i, c, QtWidgets.QTableWidgetItem(_fmt_float(v)))

    def _read_susp_table(self) -> List[Dict[str, Any]]:
        if self.susp_table is None:
            return []
        out: List[Dict[str, Any]] = []
        for i in range(self.susp_table.rowCount()):
            def getf(col: int, default: float = 0.0) -> float:
                item = self.susp_table.item(i, col)
                try:
                    return float(item.text()) if item else float(default)
                except Exception:
                    return float(default)

            out.append(
                {
                    "position_local_m": [getf(0), getf(1), getf(2)],
                    "natural_frequency_hz": getf(3, 7.0),
                    "damping_ratio": getf(4, 1.0),
                    "rest_length_m": getf(5, 0.3),
                    "max_compression_m": getf(6, 0.1),
                    "max_droop_m": getf(7, 0.1),
                }
            )
        return out

