#!/bin/bash
# 🎮 Vehicle Game Console 快速启动脚本

echo "============================================================"
echo "🎮 Vehicle Game Console v0.1.0"
echo "============================================================"
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在"
    echo "请先运行：python3 -m venv .venv"
    exit 1
fi

# 激活虚拟环境
echo "✅ 激活虚拟环境..."
source .venv/bin/activate

# 检查依赖
echo "📦 检查依赖..."
python -c "import customtkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  CustomTkinter 未安装，正在安装..."
    pip install customtkinter -q
fi

python -c "import dearpygui" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  DearPyGui 未安装，正在安装..."
    pip install dearpygui -q
fi

python -c "import panda3d" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Panda3D 未安装（游戏功能将不可用）"
    echo "安装：pip install panda3d"
fi

echo ""
echo "🚀 启动控制台..."
echo "============================================================"
echo ""

# 启动控制台
python console.py
