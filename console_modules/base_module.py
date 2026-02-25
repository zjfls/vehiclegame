"""
控制台模块基类
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class ConsoleModule(ABC):
    """控制台模块基类"""
    
    def __init__(self, console_app: Any):
        """
        初始化模块
        
        Args:
            console_app: 控制台应用实例
        """
        self.console_app = console_app
        self.initialized = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """模块名称（显示在菜单中）"""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """显示名称"""
        pass
    
    @property
    def icon(self) -> str:
        """模块图标（emoji）"""
        return "📦"
    
    @property
    def description(self) -> str:
        """模块描述"""
        return ""
    
    @abstractmethod
    def build_ui(self, parent: Any) -> None:
        """
        构建 UI
        
        Args:
            parent: 父容器（DearPyGui 的 group 或 window）
        """
        pass
    
    def on_show(self) -> None:
        """模块显示时调用"""
        pass
    
    def on_hide(self) -> None:
        """模块隐藏时调用"""
        pass
    
    def on_update(self, dt: float) -> None:
        """
        每帧更新
        
        Args:
            dt: 帧间隔时间（秒）
        """
        pass
    
    def cleanup(self) -> None:
        """清理资源"""
        pass
    
    def log(self, message: str, level: str = "info") -> None:
        """
        记录日志
        
        Args:
            message: 日志消息
            level: 日志级别 (info, warning, error, success)
        """
        if hasattr(self.console_app, 'log_message'):
            self.console_app.log_message(message, level)
    
    def get_config_manager(self):
        """获取配置管理器"""
        if hasattr(self.console_app, 'config_manager'):
            return self.console_app.config_manager
        return None
    
    def get_process_manager(self):
        """获取进程管理器"""
        if hasattr(self.console_app, 'process_manager'):
            return self.console_app.process_manager
        return None


class ModuleRegistry:
    """模块注册中心"""
    
    _modules: Dict[str, type] = {}
    
    @classmethod
    def register(cls, module_class: type) -> type:
        """注册模块（可作为装饰器）"""
        cls._modules[module_class.name] = module_class
        return module_class
    
    @classmethod
    def get_module(cls, name: str) -> type:
        """获取模块类"""
        if name not in cls._modules:
            raise ValueError(f"Module not found: {name}")
        return cls._modules[name]
    
    @classmethod
    def list_modules(cls) -> Dict[str, type]:
        """列出所有已注册模块"""
        return cls._modules.copy()
    
    @classmethod
    def create_module(cls, name: str, console_app: Any) -> ConsoleModule:
        """创建模块实例"""
        module_class = cls.get_module(name)
        return module_class(console_app)
