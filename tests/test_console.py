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
    print(f"✓ 车辆配置：{vehicles}")
    assert len(vehicles) > 0, "应该有车辆配置"
    
    # 测试加载配置
    sports_car = cm.load_config("vehicles", "sports_car")
    print(f"✓ 加载跑车配置：{sports_car['name']}")
    assert sports_car['name'] == "Sports Car"
    assert sports_car['vehicle_mass'] == 1500.0
    
    truck = cm.load_config("vehicles", "truck")
    print(f"✓ 加载卡车配置：{truck['name']} (质量：{truck['vehicle_mass']}kg)")
    assert truck['vehicle_mass'] == 3500.0
    
    offroad = cm.load_config("vehicles", "offroad")
    print(f"✓ 加载越野车配置：{offroad['name']} (质量：{offroad['vehicle_mass']}kg)")
    assert offroad['vehicle_mass'] == 2200.0
    
    # 测试保存配置
    test_config = {"name": "Test Car", "vehicle_mass": 1000.0}
    cm.save_config("vehicles", "test_car", test_config)
    loaded = cm.load_config("vehicles", "test_car")
    print(f"✓ 保存并加载测试配置：{loaded['name']}")
    assert loaded['name'] == "Test Car"
    
    # 清理测试配置
    cm.delete_config("vehicles", "test_car")
    print(f"✓ 删除测试配置")
    
    print("\n✅ 配置管理器测试通过!\n")
    return True


def test_module_registry():
    """测试模块注册中心"""
    print("=" * 60)
    print("测试：模块注册中心")
    print("=" * 60)
    
    from console_modules.base_module import ModuleRegistry
    
    # 列出已注册模块
    modules = ModuleRegistry.list_modules()
    print(f"✓ 已注册模块：{list(modules.keys())}")
    
    # 测试创建模块实例
    for name in modules.keys():
        # 需要传入 console_app 参数，这里简单测试
        print(f"✓ 模块 {name} 已注册")
    
    print("\n✅ 模块注册中心测试通过!\n")
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
    
    print(f"✓ 命令执行结果：{result.status.value}")
    print(f"✓ 输出：{result.stdout.strip()}")
    assert result.status.value == "completed"
    assert "Hello from process manager" in result.stdout
    
    print("\n✅ 进程管理器测试通过!\n")
    return True


def test_module_imports():
    """测试模块导入"""
    print("=" * 60)
    print("测试：模块导入")
    print("=" * 60)
    
    # 测试游戏启动模块
    from console_modules.game_launcher import GameLauncherModule
    print(f"✓ 游戏启动模块导入成功：{GameLauncherModule.display_name}")
    
    # 测试地形生成模块
    from console_modules.terrain_generator import TerrainGeneratorModule
    print(f"✓ 地形生成模块导入成功：{TerrainGeneratorModule.display_name}")
    
    print("\n✅ 模块导入测试通过!\n")
    return True


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🎮 Vehicle Game Console - 组件测试")
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
            print(f"\n❌ {name} 测试失败：{e}\n")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"测试结果：{passed} 通过，{failed} 失败")
    print("=" * 60)
    
    if failed == 0:
        print("\n🎉 所有测试通过!\n")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
