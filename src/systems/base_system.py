"""
系统基类
所有系统都实现这个接口
"""
from abc import ABC, abstractmethod

from .update_context import SystemUpdateContext

class ISystem(ABC):
    """
    系统接口
    
    所有系统都应该实现这个接口
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """初始化系统"""
        pass
    
    @abstractmethod
    def update(self, ctx: SystemUpdateContext) -> None:
        """每帧更新"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """关闭系统"""
        pass

class SystemBase(ISystem):
    """
    系统基类
    
    提供默认实现，子类可以覆盖需要的方法
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._initialized = False
    
    def initialize(self) -> None:
        """初始化系统"""
        self._initialized = True
    
    def shutdown(self) -> None:
        """关闭系统"""
        self._initialized = False
    
    def is_initialized(self) -> bool:
        """是否已初始化"""
        return self._initialized
