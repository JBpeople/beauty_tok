#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美颜视频播放器启动脚本
"""

import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

try:
    from view import main

    if __name__ == "__main__":
        main()
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"运行错误: {e}")
    sys.exit(1)
