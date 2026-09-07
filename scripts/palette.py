#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
palette.py - PaletteManager 调色板与色彩空间管理模块
封装 Minecraft 61色平面地图画色板构建及 OKLab 感知空间正逆向变换。
"""

import numpy as np
from config import BASE_COLORS_RAW, OKLAB_M1, OKLAB_M2


class PaletteManager:
    """Minecraft 地图画色板管理器"""

    def __init__(self, mode: str = "flat61"):
        self.mode = mode
        self.palette_rgb, self.palette_ids = self._build_flat61_palette()
        self.palette_oklab = self.srgb_to_oklab(self.palette_rgb)

    def _build_flat61_palette(self) -> tuple[np.ndarray, list[int]]:
        """
        构建 61 色平面地图画调色板
        遵循 Minecraft 标准: round(base_rgb * 220.0 / 255.0)
        """
        rgb_list = []
        id_list = []
        for cid in sorted(BASE_COLORS_RAW.keys()):
            base_r, base_g, base_b = BASE_COLORS_RAW[cid]
            r = int(round(base_r * 220.0 / 255.0))
            g = int(round(base_g * 220.0 / 255.0))
            b = int(round(base_b * 220.0 / 255.0))
            rgb_list.append((r, g, b))
            id_list.append(cid)
        return np.array(rgb_list, dtype=np.uint8), id_list

    @staticmethod
    def srgb_to_oklab(rgb_array: np.ndarray) -> np.ndarray:
        """
        将 sRGB [0, 255] 转换为 OKLab [L, a, b]
        输入: (..., 3) 形状的 uint8 或 float
        输出: (..., 3) 形状的 float32 OKLab
        """
        rgb = rgb_array.astype(np.float32) / 255.0

        # sRGB 转为线性 RGB (Gamma 逆校正)
        mask = rgb <= 0.04045
        linear = np.empty_like(rgb)
        linear[mask] = rgb[mask] / 12.92
        linear[~mask] = ((rgb[~mask] + 0.055) / 1.055) ** 2.4

        # 线性 RGB -> LMS
        lms = linear @ OKLAB_M1.T
        lms = np.cbrt(np.maximum(lms, 0.0))

        # LMS -> OKLab
        lab = lms @ OKLAB_M2.T
        return lab

    def find_nearest(self, curr_oklab: np.ndarray) -> tuple[int, np.ndarray, np.ndarray]:
        """
        在 OKLab 空间检索与当前颜色欧氏距离最近的调色板方块
        返回: (best_index, best_oklab, best_rgb)
        """
        diff = self.palette_oklab - curr_oklab
        dists_sq = np.sum(diff * diff, axis=-1)
        best_idx = int(np.argmin(dists_sq))
        return best_idx, self.palette_oklab[best_idx], self.palette_rgb[best_idx]
