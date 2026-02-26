"""
生成器模块 - 各地形/颜色/赛道/场景生成器实现
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 添加到路径以便导入脚本
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.map_generator_orchestrator import GenerationStep


class TerrainGenerationStep(GenerationStep):
    """基础地形生成步骤"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("1_terrain", depends_on=None)
        self.config = config
    
    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """执行地形生成"""
        try:
            # 提取配置参数
            width = self.config.get('width', 1024)
            height = self.config.get('height', 1024)
            seed = self.config.get('seed', 42)
            generator = self.config.get('generator', 'opensimplex')
            output_name = self.config.get('output', 'race_base')
            
            noise_config = self.config.get('noise', {})
            sculpt_config = self.config.get('sculpt', {})
            
            # 构建命令行参数
            cmd_args = [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "generate_terrain.py"),
                "--width", str(width),
                "--height", str(height),
                "--seed", str(seed),
                "--generator", generator,
                "--out-dir", str(PROJECT_ROOT / "res" / "terrain"),
                "--name", output_name,
                "--base-frequency", str(noise_config.get('base_frequency', 0.003)),
                "--octaves", str(noise_config.get('octaves', 5)),
                "--persistence", str(noise_config.get('persistence', 0.5)),
                "--lacunarity", str(noise_config.get('lacunarity', 2.0)),
                "--smooth-sigma", str(sculpt_config.get('smooth_sigma', 2.5)),
                "--relief-strength", str(sculpt_config.get('relief_strength', 0.25)),
            ]
            
            self._log("执行地形生成脚本...", "info")
            self.progress = 0.2
            
            # 执行脚本
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(PROJECT_ROOT)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                return False, f"地形生成失败：{error_msg}"
            
            self.progress = 0.8
            
            # 验证生成的文件
            output_dir = PROJECT_ROOT / "res" / "terrain"
            expected_files = [
                output_dir / f"{output_name}.npy",
                output_dir / f"{output_name}.pgm",
                output_dir / f"{output_name}.json"
            ]
            
            generated = []
            for f in expected_files:
                if f.exists():
                    generated.append(str(f.relative_to(PROJECT_ROOT)))
            
            if not generated:
                return False, "未生成任何文件"
            
            self.generated_files = generated
            self.progress = 1.0
            
            # 保存到上下文供后续步骤使用
            context['terrain_output'] = output_name
            context['terrain_config'] = {
                'width': width,
                'height': height,
                'seed': seed,
                **noise_config,
                **sculpt_config
            }
            
            return True, f"生成 {len(generated)} 个文件：{', '.join(generated)}"
            
        except Exception as e:
            return False, f"地形生成异常：{str(e)}"
    
    def _log(self, message: str, level: str = "info"):
        """日志辅助方法"""
        print(f"[TERRAIN] [{level.upper()}] {message}")


class ColorGenerationStep(GenerationStep):
    """地图颜色配置生成步骤"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("2_colors", depends_on="1_terrain")
        self.config = config
    
    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """生成颜色配置文件"""
        try:
            terrain_output = context.get('terrain_output')
            if not terrain_output:
                return False, "依赖地形未生成"
            
            mode = self.config.get('mode', 'procedural')
            
            # 构建颜色配置
            color_config = {
                'version': '1.0',
                'terrain_base': terrain_output,
                'mode': mode,
                'generated_at': asyncio.get_event_loop().time()
            }
            
            if mode == 'procedural':
                procedural = self.config.get('procedural', {})
                color_config['procedural'] = {
                    'grass_color': procedural.get('grass_color', [0.08, 0.38, 0.08]),
                    'dirt_color': procedural.get('dirt_color', [0.58, 0.42, 0.25]),
                    'rock_color': procedural.get('rock_color', [0.68, 0.62, 0.55]),
                    'height_rock_threshold': procedural.get('height_rock_threshold', 0.4),
                    'slope_rock_threshold': procedural.get('slope_rock_threshold', 0.3)
                }
            elif mode == 'texture_blend':
                texture = self.config.get('texture_blend', {})
                color_config['texture_blend'] = texture
            
            # 保存配置文件
            output_dir = PROJECT_ROOT / "res" / "terrain"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = output_dir / f"{terrain_output}_colors.json"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(color_config, f, indent=2, ensure_ascii=False)
            
            self.generated_files = [str(output_path.relative_to(PROJECT_ROOT))]
            self.progress = 1.0
            
            context['color_config'] = color_config
            
            return True, f"颜色配置已保存：{output_path.name}"
            
        except Exception as e:
            return False, f"颜色生成异常：{str(e)}"
    
    def _log(self, message: str, level: str = "info"):
        print(f"[COLOR] [{level.upper()}] {message}")


class TrackGenerationStep(GenerationStep):
    """赛道数据生成步骤"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("3_track", depends_on="1_terrain")
        self.config = config
    
    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """生成赛道配置"""
        try:
            terrain_output = context.get('terrain_output')
            if not terrain_output:
                return False, "依赖地形未生成"
            
            # 验证 CSV 文件存在
            csv_path_str = self.config.get('csv_path', 'configs/tracks/default_track.csv')
            csv_path = PROJECT_ROOT / csv_path_str
            
            if not csv_path.exists():
                # 尝试创建示例赛道
                return await self._create_default_track(csv_path)
            
            # 加载 CSV 验证格式
            points = self._load_csv_points(csv_path)
            if len(points) < 2:
                return False, "赛道 CSV 至少需要 2 个点"
            
            # 构建赛道配置
            track_config = {
                'version': '1.0',
                'terrain_base': terrain_output,
                'source': 'csv',
                'csv_path': csv_path_str,
                'coord_space': self.config.get('coord_space', 'normalized'),
                'geometry': self.config.get('geometry', {
                    'track_width': 9.0,
                    'border_width': 0.8,
                    'samples_per_segment': 8,
                    'elevation_offset': 0.05
                }),
                'visuals': self.config.get('visuals', {
                    'track_color': [0.18, 0.18, 0.20, 1.0],
                    'border_color': [0.85, 0.14, 0.14, 1.0],
                    'centerline_color': [0.95, 0.95, 0.95, 1.0],
                    'show_centerline': True
                }),
                'point_count': len(points),
                'generated_at': asyncio.get_event_loop().time()
            }
            
            # 保存配置
            output_dir = PROJECT_ROOT / "configs" / "tracks"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_name = csv_path.stem + "_runtime.json"
            output_path = output_dir / output_name
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(track_config, f, indent=2, ensure_ascii=False)
            
            self.generated_files = [
                str(output_path.relative_to(PROJECT_ROOT)),
                csv_path_str
            ]
            self.progress = 1.0
            
            context['track_config'] = track_config
            
            return True, f"赛道配置已保存：{output_name} ({len(points)} 个点)"
            
        except Exception as e:
            return False, f"赛道生成异常：{str(e)}"
    
    def _load_csv_points(self, path: Path) -> List[Tuple[float, float]]:
        """加载 CSV 赛道点"""
        import csv
        points = []
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or row[0].strip().startswith('#'):
                    continue
                if len(row) >= 2:
                    try:
                        x = float(row[0])
                        y = float(row[1])
                        points.append((x, y))
                    except ValueError:
                        continue
        
        return points
    
    async def _create_default_track(self, path: Path) -> Tuple[bool, str]:
        """创建默认椭圆形赛道"""
        import math
        import csv
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成椭圆形赛道点
        points = []
        num_points = 50
        a = 0.4  # 长半轴
        b = 0.3  # 短半轴
        
        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi
            x = 0.5 + a * math.cos(angle)
            y = 0.5 + b * math.sin(angle)
            points.append((x, y))
        
        # 写入 CSV
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['# Default oval track'])
            writer.writerow(['# x, y (normalized coordinates)'])
            for x, y in points:
                writer.writerow([f"{x:.6f}", f"{y:.6f}"])
        
        self._log(f"创建默认赛道：{path}", "info")
        return await self.execute({'csv_path': str(path.relative_to(PROJECT_ROOT))})
    
    def _log(self, message: str, level: str = "info"):
        print(f"[TRACK] [{level.upper()}] {message}")


class SceneryGenerationStep(GenerationStep):
    """场景元素生成步骤"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("4_scenery", depends_on="1_terrain")
        self.config = config
    
    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """生成场景元素配置"""
        try:
            terrain_output = context.get('terrain_output')
            if not terrain_output:
                return False, "依赖地形未生成"
            
            scenery_config = {
                'version': '1.0',
                'terrain_base': terrain_output,
                'generated_at': asyncio.get_event_loop().time()
            }
            
            # 树木配置
            trees_config = self.config.get('trees', {})
            if trees_config.get('enabled', True):
                scenery_config['trees'] = {
                    'enabled': True,
                    'count': trees_config.get('count', 30),
                    'min_radius': trees_config.get('min_radius', 40),
                    'max_radius': trees_config.get('max_radius', 95),
                    'exclude_center': trees_config.get('exclude_center', {
                        'width': 18,
                        'length': 100
                    }),
                    'model': 'tree_pine',
                    'scale_range': [0.8, 1.5]
                }
            
            # 岩石配置
            rocks_config = self.config.get('rocks', {})
            if rocks_config.get('enabled', True):
                scenery_config['rocks'] = {
                    'enabled': True,
                    'count': rocks_config.get('count', 40),
                    'min_radius': rocks_config.get('min_radius', 30),
                    'max_radius': rocks_config.get('max_radius', 90),
                    'size_range': rocks_config.get('size_range', [1.5, 4.0]),
                    'model': 'rock_boulder'
                }
            
            # 自定义道具配置
            props_config = self.config.get('props', {})
            scenery_config['props'] = {
                'enabled': props_config.get('enabled', False),
                'custom_models': props_config.get('custom_models', [])
            }
            
            # 保存配置
            output_dir = PROJECT_ROOT / "configs" / "scenery"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_name = f"{terrain_output}_scenery.json"
            output_path = output_dir / output_name
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(scenery_config, f, indent=2, ensure_ascii=False)
            
            self.generated_files = [str(output_path.relative_to(PROJECT_ROOT))]
            self.progress = 1.0
            
            context['scenery_config'] = scenery_config
            
            return True, f"场景配置已保存：{output_name}"
            
        except Exception as e:
            return False, f"场景生成异常：{str(e)}"
    
    def _log(self, message: str, level: str = "info"):
        print(f"[SCENERY] [{level.upper()}] {message}")


def create_all_steps(map_config: Dict[str, Any]) -> List[GenerationStep]:
    """根据地图配置创建所有生成步骤"""
    steps = []
    
    # 1. 地形
    terrain_data = map_config.get('1_terrain', {})
    if terrain_data.get('enabled', True):
        steps.append(TerrainGenerationStep(terrain_data.get('data', {})))
    
    # 2. 颜色
    colors_data = map_config.get('2_colors', {})
    if colors_data.get('enabled', True):
        steps.append(ColorGenerationStep(colors_data.get('data', {})))
    
    # 3. 赛道
    track_data = map_config.get('3_track', {})
    if track_data.get('enabled', True):
        steps.append(TrackGenerationStep(track_data.get('data', {})))
    
    # 4. 场景
    scenery_data = map_config.get('4_scenery', {})
    if scenery_data.get('enabled', True):
        steps.append(SceneryGenerationStep(scenery_data.get('data', {})))
    
    return steps
