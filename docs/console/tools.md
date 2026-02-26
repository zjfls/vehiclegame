# 工具接口与调用方法

## 1. 运行入口

| 场景 | 接口/文件 | 调用方法 |
|---|---|---|
| 启动游戏 | `main.py` | `python main.py` |
| 车辆系统测试 | `examples/test_vehicle.py` | `python examples/test_vehicle.py` |
| 完整链路测试 | `examples/test_complete.py` | `python examples/test_complete.py` |

## 2. 地形生成工具

### 2.1 接口

- 脚本：`scripts/generate_terrain.py`
- 输入：命令行参数（尺寸、噪声参数、赛道 CSV、输出路径）
- 输出：`res/terrain/*.pgm`、`res/terrain/*.npy`、`res/terrain/*.json`

### 2.2 基础调用

```bash
python scripts/generate_terrain.py \
  --width 1024 \
  --height 1024 \
  --name race_base_flat
```

### 2.3 赛道刷平调用

```bash
python scripts/generate_terrain.py \
  --name race_track_flat \
  --track-csv scripts/track_example.csv \
  --track-coord-space normalized \
  --corridor-width-px 120 \
  --edge-falloff-px 50 \
  --track-flatten-strength 0.95
```

### 2.4 常用参数

- 基础：`--width` `--height` `--seed` `--name` `--out-dir`
- 噪声：`--generator` `--octaves` `--base-frequency` `--persistence` `--lacunarity`
- 地形：`--smooth-sigma` `--relief-strength`
- 赛道：`--track-csv` `--track-coord-space` `--corridor-width-px` `--edge-falloff-px` `--track-flatten-strength`

## 3. 依赖安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

依赖：`panda3d`、`numpy`、`scipy`、`opensimplex`、`noise`

## 4. 常见问题

- 报 `ModuleNotFoundError`：先确认已激活 `.venv`。
- 地形生成报 `opensimplex/scipy/noise` 缺失：重新执行依赖安装命令。
