#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py - MapArt 图像预处理与自适应抖动流水线统一入口
提供命令行参数调用与控制台无参交互式运行双模式。
"""

import sys
import io
import argparse
from pathlib import Path

# 兼容 Windows 控制台 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

from config import (
    WORKSPACE_ROOT,
    DEFAULT_COLOR_MODE,
    DEFAULT_DITHER_WEIGHT,
    DEFAULT_EDGE_THRESHOLD,
    DEFAULT_FLAT_DEADZONE,
    DEFAULT_SERPENTINE
)
from pipeline import PipelineManager


def prompt_interactive_menu() -> dict:
    """无参数运行时的交互式引导菜单"""
    print("\n" + "=" * 65)
    print("      Minecraft MapArt 图像预处理与自适应优化工具箱")
    print("=" * 65)
    print("功能模式说明：")
    print("  [1] 直接切片模式 (保持 100% 原画像素，仅切分为 128x128 纵向优先子图)")
    print("  [2] 保真优化 + 切片模式 (推荐: 61色平面自适应抖动优化 -> 导出大图 -> 切片)")
    print("-" * 65)

    # 1. 输入模式
    mode_input = input("请选择运行模式 [默认 2]: ").strip()
    mode = 1 if mode_input == "1" else 2

    # 2. 输入图片路径
    img_input = input("请输入图片路径 (可直接将文件拖拽入此窗口): ").strip().strip('"').strip("'")
    while not img_input:
        img_input = input("图片路径不能为空，请重新输入: ").strip().strip('"').strip("'")

    # 3. 输入可选项目名
    proj_input = input("请输入项目名称 [回车默认使用图片文件名]: ").strip().strip('"').strip("'")
    proj_name = proj_input if proj_input else None

    return {
        "mode": mode,
        "input": img_input,
        "project_name": proj_name
    }


def parse_arguments() -> argparse.Namespace:
    """命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="Minecraft MapArt 图像预处理与自适应抖动统一工具",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--input", "-i", type=str, help="输入图片路径 (例如 0831034707/0831034707.png)")
    parser.add_argument("--mode", "-m", type=int, choices=[1, 2], default=2, help="运行模式: 1=直接切片, 2=保真抖动+切片")
    parser.add_argument("--project-name", "-p", type=str, default=None, help="自定义项目文件夹名称 (默认取输入图片文件名)")
    parser.add_argument("--dither-weight", "-w", type=float, default=DEFAULT_DITHER_WEIGHT, help="基础抖动强度 (0.70~0.95)")
    parser.add_argument("--edge-threshold", "-e", type=float, default=DEFAULT_EDGE_THRESHOLD, help="五官边缘保护灵敏度 (0.15~0.40)")
    parser.add_argument("--flat-deadzone", "-d", type=float, default=DEFAULT_FLAT_DEADZONE, help="平坦背景纯色死区门限 (0.010~0.035)")
    parser.add_argument("--no-serpentine", action="store_true", help="禁用S型往复扫描 (改用传统单向扫描)")

    return parser.parse_args()


def main():
    args = parse_arguments()

    if not args.input:
        # 无参执行时进入交互式模式
        user_inputs = prompt_interactive_menu()
        input_path = Path(user_inputs["input"])
        mode = user_inputs["mode"]
        project_name = user_inputs["project_name"]
        dither_weight = DEFAULT_DITHER_WEIGHT
        edge_threshold = DEFAULT_EDGE_THRESHOLD
        flat_deadzone = DEFAULT_FLAT_DEADZONE
        use_serpentine = DEFAULT_SERPENTINE
    else:
        input_path = Path(args.input)
        mode = args.mode
        project_name = args.project_name
        dither_weight = args.dither_weight
        edge_threshold = args.edge_threshold
        flat_deadzone = args.flat_deadzone
        use_serpentine = not args.no_serpentine

    # 若输入为相对路径，自动转换为工作区绝对路径
    if not input_path.is_absolute():
        input_path = (WORKSPACE_ROOT / input_path).resolve()

    print(f"\n[任务启动] 模式: {mode} | 输入文件: {input_path}")
    pipeline = PipelineManager()

    if mode == 1:
        res = pipeline.run_mode1_slice_only(input_path, project_name=project_name)
    else:
        res = pipeline.run_mode2_dither_and_slice(
            input_path=input_path,
            project_name=project_name,
            dither_weight=dither_weight,
            edge_threshold=edge_threshold,
            flat_deadzone=flat_deadzone,
            use_serpentine=use_serpentine
        )

    print("\n" + "=" * 65)
    print("                      处理完成！产物清单")
    print("=" * 65)
    print(f"项目名称: {res['project_name']}")
    print(f"模式类型: {res['mode_name']}")
    print(f"成果目录: {res['project_dir']}")
    print(f"原始备份: {res['raw_image']}")
    if res.get("processed_image"):
        print(f"处理大图: {res['processed_image']} (Windows排序紧随原图)")
        print(f"色彩统计: 包含 {res['unique_colors']} 种 Minecraft 61色平面色")
    print(f"切片数量: {res['num_tiles']} 个 128x128 纵向优先子图")
    print(f"总计耗时: {res['time_cost']} 秒")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
