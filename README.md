# 🎮 Panda3D 赛车游戏

一个基于 Panda3D 的轻量赛车项目，包含：车辆物理系统、可视化主循环、地形生成脚本、游戏控制台。

## 📚 文档约定

- `README.md`：真源文档（以此为准）
- `docs/console/CONSOLE.md`：游戏控制台使用指南
- `docs/console/PROJECT_STRUCTURE.md`：项目结构详解
- `docs/console/requirement_design.md`：需求与设计概要
- `docs/console/tools.md`：工具接口与调用方法

## 🚀 快速开始

### 方式一：直接启动游戏

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

### 方式二：使用游戏控制台（推荐）

```bash
# 启动控制台
python console.py
```

## 🎯 功能特性

### 游戏控制台 ✨ NEW

控制台提供可视化界面，支持：

- **🚀 游戏启动**
  - 多车辆配置选择（跑车/卡车/越野车）
  - 地图配置选择（由“地图生成”模块自动保存）
  - 游戏设置（全屏/调试模式）
  - 实时状态监控

- **🗺️ 地图生成**
  - 选择/新建地图配置（自动出现在列表中）
  - 分步生成（地形/颜色/赛道/场景）与一键生成
  - 生成成功后自动保存到 `configs/maps/`

### 车辆系统

- 完整的车辆物理模拟
- 悬挂系统
- 轮胎力学
- 传动系统
- 多车型支持

### 地形系统

- 程序化地形生成
- 高度图输出
- 轨道走廊刷平
- 多材质混合

## 🎮 控制方式

| 按键 | 功能 |
|-----|------|
| W / ↑ | 油门 |
| S / ↓ | 刹车 |
| A / ← | 左转 |
| D / → | 右转 |
| Space | 手刹 |
| ESC | 退出 |
| C | 切换相机模式 |

## 🛠️ 工具使用

### 地形生成（命令行）

```bash
# 基本地形
python scripts/generate_terrain.py \
  --width 1024 \
  --height 1024 \
  --name race_base_flat

# 带赛道走廊
python scripts/generate_terrain.py \
  --name race_track_flat \
  --track-csv scripts/track_example.csv \
  --corridor-width-px 120 \
  --edge-falloff-px 50 \
  --track-flatten-strength 0.95
```

### 地形生成（命令行）

控制台不再提供“地形生成”页面；请使用命令行脚本生成地形。

## 📁 项目结构

```
vehiclegame/
├── 📄 console.py              # 游戏控制台入口
├── 📄 main.py                 # 游戏主入口
│
├── 📁 console_modules/        # 控制台模块
│   ├── game_launcher.py       # 🚀 游戏启动（多车辆支持）
│   ├── vehicle_editor.py      # 🚗 车辆配置编辑
│   └── map_generator.py       # 🗺️ 地图生成（配置选择/新建/自动保存）
│
├── 📁 core/                   # 核心组件
│   ├── config_manager.py      # 配置管理
│   ├── map_config_manager.py  # 地图配置管理（configs/maps）
│   └── process_manager.py     # 进程管理
│
├── 📁 configs/                # 配置文件
│   ├── vehicles/
│   │   ├── sports_car.json    # 跑车 (1500kg)
│   │   ├── truck.json         # 卡车 (3500kg)
│   │   └── offroad.json       # 越野车 (2200kg)
│   ├── maps/                  # 地图配置（自动保存）
│   ├── tracks/                # 赛道运行时配置（生成输出）
│   └── scenery/               # 场景元素配置（生成输出）
│
├── 📁 src/                    # 游戏业务代码
│   ├── business/
│   ├── systems/
│   └── world/
│
├── 📁 scripts/                # 工具脚本
│   └── generate_terrain.py
│
└── 📁 res/                    # 资源文件
    └── terrain/
```

详细结构见：[`docs/console/PROJECT_STRUCTURE.md`](docs/console/PROJECT_STRUCTURE.md)

## 🚗 车辆配置

### 预设车辆

| 车型 | 质量 | 最高速度 | 加速 | 特性 |
|-----|------|---------|------|------|
| **Sports Car** | 1500kg | 200km/h | 80 | 操控性好，加速快 |
| **Truck** | 3500kg | 120km/h | 30 | 质量大，加速慢，稳定 |
| **Off-Road** | 2200kg | 160km/h | 50 | 越野性能好，通过性强 |

### 自定义车辆

1. 复制配置：
```bash
cp configs/vehicles/sports_car.json configs/vehicles/my_car.json
```

2. 编辑参数：
```json
{
  "name": "My Car",
  "vehicle_mass": 1800.0,
  "physics": {
    "max_speed": 180.0,
    "acceleration": 70.0
  }
}
```

3. 在控制台中选择启动

## 📦 依赖

### 核心依赖
```txt
panda3d          # 游戏引擎
numpy            # 数值计算
scipy            # 科学计算
opensimplex      # 噪声生成
noise            # 噪声生成
```

### 控制台依赖（可选）
```txt
PySide6          # GUI 框架
```

### 安装
```bash
# 完整安装
pip install -r requirements.txt

# 仅游戏
pip install panda3d numpy scipy opensimplex noise

# 仅控制台
pip install PySide6
```

## ✅ 测试

### 组件测试
```bash
python tests/test_console.py
```

### 游戏测试
```bash
python examples/test_complete.py
```

## 📖 文档

| 文档 | 说明 |
|-----|------|
| [`docs/console/CONSOLE.md`](docs/console/CONSOLE.md) | 控制台使用指南 |
| [`docs/console/PROJECT_STRUCTURE.md`](docs/console/PROJECT_STRUCTURE.md) | 项目结构详解 |
| [`docs/`](docs/) | 技术文档目录 |

## 🔧 开发

### 添加新模块

1. 创建 `console_modules/my_module.py`
2. 继承 `ConsoleModule` 基类
3. 在 `console.py` 的 `_register_modules()` 中导入并注册

详见：[`docs/console/CONSOLE.md`](docs/console/CONSOLE.md#扩展开发)

### 代码风格

- 遵循 PEP 8
- 类型注解
- 文档字符串

## ⚠️ 故障排除

### PySide6 未安装/启动失败
```bash
pip install --upgrade PySide6
```

### 游戏无法启动
```bash
# 检查 Panda3D
python -c "import panda3d"

# 查看日志
cat logs/game.log
```

### 地形生成失败
```bash
# 检查 scipy
python -c "import scipy"

# 检查输出目录
ls -la res/terrain/
```

## 📝 更新日志

### v0.1.0 (2025-02-25)
- ✨ 新增游戏控制台
- 🚀 支持多车辆配置（3 种预设）
- 🛠️ 可视化地形生成工具
- ⚙️ 配置管理系统
- 📊 统一界面操作

## 📄 许可证

MIT License
