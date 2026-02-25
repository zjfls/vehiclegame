"""
进程管理器 - 异步运行子进程（游戏、工具等）
"""
import asyncio
import subprocess
import sys
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ProcessStatus(Enum):
    """进程状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ProcessResult:
    """进程执行结果"""
    return_code: int
    stdout: str
    stderr: str
    status: ProcessStatus
    duration: float


class ProcessManager:
    """进程管理器"""
    
    def __init__(self):
        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._results: Dict[str, ProcessResult] = {}
    
    async def run_command(
        self,
        command_id: str,
        command: str,
        callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = None,
        cwd: Optional[str] = None
    ) -> ProcessResult:
        """
        运行命令（异步）
        
        Args:
            command_id: 命令唯一标识
            command: 要执行的命令
            callback: 实时输出回调（每行调用一次）
            timeout: 超时时间（秒）
            cwd: 工作目录
        
        Returns:
            ProcessResult: 执行结果
        """
        import time
        start_time = time.time()
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            self._processes[command_id] = process
            
            # 读取输出
            stdout_lines: List[str] = []
            stderr_lines: List[str] = []
            
            async def read_stream(stream, lines, is_stdout=True):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode('utf-8', errors='replace').rstrip()
                    lines.append(decoded)
                    if callback:
                        callback(decoded)
            
            # 并发读取 stdout 和 stderr
            await asyncio.gather(
                read_stream(process.stdout, stdout_lines, True),
                read_stream(process.stderr, stderr_lines, False)
            )
            
            # 等待进程结束
            if timeout:
                remaining = timeout - (time.time() - start_time)
                if remaining <= 0:
                    process.kill()
                    await process.wait()
                    return ProcessResult(
                        return_code=-1,
                        stdout="\n".join(stdout_lines),
                        stderr="\n".join(stderr_lines),
                        status=ProcessStatus.TIMEOUT,
                        duration=time.time() - start_time
                    )
                try:
                    await asyncio.wait_for(process.wait(), timeout=remaining)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    return ProcessResult(
                        return_code=-1,
                        stdout="\n".join(stdout_lines),
                        stderr="\n".join(stderr_lines),
                        status=ProcessStatus.TIMEOUT,
                        duration=time.time() - start_time
                    )
            else:
                await process.wait()
            
            status = ProcessStatus.COMPLETED if process.returncode == 0 else ProcessStatus.FAILED
            
            result = ProcessResult(
                return_code=process.returncode or 0,
                stdout="\n".join(stdout_lines),
                stderr="\n".join(stderr_lines),
                status=status,
                duration=time.time() - start_time
            )
            
            self._results[command_id] = result
            return result
            
        except Exception as e:
            return ProcessResult(
                return_code=-1,
                stdout="",
                stderr=str(e),
                status=ProcessStatus.FAILED,
                duration=time.time() - start_time
            )
        finally:
            self._processes.pop(command_id, None)
    
    def get_process_status(self, command_id: str) -> Optional[ProcessStatus]:
        """获取进程状态"""
        if command_id in self._processes:
            return ProcessStatus.RUNNING
        if command_id in self._results:
            return self._results[command_id].status
        return None
    
    def get_result(self, command_id: str) -> Optional[ProcessResult]:
        """获取执行结果"""
        return self._results.get(command_id)
    
    async def kill_process(self, command_id: str) -> bool:
        """终止进程"""
        if command_id in self._processes:
            try:
                self._processes[command_id].kill()
                await self._processes[command_id].wait()
                return True
            except Exception:
                return False
        return False
    
    def clear_result(self, command_id: str) -> None:
        """清除执行结果"""
        self._results.pop(command_id, None)
