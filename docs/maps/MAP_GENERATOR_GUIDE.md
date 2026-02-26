# 🗺️ 地图生成器使用指南

## 概述

地图生成器提供了一个完整的地图配置和生成系统，支持：
- **基础地形**：程序化生成高度图
- **地图颜色**：程序化颜色或纹理混合
- **赛道数据**：从 CSV 导入或自动生成
- **场景元素**：树木、岩石等装饰物

## 快速开始

### 1. 启动控制台

```bash
python console.py
```

### 2. 切换到"地图生成"模块

点击左侧导航栏的 **🗺️ 地图生成**

### 3. 创建或加载配置

- **新建配置**：点击 `➕ 新建`，输入配置名称
- **加载配置**：从下拉列表选择已有配置
- **保存配置**：修改参数后点击 `💾 保存`

### 4. 生成地图元素

#### 方式一：分步生成

1. **基础地形** → 点击 `⚙️ 生成`
   - 等待生成完成（状态变为 ✅ 已完成）
   - 可点击 `👁️ 预览` 查看效果

2. **地图颜色** → 点击 `⚙️ 生成`
   - 依赖基础地形，必须先生成地形
   - 生成颜色配置文件

3. **赛道数据** → 点击 `⚙️ 生成`
   - 依赖基础地形
   - 可指定 CSV 文件或使用默认椭圆赛道

4. **场景元素** → 点击 `⚙️ 生成`
   - 依赖基础地形
   - 生成树木、岩石等配置

#### 方式二：一键生成

点击 `▶️ 一键生成所有` 按钮
- 自动按依赖顺序执行（地形 → 颜色 → 赛道 → 场景）
- 如果某步已存在，会提示：跳过/覆盖/停止
- 可随时点击 `⏹️ 停止` 中断生成

## 配置说明

### 1. 基础地形参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 宽度 | 高度图宽度（像素） | 1024 |
| 高度 | 高度图高度（像素） | 1024 |
| 种子 | 随机种子（相同种子生成相同地形） | 42 |
| 输出名称 | 输出文件前缀 | race_base |
| 基础频率 | 噪声基础频率（越大细节越密） | 0.003 |
| Octaves | 噪声层数（更高更细节） | 5 |

**生成文件：**
- `res/terrain/{output}.npy` - 高度图数据（NumPy 格式）
- `res/terrain/{output}.pgm` - 高度图图像（可视化的灰度图）
- `res/terrain/{output}.json` - 地形元数据

### 2. 地图颜色参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 模式 | 程序化生成 / 纹理混合 | 程序化 |
| 草地颜色 | 低海拔平地的颜色 | 深绿色 |
| 泥土颜色 | 中等高度的颜色 | 棕色 |
| 岩石颜色 | 高海拔或陡坡的颜色 | 灰色 |
| 高度阈值 | 超过此高度显示岩石 | 0.4 (40%) |
| 坡度阈值 | 超过此坡度显示岩石 | 0.3 (30%) |

**生成文件：**
- `res/terrain/{terrain_base}_colors.json` - 颜色配置

### 3. 赛道数据参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| CSV 路径 | 赛道点文件路径 | configs/tracks/default_track.csv |
| 赛道宽度 | 赛道宽度（世界单位） | 9.0 |
| 边线宽度 | 赛道边线宽度 | 0.8 |
| 采样密度 | 每段采样点数 | 8 |
| 高程偏移 | 赛道相对地形的高度 | 0.05 |

**CSV 格式：**
```csv
# 注释行以 # 开头
x, y
0.5, 0.2
0.6, 0.25
...
```

坐标系统：
- `normalized`：归一化坐标 (0.0-1.0)
- `world`：世界坐标（米）
- `pixel`：像素坐标

**生成文件：**
- `configs/tracks/{track_name}_runtime.json` - 赛道运行时配置

### 4. 场景元素参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| 树木数量 | 生成的树木数量 | 30 |
| 分布半径 | 最小/最大分布半径 | 40-95 |
| 排除区域 | 中心排除区域（宽 x 长） | 18x100 |
| 岩石数量 | 生成的岩石数量 | 40 |
| 岩石大小 | 岩石尺寸范围 | 1.5-4.0 |

**生成文件：**
- `configs/scenery/{terrain_base}_scenery.json` - 场景配置

## 依赖关系

```
基础地形 (1_terrain)
    ├── 地图颜色 (2_colors)
    ├── 赛道数据 (3_track)
    └── 场景元素 (4_scenery)
```

- **2/3/4 模块依赖 1**：必须先生成基础地形
- 如果依赖未满足，生成按钮会显示提示

## 配置文件管理

### 保存配置

1. 调整各模块参数
2. 点击 `💾 保存`
3. 配置保存到 `configs/maps/{name}.json`

### 加载配置

1. 从下拉列表选择配置
2. 或点击 `📂 加载`
3. UI 自动填充之前的参数

### 配置示例

```json
{
  "name": "Race Track Alpha",
  "version": "1.0",
  "1_terrain": {
    "enabled": true,
    "width": 1024,
    "height": 1024,
    "seed": 42,
    "output": "race_alpha",
    "noise": {
      "base_frequency": 0.003,
      "octaves": 5
    }
  },
  "2_colors": {
    "enabled": true,
    "depends_on": "1_terrain",
    "mode": "procedural"
  },
  "3_track": {
    "enabled": true,
    "depends_on": "1_terrain",
    "csv_path": "configs/tracks/alpha_track.csv"
  },
  "4_scenery": {
    "enabled": true,
    "depends_on": "1_terrain",
    "trees": {"count": 30},
    "rocks": {"count": 40}
  }
}
```

## 故障排除

### 问题：依赖未满足

**原因**：尝试生成 2/3/4 模块时，基础地形未生成

**解决**：先生成基础地形模块

### 问题：赛道 CSV 文件不存在

**原因**：指定的 CSV 路径无效

**解决**：
1. 点击 `浏览...` 选择正确的 CSV 文件
2. 或使用默认赛道（系统会自动创建）

### 问题：生成失败

**检查**：
1. 查看日志区域的错误信息
2. 确认 `res/terrain` 目录可写
3. 检查是否有足够的磁盘空间

### 问题：覆盖确认

**场景**：模块已生成，再次生成时会提示

**选项**：
- **跳过**：保留现有文件，继续下一个
- **覆盖**：重新生成并覆盖文件
- **停止**：中断整个生成流程

## 高级用法

### 自定义赛道设计

1. 使用文本编辑器创建 CSV 文件：
```csv
# My custom track
0.5, 0.1
0.7, 0.2
0.9, 0.4
0.8, 0.6
0.5, 0.8
0.2, 0.6
0.1, 0.4
0.3, 0.2
0.5, 0.1
```

2. 保存到 `configs/tracks/my_track.csv`
3. 在赛道模块中选择该文件
4. 生成赛道配置

### 批量生成多个地图

创建多个配置文件，然后使用脚本批量生成：

```python
from core.map_config_manager import MapConfigManager
from core.map_generator_orchestrator import MapGeneratorOrchestrator

manager = MapConfigManager()
orchestrator = MapGeneratorOrchestrator()

for config_name in ["map1", "map2", "map3"]:
    config = manager.load_config(config_name)
    # ... 配置生成器并执行
```

### 集成到游戏加载

游戏启动时加载地图配置：

```python
from core.map_config_manager import MapConfigManager

manager = MapConfigManager()
config = manager.load_config("Race Track Alpha")

# 读取地形
terrain_output = config.modules["1_terrain"].data["output"]
heightmap_path = f"res/terrain/{terrain_output}.npy"

# 读取赛道
track_config_path = config.modules["3_track"].generated_files[0]
```

## 文件结构

```
vehiclegame/
├── configs/
│   ├── maps/                    # 地图配置文件
│   │   ├── default_map.json
│   │   └── race_alpha.json
│   ├── tracks/                  # 赛道 CSV 和配置
│   │   ├── default_track.csv
│   │   └── default_track_runtime.json
│   └── scenery/                 # 场景配置
│       └── race_base_scenery.json
│
├── res/
│   └── terrain/                 # 生成的地形文件
│       ├── race_base.npy
│       ├── race_base.pgm
│       ├── race_base.json
│       └── race_base_colors.json
│
├── core/
│   ├── map_config_manager.py    # 配置管理
│   └── map_generator_orchestrator.py  # 生成编排
│
├── generators/
│   └── __init__.py              # 生成器实现
│
└── console_modules/
    └── map_generator.py         # UI 模块
```

## 技术支持

如有问题，请查看：
1. 控制台日志区域
2. `logs/console.log` 文件
3. 游戏主日志 `logs/game.log`
