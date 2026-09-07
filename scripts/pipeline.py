#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline.py - PipelineManager 预处理全流程调度编排模块
统筹两阶段模式调度、原始文件保真复制、处理后大图生成与子图切片归档。
"""

import time
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from config import PICS_DIR, TILE_SIZE, DEFAULT_DITHER_WEIGHT, DEFAULT_EDGE_THRESHOLD, DEFAULT_FLAT_DEADZONE, DEFAULT_SERPENTINE
from palette import PaletteManager
from dither_engine import AdaptiveDitherEngine
from slicer import ImageSlicer


class PipelineManager:
    """MapArt 图像预处理全流程编排管理器"""

    def __init__(self, pics_dir: Path = None):
        self.pics_dir = pics_dir if pics_dir is not None else PICS_DIR
        self.palette_mgr = PaletteManager()
        self.slicer = ImageSlicer(tile_size=TILE_SIZE)

    def _prepare_project_dir(self, input_path: Path, custom_name: str = None) -> tuple[Path, str, str]:
        """
        初始化项目目录并校验文件名
        返回: (project_dir, project_name, file_suffix)
        """
        project_name = custom_name.strip() if custom_name else input_path.stem
        suffix = input_path.suffix.lower()
        if not suffix:
            suffix = ".png"

        project_dir = self.pics_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir, project_name, suffix

    def run_mode1_slice_only(self, input_path: Path, project_name: str = None) -> dict:
        """
        【模式 1：直接切片模式】
        跳过色彩转换与抖动，原样保留 100% 原始像素，直接切分成 128x128 纵向优先子图。
        """
        t0 = time.time()
        input_path = Path(input_path).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"未找到输入图片: {input_path}")

        project_dir, proj_name, suffix = self._prepare_project_dir(input_path, project_name)

        # 1. 复制未修改的原图到 PICS/{project}/，文件名保持严格一致
        raw_copy_path = project_dir / f"{proj_name}{suffix}"
        if input_path != raw_copy_path:
            shutil.copy2(input_path, raw_copy_path)
            print(f"[原图保存] 已归档原图副本: {raw_copy_path.name}")

        # 2. 读取图像进行切片
        pil_img = Image.open(input_path).convert("RGBA")
        w, h = pil_img.size
        is_valid, cols, rows = self.slicer.validate_dimensions(w, h)
        if not is_valid:
            print(f"[警告] 图像尺寸 {w}x{h} 不是 {TILE_SIZE} 的整数倍，切片可能发生边缘截断！")

        # 3. 纵向优先切片
        sliced_files = self.slicer.slice_column_first(pil_img, project_dir, proj_name)
        t1 = time.time()

        return {
            "mode": 1,
            "mode_name": "Direct Slice (纯切片模式)",
            "project_name": proj_name,
            "project_dir": str(project_dir),
            "raw_image": str(raw_copy_path),
            "processed_image": None,
            "num_tiles": len(sliced_files),
            "time_cost": round(t1 - t0, 2)
        }

    def run_mode2_dither_and_slice(
        self,
        input_path: Path,
        project_name: str = None,
        dither_weight: float = None,
        edge_threshold: float = None,
        flat_deadzone: float = None,
        use_serpentine: bool = None
    ) -> dict:
        """
        【模式 2：保真优化 + 切片模式】
        1. 归档原始整图；
        2. 执行 Minecraft 61色平面自适应保真抖动优化（OKLab空间、五官阻断、背景去噪）；
        3. 保存处理后高清大图（文件名按 Windows 排序紧随原图正后方）；
        4. 对处理后大图切分 128x128 纵向优先子图。
        """
        t0 = time.time()
        input_path = Path(input_path).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"未找到输入图片: {input_path}")

        project_dir, proj_name, suffix = self._prepare_project_dir(input_path, project_name)

        # 1. 复制原图副本，文件名保持严格一致
        raw_copy_path = project_dir / f"{proj_name}{suffix}"
        if input_path != raw_copy_path:
            shutil.copy2(input_path, raw_copy_path)
            print(f"[原图保存] 已归档原图副本: {raw_copy_path.name}")

        # 2. 读取图像
        img_bgr = cv2.imread(str(input_path))
        if img_bgr is None:
            raise ValueError(f"无法使用 OpenCV 读取图像: {input_path}")

        h, w = img_bgr.shape[:2]
        is_valid, cols, rows = self.slicer.validate_dimensions(w, h)
        if not is_valid:
            print(f"[警告] 图像尺寸 {w}x{h} 不是 {TILE_SIZE} 的整数倍，切片可能发生边缘截断！")

        # 3. 实例化自适应抖动引擎并执行处理
        dw = dither_weight if dither_weight is not None else DEFAULT_DITHER_WEIGHT
        et = edge_threshold if edge_threshold is not None else DEFAULT_EDGE_THRESHOLD
        fd = flat_deadzone if flat_deadzone is not None else DEFAULT_FLAT_DEADZONE
        serp = use_serpentine if use_serpentine is not None else DEFAULT_SERPENTINE

        print(f"正在执行自适应抖动处理 (参数: weight={dw}, edge_thresh={et}, deadzone={fd}, serpentine={serp})...")
        engine = AdaptiveDitherEngine(
            palette_mgr=self.palette_mgr,
            dither_weight=dw,
            edge_threshold=et,
            flat_deadzone=fd,
            use_serpentine=serp
        )
        processed_rgb = engine.process(img_bgr)

        # 4. 保存处理后高清大图 (使用 .processed.png 确保在 Windows 资源管理器排序中紧随原图正后方)
        processed_path = project_dir / f"{proj_name}.processed.png"
        proc_bgr = cv2.cvtColor(processed_rgb, cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(processed_path), proc_bgr)
        print(f"[大图保存] 已生成 61 色标准处理大图: {processed_path.name}")

        # 5. 对处理后的大图执行 128x128 纵向优先切片
        pil_proc = Image.fromarray(processed_rgb)
        sliced_files = self.slicer.slice_column_first(pil_proc, project_dir, proj_name)

        t1 = time.time()
        unique_colors = len(np.unique(processed_rgb.reshape(-1, 3), axis=0))

        return {
            "mode": 2,
            "mode_name": "Adaptive Dither + Slice (保真优化+切片模式)",
            "project_name": proj_name,
            "project_dir": str(project_dir),
            "raw_image": str(raw_copy_path),
            "processed_image": str(processed_path),
            "num_tiles": len(sliced_files),
            "unique_colors": unique_colors,
            "time_cost": round(t1 - t0, 2)
        }
