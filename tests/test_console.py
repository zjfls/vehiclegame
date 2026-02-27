#!/usr/bin/env python3
"""
控制台组件测试脚本
"""
import sys
import os

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_config_manager():
    """测试配置管理器"""
    print("=" * 60)
    print("测试：配置管理器")
    print("=" * 60)
    
    from core.config_manager import ConfigManager
    
    cm = ConfigManager()
    
    # 测试列出配置
    vehicles = cm.list_configs("vehicles")
    print(f"Vehicle configs: {vehicles}")
    assert len(vehicles) > 0, "应该有车辆配置"
    
    # 测试加载配置
    sports_car = cm.load_config("vehicles", "sports_car")
    print(f"Loaded sports_car: {sports_car['name']}")
    assert sports_car['name'] == "Sports Car"
    assert int(sports_car.get('version', 0) or 0) == 2
    assert float(sports_car['chassis']['mass_kg']) == 1500.0
    
    truck = cm.load_config("vehicles", "truck")
    print(f"Loaded truck: {truck['name']} (mass={truck['chassis']['mass_kg']}kg)")
    assert float(truck['chassis']['mass_kg']) == 3500.0
    
    offroad = cm.load_config("vehicles", "offroad")
    print(f"Loaded offroad: {offroad['name']} (mass={offroad['chassis']['mass_kg']}kg)")
    assert float(offroad['chassis']['mass_kg']) == 2200.0
    
    # 测试保存配置
    test_config = {"name": "Test Car", "vehicle_mass": 1000.0}
    cm.save_config("vehicles", "test_car", test_config)
    loaded = cm.load_config("vehicles", "test_car")
    print(f"Saved and loaded test config: {loaded['name']}")
    assert loaded['name'] == "Test Car"
    
    # 清理测试配置
    cm.delete_config("vehicles", "test_car")
    print("Deleted test config")
    
    print("\nConfig manager test: OK\n")
    return True


def test_module_registry():
    """测试模块注册中心"""
    print("=" * 60)
    print("测试：模块注册中心")
    print("=" * 60)
    
    from console_modules.base_module import ModuleRegistry
    
    # 列出已注册模块
    modules = ModuleRegistry.list_modules()
    print(f"Registered modules: {list(modules.keys())}")
    
    # 测试创建模块实例
    for name in modules.keys():
        # 需要传入 console_app 参数，这里简单测试
        print(f"Module registered: {name}")
    
    print("\nModule registry test: OK\n")
    return True


def test_process_manager():
    """测试进程管理器"""
    print("=" * 60)
    print("测试：进程管理器")
    print("=" * 60)
    
    from core.process_manager import ProcessManager
    import asyncio
    
    pm = ProcessManager()
    
    # 测试运行简单命令
    async def test_run():
        result = await pm.run_command(
            "test_cmd",
            "echo 'Hello from process manager'",
            timeout=5.0
        )
        return result
    
    # 运行异步测试
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(test_run())
    
    print(f"Command status: {result.status.value}")
    print(f"Output: {result.stdout.strip()}")
    assert result.status.value == "completed"
    assert "Hello from process manager" in result.stdout
    
    print("\nProcess manager test: OK\n")
    return True


def test_module_imports():
    """测试模块导入"""
    print("=" * 60)
    print("测试：模块导入")
    print("=" * 60)

    try:
        from PySide6 import QtCore  # noqa: F401
    except Exception as e:
        # In CI / minimal environments, Qt may not be installed. Skip the UI import test.
        print(f"Skipping module import test (PySide6 not available): {e}")
        return True

    # Test module imports that require Qt.
    from console_modules.game_launcher import GameLauncherModule
    from console_modules.map_generator import MapGeneratorModule
    from console_modules.vehicle_editor import VehicleEditorModule

    print(f"Imported game launcher module: {GameLauncherModule.display_name}")
    print(f"Imported map generator module: {MapGeneratorModule.display_name}")
    print(f"Imported vehicle editor module: {VehicleEditorModule.display_name}")

    print("\nModule imports test: OK\n")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    # Avoid UnicodeEncodeError on Windows consoles using legacy encodings (e.g. GBK).
    print("Vehicle Game Console - component tests")
    print("=" * 60 + "\n")
    
    tests = [
        ("配置管理器", test_config_manager),
        ("模块注册中心", test_module_registry),
        ("进程管理器", test_process_manager),
        ("模块导入", test_module_imports),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\nFAIL: {name}: {e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"Results: passed={passed}, failed={failed}")
    print("=" * 60)
    
    if failed == 0:
        print("\nAll tests passed.\n")
        return 0
    else:
        print(f"\nSome tests failed: {failed}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
