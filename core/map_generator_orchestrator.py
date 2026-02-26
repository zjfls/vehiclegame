"""
地图生成器编排器 - 管理生成步骤的依赖和执行顺序
"""
from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path
import asyncio
from abc import ABC, abstractmethod


class GenerationStep(ABC):
    """生成步骤基类"""
    
    def __init__(self, name: str, depends_on: Optional[str] = None):
        self.name = name
        self.depends_on = depends_on
        self.status = "pending"  # pending, ready, running, completed, error
        self.generated_files: List[str] = []
        self.error_message: Optional[str] = None
        self.progress = 0.0  # 0.0 - 1.0
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """执行生成步骤
        
        Returns:
            (success, message)
        """
        pass
    
    def can_execute(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """检查是否可以执行"""
        if self.status == "running":
            return False, "步骤正在执行中"
        
        if self.depends_on:
            dep_step = context.get('steps', {}).get(self.depends_on)
            if not dep_step or dep_step.status != "completed":
                return False, f"依赖 {self.depends_on} 未完成"
        
        return True, "OK"


class MapGeneratorOrchestrator:
    """地图生成器编排器"""
    
    def __init__(self):
        self.steps: Dict[str, GenerationStep] = {}
        self.context: Dict[str, Any] = {}
        self.log_callback: Optional[Callable[[str, str], None]] = None
        self.progress_callback: Optional[Callable[[str, float], None]] = None
    
    def add_step(self, step: GenerationStep):
        """添加生成步骤"""
        self.steps[step.name] = step
        self.context['steps'] = self.steps
    
    def remove_step(self, step_name: str) -> bool:
        """移除生成步骤"""
        if step_name in self.steps:
            del self.steps[step_name]
            return True
        return False
    
    def can_execute(self, step_name: str) -> Tuple[bool, str]:
        """检查步骤是否可以执行"""
        step = self.steps.get(step_name)
        if not step:
            return False, f"步骤不存在：{step_name}"
        
        return step.can_execute(self.context)
    
    def is_module_generated(self, step_name: str) -> bool:
        """检查模块是否已生成"""
        step = self.steps.get(step_name)
        return step and step.status == "completed" and len(step.generated_files) > 0
    
    def get_generated_files(self, step_name: str) -> List[str]:
        """获取模块生成的文件列表"""
        step = self.steps.get(step_name)
        return step.generated_files if step else []
    
    async def execute_step(self, step_name: str, force: bool = False) -> Tuple[bool, str]:
        """执行单个步骤
        
        Args:
            step_name: 步骤名称
            force: 是否强制重新生成（即使已完成）
        
        Returns:
            (success, message)
        """
        step = self.steps.get(step_name)
        if not step:
            return False, f"步骤不存在：{step_name}"
        
        # 如果已生成且未强制，需要用户确认（由 UI 层处理）
        if self.is_module_generated(step_name) and not force:
            return False, "MODULE_EXISTS"
        
        # 检查依赖
        can_exec, reason = step.can_execute(self.context)
        if not can_exec:
            self._log(f"⚠️ {step_name} 无法执行：{reason}", "warning")
            return False, reason
        
        step.status = "running"
        step.progress = 0.0
        self._log(f"▶️ 开始生成 {step_name}", "info")
        self._progress(step_name, 0.0)
        
        try:
            success, message = await step.execute(self.context)
            
            if success:
                step.status = "completed"
                step.progress = 1.0
                self._log(f"✅ {step_name} 生成完成：{message}", "success")
                self._progress(step_name, 1.0)
            else:
                step.status = "error"
                step.error_message = message
                self._log(f"❌ {step_name} 生成失败：{message}", "error")
            
            return success, message
            
        except Exception as e:
            step.status = "error"
            step.error_message = str(e)
            self._log(f"❌ {step_name} 异常：{e}", "error")
            import traceback
            traceback.print_exc()
            return False, str(e)
    
    async def generate_all(self) -> Tuple[bool, str]:
        """一键生成所有模块（按依赖顺序）
        
        Returns:
            (success, message)
        """
        # 拓扑排序确定执行顺序
        order = self._topological_sort()
        
        if not order:
            return False, "没有可执行的步骤"
        
        total = len(order)
        completed = 0
        
        for step_name in order:
            step = self.steps.get(step_name)
            if not step:
                continue
            
            # 如果已生成，确认是否跳过
            if self.is_module_generated(step_name):
                # 这里返回特殊标记，由 UI 层处理确认
                action = self._confirm_overwrite(step_name)
                if action == "skip":
                    completed += 1
                    self._log(f"⏭️ 跳过 {step_name}", "info")
                    continue
                elif action == "stop":
                    return False, f"用户在 {step_name} 处停止"
                # action == "overwrite" 继续执行
            
            success, message = await self.execute_step(step_name, force=True)
            if not success:
                return False, f"在 {step_name} 处失败：{message}"
            
            completed += 1
        
        return True, f"地图生成完成！共 {completed}/{total} 个模块"
    
    def _topological_sort(self) -> List[str]:
        """拓扑排序确定执行顺序（Kahn 算法）"""
        # 构建入度表
        in_degree = {name: 0 for name in self.steps}
        dependents = {name: [] for name in self.steps}
        
        for name, step in self.steps.items():
            if step.depends_on and step.depends_on in self.steps:
                in_degree[name] = 1
                dependents[step.depends_on].append(name)
        
        # 找到所有入度为 0 的节点
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            # 按名称排序，确保确定性顺序
            queue.sort()
            current = queue.pop(0)
            result.append(current)
            
            # 减少依赖当前节点的节点的入度
            for dependent in dependents[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # 检查是否有环
        if len(result) != len(self.steps):
            self._log("⚠️ 检测到循环依赖，使用默认顺序", "warning")
            # 返回默认顺序
            return sorted(self.steps.keys())
        
        return result
    
    def _confirm_overwrite(self, step_name: str) -> str:
        """确认是否覆盖已存在的文件
        
        Returns:
            "skip" | "overwrite" | "stop"
        """
        # 默认行为：需要 UI 层覆盖此方法提供交互
        # 这里返回 "overwrite" 作为默认
        return "overwrite"
    
    def _log(self, message: str, level: str = "info"):
        """记录日志"""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            timestamp = asyncio.get_event_loop().time()
            print(f"[{timestamp:.2f}] [{level.upper()}] {message}")
    
    def _progress(self, step_name: str, progress: float):
        """更新进度"""
        if self.progress_callback:
            self.progress_callback(step_name, progress)
    
    def reset_all(self):
        """重置所有步骤状态"""
        for step in self.steps.values():
            step.status = "pending"
            step.generated_files = []
            step.error_message = None
            step.progress = 0.0
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        summary = {
            "total": len(self.steps),
            "completed": 0,
            "pending": 0,
            "running": 0,
            "error": 0,
            "steps": {}
        }
        
        for name, step in self.steps.items():
            summary["steps"][name] = {
                "status": step.status,
                "progress": step.progress,
                "files": step.generated_files,
                "error": step.error_message
            }
            
            if step.status == "completed":
                summary["completed"] += 1
            elif step.status == "pending":
                summary["pending"] += 1
            elif step.status == "running":
                summary["running"] += 1
            elif step.status == "error":
                summary["error"] += 1
        
        return summary
