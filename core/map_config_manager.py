"""
地图配置管理器 - 管理地图模块配置（地形/颜色/赛道/场景）
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


@dataclass
class MapModuleConfig:
    """单个模块的配置"""
    name: str
    enabled: bool
    depends_on: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    generated_files: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, ready, completed, error


@dataclass
class MapConfig:
    """完整地图配置"""
    name: str
    version: str = "1.0"
    description: str = ""
    modules: Dict[str, MapModuleConfig] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MapConfigManager:
    """地图配置管理器"""
    
    def __init__(self, maps_dir: str = "configs/maps"):
        self.maps_dir = Path(maps_dir)
        self.maps_dir.mkdir(parents=True, exist_ok=True)
        
        # 确保子目录存在
        (self.maps_dir.parent / "tracks").mkdir(exist_ok=True)
        (self.maps_dir.parent / "scenery").mkdir(exist_ok=True)
    
    def create_default_config(self, name: str) -> MapConfig:
        """创建默认地图配置"""
        config = MapConfig(
            name=name,
            version="1.0",
            description=f"地图配置：{name}"
        )
        
        # 1. 基础地形模块
        config.modules["1_terrain"] = MapModuleConfig(
            name="1_terrain",
            enabled=True,
            depends_on=None,
            data={
                "width": 1024,
                "height": 1024,
                "seed": 42,
                "generator": "opensimplex",
                "noise": {
                    "base_frequency": 0.003,
                    "octaves": 5,
                    "persistence": 0.5,
                    "lacunarity": 2.0
                },
                "sculpt": {
                    "smooth_sigma": 2.5,
                    "relief_strength": 0.25
                },
                "output": "race_base"
            },
            status="pending"
        )
        
        # 2. 地图颜色模块
        config.modules["2_colors"] = MapModuleConfig(
            name="2_colors",
            enabled=True,
            depends_on="1_terrain",
            data={
                "mode": "procedural",
                "procedural": {
                    "grass_color": [0.08, 0.38, 0.08],
                    "dirt_color": [0.58, 0.42, 0.25],
                    "rock_color": [0.68, 0.62, 0.55],
                    "height_rock_threshold": 0.4,
                    "slope_rock_threshold": 0.3
                }
            },
            status="pending"
        )
        
        # 3. 赛道数据模块
        config.modules["3_track"] = MapModuleConfig(
            name="3_track",
            enabled=True,
            depends_on="1_terrain",
            data={
                "source": "csv",
                "csv_path": "configs/tracks/default_track.csv",
                "coord_space": "normalized",
                "geometry": {
                    "track_width": 9.0,
                    "border_width": 0.8,
                    "samples_per_segment": 8,
                    "elevation_offset": 0.05
                },
                "visuals": {
                    "track_color": [0.18, 0.18, 0.20, 1.0],
                    "border_color": [0.85, 0.14, 0.14, 1.0],
                    "centerline_color": [0.95, 0.95, 0.95, 1.0],
                    "show_centerline": True
                }
            },
            status="pending"
        )
        
        # 4. 场景元素模块
        config.modules["4_scenery"] = MapModuleConfig(
            name="4_scenery",
            enabled=True,
            depends_on="1_terrain",
            data={
                "trees": {
                    "enabled": True,
                    "count": 30,
                    "min_radius": 40,
                    "max_radius": 95,
                    "exclude_center": {"width": 18, "length": 100}
                },
                "rocks": {
                    "enabled": True,
                    "count": 40,
                    "min_radius": 30,
                    "max_radius": 90,
                    "size_range": [1.5, 4.0]
                },
                "props": {
                    "enabled": False,
                    "custom_models": []
                }
            },
            status="pending"
        )
        
        return config
    
    def load_config(self, name: str) -> MapConfig:
        """加载地图配置"""
        path = self.maps_dir / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Map config not found: {name}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = MapConfig(
            name=data.get('name', name),
            version=data.get('version', '1.0'),
            description=data.get('description', '')
        )
        
        # 解析模块配置
        for key in ['1_terrain', '2_colors', '3_track', '4_scenery']:
            if key in data:
                module_data = data[key]
                module = MapModuleConfig(
                    name=key,
                    enabled=module_data.get('enabled', True),
                    depends_on=module_data.get('depends_on'),
                    data={k: v for k, v in module_data.items() 
                          if k not in ('enabled', 'depends_on', 'generated_files', 'status')},
                    generated_files=module_data.get('generated_files', []),
                    status=module_data.get('status', 'pending')
                )
                config.modules[key] = module
        
        config.metadata = data.get('metadata', {})
        return config
    
    def save_config(self, config: MapConfig) -> str:
        """保存地图配置"""
        data = {
            'name': config.name,
            'version': config.version,
            'description': config.description,
            'metadata': config.metadata
        }
        
        for module_name, module in config.modules.items():
            module_data = {
                'enabled': module.enabled,
                'depends_on': module.depends_on,
                'status': module.status,
                'generated_files': module.generated_files,
                **module.data
            }
            data[module_name] = module_data
        
        safe_name = config.name.replace(' ', '_').lower()
        path = self.maps_dir / f"{safe_name}.json"
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(path)
    
    def check_dependencies(self, config: MapConfig, module_name: str) -> bool:
        """检查模块依赖是否满足"""
        module = config.modules.get(module_name)
        if not module or not module.depends_on:
            return True
        
        dep_module = config.modules.get(module.depends_on)
        if not dep_module:
            return False
        
        # 依赖模块必须已完成
        return dep_module.status == "completed"
    
    def get_module_files(self, module_name: str) -> List[str]:
        """获取模块已生成的文件列表"""
        # 检查 configs/maps 中所有配置
        all_files = []
        for config_path in self.maps_dir.glob("*.json"):
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if module_name in data:
                    files = data[module_name].get('generated_files', [])
                    all_files.extend(files)
        return all_files
    
    def list_configs(self) -> List[str]:
        """列出所有地图配置"""
        return [f.stem for f in self.maps_dir.glob("*.json")]
    
    def delete_config(self, name: str) -> bool:
        """删除地图配置（不删除生成的文件）"""
        path = self.maps_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            return True
        return False
    
    def update_module_status(self, config: MapConfig, module_name: str, 
                            status: str, files: Optional[List[str]] = None) -> None:
        """更新模块状态"""
        module = config.modules.get(module_name)
        if module:
            module.status = status
            if files:
                module.generated_files = files
    
    def get_dependency_chain(self, module_name: str) -> List[str]:
        """获取模块的依赖链（从根到当前）"""
        chain = []
        current = module_name
        
        # 简单实现：硬编码依赖关系
        deps = {
            "1_terrain": None,
            "2_colors": "1_terrain",
            "3_track": "1_terrain",
            "4_scenery": "1_terrain"
        }
        
        while current:
            chain.insert(0, current)
            current = deps.get(current)
        
        return chain
