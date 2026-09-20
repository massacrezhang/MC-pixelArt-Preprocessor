#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_3d_features.py - 3D 调色板、坐标转换与自适应抖动单元测试
"""

import sys
from pathlib import Path
import numpy as np

# 加入 scripts 目录
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from processor_3d import Palette3DManager, AdaptiveDitherEngine3D, process_image_3d


def test_palette_3d_and_coords():
    print("=== [测试 1] 3D 调色板加载与坐标映射闭环校验 ===")
    palette_mgr = Palette3DManager()

    # 1. 检验提取色彩数量严格为 183
    assert len(palette_mgr.palette_rgb) == 183, f"期望 183 种颜色，实际得到 {len(palette_mgr.palette_rgb)}"
    assert len(palette_mgr.coord_to_info) == 183, f"期望 183 个坐标信息，实际得到 {len(palette_mgr.coord_to_info)}"
    assert len(palette_mgr.rgb_to_coord) == 183, f"期望 183 个唯一 RGB，实际得到 {len(palette_mgr.rgb_to_coord)}"

    # 2. 检验坐标与 MapColor 的数学公式与有效范围
    for coord, info in palette_mgr.coord_to_info.items():
        x, y = coord
        assert 0 <= x < 16 and 0 <= y < 16, f"坐标越界: ({x}, {y})"
        expected_map_color = y * 16 + x
        assert info["map_color"] == expected_map_color, f"MapColor 计算不一致: {info['map_color']} vs {expected_map_color}"
        assert 1 <= info["base_id"] <= 61, f"Base ID 超出范围 1~61: {info['base_id']}"
        assert info["shadow"] in (0, 1, 2), f"Shadow 只能为 0, 1, 2: {info['shadow']}"

        # 双向查询闭环校验
        rgb = info["rgb"]
        found_coord = palette_mgr.get_coord_by_rgb(*rgb)
        assert found_coord == coord, f"反向 RGB 查坐标失败: {coord} -> {rgb} -> {found_coord}"

        coord_info = palette_mgr.get_info_by_coord(x, y)
        assert coord_info == info, f"坐标查信息不匹配: {coord}"

        mc_coord = palette_mgr.get_coord_by_map_color(expected_map_color)
        assert mc_coord == coord, f"MapColor 查坐标不匹配: {expected_map_color} -> {mc_coord}"

    print("[通过] pic3d.png 全部 183 色解析成功，数学坐标双向映射 100% 准确！")


def test_vectorized_coord_mapping():
    print("\n=== [测试 2] 批量图像反向坐标矩阵向量化映射测试 ===")
    palette_mgr = Palette3DManager()

    # 随机取 1000 个采样像素构造合成图像
    indices = np.random.randint(0, 183, size=(64, 64))
    synthetic_rgb = palette_mgr.palette_rgb[indices]

    coord_map = palette_mgr.image_to_coords(synthetic_rgb)
    assert coord_map.shape == (64, 64, 2), f"坐标矩阵形状不正确: {coord_map.shape}"

    # 抽样验证 20 个点
    for _ in range(20):
        r_idx = np.random.randint(0, 64)
        c_idx = np.random.randint(0, 64)
        rgb_val = tuple(synthetic_rgb[r_idx, c_idx])
        expected_coord = palette_mgr.get_coord_by_rgb(*rgb_val)
        actual_coord = tuple(coord_map[r_idx, c_idx])
        assert actual_coord == expected_coord, f"向量化查找坐标不符: {actual_coord} vs {expected_coord}"

    print("[通过] 批量图像反向坐标矩阵向量化映射验证成功！")


def test_adaptive_dither_3d():
    print("\n=== [测试 3] 3D 自适应抖动量化引擎色彩约束验证 ===")
    # 构造渐变色彩图像 (128x128)
    h, w = 128, 128
    x = np.linspace(0, 255, w)
    y = np.linspace(0, 255, h)
    xx, yy = np.meshgrid(x, y)
    test_bgr = np.zeros((h, w, 3), dtype=np.uint8)
    test_bgr[..., 0] = xx.astype(np.uint8)
    test_bgr[..., 1] = yy.astype(np.uint8)
    test_bgr[..., 2] = ((xx + yy) / 2).astype(np.uint8)

    palette_mgr = Palette3DManager()
    engine = AdaptiveDitherEngine3D(palette_3d=palette_mgr)

    output_rgb, coord_map = engine.process(test_bgr)
    assert output_rgb.shape == (h, w, 3)
    assert coord_map.shape == (h, w, 2)

    # 验证处理后图像中的每一个像素均 100% 存在于 183 色板中
    unique_rgbs = np.unique(output_rgb.reshape(-1, 3), axis=0)
    print(f"测试图像共激活了 {len(unique_rgbs)} 种 3D 地图色彩 (总色板 183 色)")
    for rgb_vec in unique_rgbs:
        rgb_t = tuple(rgb_vec)
        assert rgb_t in palette_mgr.rgb_to_coord, f"发现非 3D 色板的异常色彩: {rgb_t}"

    # 验证输出的坐标图完全在 [0, 15] 之间
    assert np.all(coord_map >= 0) and np.all(coord_map <= 15), "坐标超出 16x16 色板区间！"

    print("[通过] 3D 自适应抖动量化引擎输出色彩 100% 严格受限于 183 色立体调色板！")


if __name__ == "__main__":
    test_palette_3d_and_coords()
    test_vectorized_coord_mapping()
    test_adaptive_dither_3d()
    print("\n" + "=" * 50)
    print("   全部 3D 核心模块单元测试 100% 通过！")
    print("=" * 50)
