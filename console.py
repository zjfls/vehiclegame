#!/usr/bin/env python3
"""
🎮 Vehicle Game Console - 游戏控制台入口 (PySide6/Qt 版本)

功能:
- 游戏启动（支持多车辆配置）
- 地形生成工具
- 配置管理
- 可视化操作界面

使用方法:
    python console.py

依赖:
    pip install PySide6
"""

import sys
import os

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def check_dependencies():
    """检查依赖"""
    missing = []
    
    # 检查 PySide6（控制台 UI）
    try:
        import PySide6  # noqa: F401
    except ImportError:
        missing.append("PySide6")
    
    # 检查 Panda3D（游戏需要）
    try:
        from direct.showbase.ShowBase import ShowBase
    except ImportError:
        print("警告：Panda3D 未安装，游戏功能将不可用")
        print("安装：pip install panda3d")
    
    if missing:
        print("错误：缺少以下依赖:")
        for dep in missing:
            print(f"  - {dep}")
        print("\n请运行：pip install " + " ".join(missing))
        return False
    
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("🎮 Vehicle Game Console v0.2.0")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    print("\n检查依赖... ✓")
    print("启动控制台...\n")
    
    # 导入并运行应用
    from console_app import ConsoleApp
    
    app = ConsoleApp()
    app.initialize()
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n用户中断")
        app._exit_app()
    except Exception as e:
        print(f"\n错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
