# Procedural Terrain Texture System

## 概述

使用 **OpenSimplex 噪声** 生成 procedual 地形纹理，无需外部纹理文件。

## 特性

- ✅ **零资源依赖**：无需下载/管理纹理文件
- ✅ **无缝拼接**：天然无缝，无平铺痕迹
- ✅ **实时可调**：参数化控制颜色、噪声频率、混合阈值
- ✅ **性能优秀**：顶点颜色混合，无纹理采样开销
- ✅ **版权安全**：无版权风险

## 使用方法

### 基础用法

```python
from src.world.terrain_runtime import RuntimeTerrain, TerrainConfig

# 使用默认配置（procedural 已启用）
config = TerrainConfig()
terrain = RuntimeTerrain(loader, config)
terrain_mesh = terrain.build(render)
```

### 自定义配置

```python
config = TerrainConfig(
    # 启用 procedural 纹理
    use_procedural_texture=True,
    
    # 基础颜色 (RGB, 0-1)
    grass_color=(0.2, 0.4, 0.15),   # 更绿的草地
    dirt_color=(0.5, 0.35, 0.25),   # 更红的泥土
    rock_color=(0.6, 0.58, 0.55),   # 更浅的岩石
    
    # 噪声参数
    noise_scale=0.08,      # 更大的噪声图案 (默认 0.05)
    noise_octaves=5,       # 更多细节层 (默认 4)
    
    # 混合阈值
    height_rock_threshold=0.7,  # 更高才出现岩石 (默认 0.65)
    slope_rock_threshold=0.6,   # 更陡才出现岩石 (默认 0.5)
)

terrain = RuntimeTerrain(loader, config)
```

### 切换回传统纹理模式

```python
config = TerrainConfig(
    use_procedural_texture=False,  # 禁用 procedural
    texture_path="res/tex/my_terrain.png",  # 使用外部纹理
    uv_tiling=3.0,  # 纹理平铺次数
)
```

## 参数配置表

### 颜色参数

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `grass_color` | tuple | (0.18, 0.35, 0.16) | 草地 RGB 颜色 |
| `dirt_color` | tuple | (0.45, 0.36, 0.24) | 泥土 RGB 颜色 |
| `rock_color` | tuple | (0.56, 0.56, 0.54) | 岩石 RGB 颜色 |

### 噪声参数

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `noise_scale` | float | 0.05 | 噪声频率 (越大图案越小) |
| `noise_octaves` | int | 4 | 噪声层数 (越多细节越丰富) |

### 混合阈值

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `height_rock_threshold` | float | 0.65 | 高度超过此值混合岩石 |
| `slope_rock_threshold` | float | 0.5 | 坡度超过此值混合岩石 |

## 测试

```bash
python3 test_procedural_terrain.py
```

## 工作原理

1. **FBM 噪声**：4 层 OpenSimplex 噪声叠加，产生自然变化
2. **三元混合**：根据高度、坡度、噪声值混合草地/泥土/岩石
3. **顶点颜色**：在 mesh 构建时计算，运行时无开销
