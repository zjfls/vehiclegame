# 🎮 Vehicle Game Console 使用指南

## 快速开始

### 1. 安装依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装控制台依赖
pip install PySide6
```

### 2. 启动控制台

```bash
python console.py
```

### 3. 使用功能

控制台提供以下功能模块：

#### 🚀 启动游戏
- 选择车辆配置（支持多辆车）
- 选择地图配置（由“🗺️ 地图生成”模块自动保存）
- 设置游戏选项（全屏、调试模式等）
- 点击"启动游戏"按钮

**预设车辆配置**:
- `sports_car` - 跑车（1500kg，最高 200km/h）
- `truck` - 卡车（3500kg，最高 120km/h）
- `offroad` - 越野车（2200kg，最高 160km/h）

#### 🛠️ 地形生成
- 设置地形参数（尺寸、噪声、高度等）
- 可选：启用轨道走廊刷平
- 点击"生成地形"按钮
- 输出到 `res/terrain/` 目录

#### 🗺️ 地图生成
- 选择已有地图配置（`configs/maps/*.json`）
- 新建地图配置（会立即出现在下拉列表中）
- 分步生成或一键生成：地形 / 颜色 / 赛道 / 场景
- 生成成功后自动保存（无需“加载/保存”按钮）

## 配置管理

### 配置目录结构

```
configs/
├── vehicles/
│   ├── sports_car.json
│   ├── truck.json
│   └── offroad.json
├── maps/                  # 地图配置（自动保存）
├── tracks/                # 赛道运行时配置（生成输出）
└── scenery/               # 场景元素配置（生成输出）
```

### 创建自定义车辆配置

1. 复制现有配置：
```bash
cp configs/vehicles/sports_car.json configs/vehicles/my_car.json
```

2. 编辑 JSON 文件，修改参数：
```json
{
  "name": "My Custom Car",
  "vehicle_mass": 1800.0,
  "physics": {
    "max_speed": 180.0,
    "acceleration": 70.0,
    ...
  }
}
```

3. 在控制台中选择新配置启动游戏

### 配置参数说明

#### 核心参数
| 参数 | 说明 | 示例值 |
|-----|------|--------|
| `vehicle_mass` | 车辆总质量（kg） | 1500.0 |
| `name` | 车辆名称 | "Sports Car" |
| `position` | 初始位置 [x, y, z] | [0, 0, 12.0] |

#### 物理系统 (`physics`)
| 参数 | 说明 | 示例值 |
|-----|------|--------|
| `max_speed` | 最高速度（km/h） | 200.0 |
| `acceleration` | 加速度 | 80.0 |
| `brake_deceleration` | 刹车减速度 | 120.0 |
| `drag_coefficient` | 风阻系数 | 0.3 |

#### 悬挂系统 (`suspension`)
| 参数 | 说明 | 示例值 |
|-----|------|--------|
| `com_position` | 质心位置 | [0, 0, 0.3] |
| `wheels` | 四轮配置数组 | [...] |

#### 传动系统 (`transmission`)
| 参数 | 说明 | 示例值 |
|-----|------|--------|
| `gear_ratios` | 档位速比 | [0, 3.5, 2.5, ...] |
| `final_ratio` | 最终传动比 | 3.5 |
| `auto_shift` | 自动换挡 | true |

## 地形生成参数

### 基本参数
| 参数 | 说明 | 默认值 |
|-----|------|--------|
| `width` | 宽度（像素） | 1024 |
| `height` | 高度（像素） | 1024 |
| `seed` | 随机种子 | 42 |
| `base_frequency` | 噪声基础频率 | 0.003 |
| `octaves` | FBM 叠加层数 | 5 |
| `persistence` | 幅度衰减系数 | 0.5 |
| `lacunarity` | 频率增长系数 | 2.0 |
| `smooth_sigma` | 高斯平滑强度 | 2.5 |
| `relief_strength` | 全局起伏强度(0..1) | 0.25 |

### 轨道走廊参数
| 参数 | 说明 | 默认值 |
|-----|------|--------|
| `track-csv` | 赛道 CSV 文件 | scripts/track_example.csv |
| `track-coord-space` | 坐标空间（normalized/pixel） | normalized |
| `corridor-width-px` | 走廊宽度（像素） | 120 |
| `edge-falloff-px` | 边缘衰减（像素） | 50 |
| `track-flatten-strength` | 刷平强度(0..1) | 0.9 |

## 命令行参数（可选）

当前控制台仅提供 GUI 入口：`python console.py`。

## 故障排除

### 问题：PySide6 未安装/启动失败
**解决**:
```bash
pip install --upgrade PySide6
```

### 问题：游戏无法启动
**检查**:
1. Panda3D 是否安装：`pip list | grep panda3d`
2. 查看日志：`cat logs/game.log`

### 问题：地形生成失败
**检查**:
1. scipy 是否安装：`pip list | grep scipy`
2. 检查输出目录权限：`ls -la res/terrain/`

## 扩展开发

### 添加新模块

1. 创建模块文件 `console_modules/my_module.py`:
```python
from PySide6 import QtWidgets
from console_modules.base_module import ConsoleModule

class MyModule(ConsoleModule):
    name = "my_module"
    display_name = "🔧 我的模块"
    
    def build_ui(self, parent):
        label = QtWidgets.QLabel("我的功能")
        parent.addWidget(label)
```

2. 在 `console.py` 的 `_register_modules()` 中导入并注册:
```python
from console_modules.my_module import MyModule

def _register_modules(self):
    self.modules["game_launcher"] = GameLauncherModule(self)
    self.modules["terrain_generator"] = TerrainGeneratorModule(self)
    self.modules["my_module"] = MyModule(self)  # 新增
```

## 技术架构

```
console.py              # 入口脚本 + 应用主类
core/
├── config_manager.py   # 配置管理
├── map_config_manager.py # 地图配置管理（configs/maps）
└── process_manager.py  # 进程管理
console_modules/
├── base_module.py      # 模块基类
├── game_launcher.py    # 游戏启动模块
├── terrain_generator.py # 地形生成模块
└── map_generator.py     # 地图生成模块
configs/
├── vehicles/           # 车辆配置
├── maps/               # 地图配置（自动保存）
├── tracks/             # 赛道输出
└── scenery/            # 场景输出
```

## 更新日志

### v0.1.0 (2025)
- ✨ 初始版本
- 🚀 游戏启动（支持多车辆配置）
- 🛠️ 地形生成工具
- ⚙️ 配置管理
- 📊 可视化界面

---

**许可证**: MIT
