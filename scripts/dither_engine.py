#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dither_engine.py - AdaptiveDitherEngine 自适应抖动核心引擎
执行 OKLab 空间下的 S型往复扫描、自适应边缘阻断与背景死区误差扩散循环。
"""

import cv2
import numpy as np
from palette import PaletteManager
from extractor import FeatureExtractor


class AdaptiveDitherEngine:
    """自适应抖动核心量化引擎"""

    def __init__(
        self,
        palette_mgr: PaletteManager = None,
        dither_weight: float = 0.85,
        edge_threshold: float = 0.22,
        flat_deadzone: float = 0.018,
        use_serpentine: bool = True
    ):
        self.palette_mgr = palette_mgr if palette_mgr is not None else PaletteManager()
        self.extractor = FeatureExtractor(edge_threshold=edge_threshold, flat_deadzone=flat_deadzone)
        self.dither_weight = dither_weight
        self.edge_threshold = edge_threshold
        self.flat_deadzone = flat_deadzone
        self.use_serpentine = use_serpentine

    def process(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        对输入 BGR 图像执行自适应量化与抖动处理
        返回: 100% 严格符合色板定义的 (H, W, 3) uint8 RGB 图像
        """
        h, w = img_bgr.shape[:2]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # 1. 提取结构掩膜
        edge_mask, flat_mask = self.extractor.extract_masks(img_bgr)

        # 2. 转入 OKLab 空间
        img_oklab = self.palette_mgr.srgb_to_oklab(img_rgb)

        # 3. 初始化误差缓冲区 (带边界 padding 防止越界)
        err_buf = np.zeros((h + 2, w + 2, 3), dtype=np.float32)
        output_rgb = np.zeros((h, w, 3), dtype=np.uint8)

        p_oklab = self.palette_mgr.palette_oklab
        p_rgb = self.palette_mgr.palette_rgb

        # 4. 逐行往复遍历扫描
        for y in range(h):
            is_reverse = self.use_serpentine and (y % 2 == 1)
            x_range = range(w - 1, -1, -1) if is_reverse else range(w)

            for x in x_range:
                # 当前真实颜色 + 累积扩散误差
                curr_c = img_oklab[y, x] + err_buf[y + 1, x + 1]

                # 快速检索最近邻方块
                diff = p_oklab - curr_c
                dists_sq = np.sum(diff * diff, axis=-1)
                best_idx = int(np.argmin(dists_sq))

                best_oklab = p_oklab[best_idx]
                best_rgb = p_rgb[best_idx]
                output_rgb[y, x] = best_rgb

                # 计算量化误差
                err = curr_c - best_oklab
                err_norm = np.sqrt(np.sum(err * err))

                # 自适应阻断与死区吸收逻辑
                m_edge = edge_mask[y, x]
                m_flat = flat_mask[y, x]

                # 平坦背景死区门限：如果微小误差处于纯平背景，吸收误差避免蠕虫杂斑
                if m_flat > 0.4 and err_norm < (self.flat_deadzone * 1.5):
                    err = err * (1.0 - m_flat)

                # 边缘保护调制：五官与暗线处阻断扩散 (无抖动保真)
                if m_edge > 0.45:
                    eff_weight = 0.0  # 彻底阻断，不向周围扩散
                else:
                    eff_weight = self.dither_weight * (1.0 - 0.9 * m_edge)

                err_diffuse = err * eff_weight

                # 阻尼误差分配 (向右/左及下方扩散)
                if not is_reverse:
                    # 正向：从左向右
                    err_buf[y + 1, x + 2] += err_diffuse * (7.0 / 16.0)
                    err_buf[y + 2, x]     += err_diffuse * (3.0 / 16.0)
                    err_buf[y + 2, x + 1] += err_diffuse * (5.0 / 16.0)
                    err_buf[y + 2, x + 2] += err_diffuse * (1.0 / 16.0)
                else:
                    # 反向：从右向左
                    err_buf[y + 1, x]     += err_diffuse * (7.0 / 16.0)
                    err_buf[y + 2, x + 2] += err_diffuse * (3.0 / 16.0)
                    err_buf[y + 2, x + 1] += err_diffuse * (5.0 / 16.0)
                    err_buf[y + 2, x]     += err_diffuse * (1.0 / 16.0)

        return output_rgb
