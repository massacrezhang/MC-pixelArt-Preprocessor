#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extractor.py - FeatureExtractor 图像特征提取模块
负责计算 Scharr 边缘梯度保真掩膜与局部方差平坦背景掩膜。
"""

import cv2
import numpy as np


class FeatureExtractor:
    """图像边缘与平坦区域双通道特征提取器"""

    def __init__(self, edge_threshold: float = 0.22, flat_deadzone: float = 0.018):
        self.edge_threshold = edge_threshold
        self.flat_deadzone = flat_deadzone

    def extract_masks(self, img_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        提取图像的边缘保真掩膜与大平坦背景掩膜
        - edge_mask ~ 1.0: 眼睛、睫毛、发丝、轮廓暗线，需关闭抖动保护纯净线条
        - flat_mask ~ 1.0: 大面积均匀纯色背景，需启用死区过滤抑制蠕虫杂色
        """
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # 1. 边缘梯度提取 (采用精确的 Scharr 算子)
        grad_x = cv2.Scharr(gray, cv2.CV_32F, 1, 0)
        grad_y = cv2.Scharr(gray, cv2.CV_32F, 0, 1)
        grad_mag = np.sqrt(grad_x**2 + grad_y**2)
        grad_norm = grad_mag / (grad_mag.max() + 1e-6)

        # 边缘掩膜映射与轻度平滑
        edge_mask = np.clip((grad_norm - self.edge_threshold * 0.4) / (self.edge_threshold * 1.2 + 1e-6), 0.0, 1.0)
        edge_mask = cv2.GaussianBlur(edge_mask, (3, 3), 0.5)

        # 2. 局部平坦区提取 (5x5 局部标准差)
        mean = cv2.blur(gray.astype(np.float32), (5, 5))
        mean_sq = cv2.blur((gray.astype(np.float32))**2, (5, 5))
        std = np.sqrt(np.maximum(mean_sq - mean**2, 0.0))

        # 当局部标准差极小时判定为大面积纯色/平坦区
        flat_mask = np.clip(1.0 - std / 5.0, 0.0, 1.0)

        return edge_mask.astype(np.float32), flat_mask.astype(np.float32)
