#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
slicer.py - ImageSlicer 网格切片模块
负责对图像进行 128x128 像素纵向优先（Column-First）切块并编号落盘。
"""

from pathlib import Path
from PIL import Image


class ImageSlicer:
    """Minecraft 地图画标准网格切片器"""

    def __init__(self, tile_size: int = 128):
        self.tile_size = tile_size

    def validate_dimensions(self, width: int, height: int) -> tuple[bool, int, int]:
        """
        检验尺寸是否满足 128x128 整数倍
        返回: (is_valid, cols, rows)
        """
        cols = width // self.tile_size
        rows = height // self.tile_size
        is_valid = (width % self.tile_size == 0) and (height % self.tile_size == 0) and (cols > 0) and (rows > 0)
        return is_valid, cols, rows

    def slice_column_first(
        self,
        pil_image: Image.Image,
        project_dir: Path,
        project_name: str
    ) -> list[Path]:
        """
        将图像按 128x128 像素切块。
        切分顺序：纵向优先（先从上到下切完第 1 列，再切第 2 列...）。
        例如 2x3 网格:
          第1列: 0, 1, 2
          第2列: 3, 4, 5
        """
        w, h = pil_image.size
        cols = w // self.tile_size
        rows = h // self.tile_size
        sliced_paths = []

        if cols == 0 or rows == 0:
            print(f"[提示] 图像尺寸 ({w}x{h}) 小于 {self.tile_size}x{self.tile_size}，跳过切片。")
            return sliced_paths

        index = 0
        # 外层循环遍历列 (横向)，内层循环遍历行 (纵向)，实现纵向优先排列
        for c in range(cols):
            for r in range(rows):
                left = c * self.tile_size
                top = r * self.tile_size
                right = left + self.tile_size
                bottom = top + self.tile_size

                box = (left, top, right, bottom)
                tile = pil_image.crop(box)

                tile_filename = f"{project_name}_{index}.png"
                tile_path = project_dir / tile_filename
                tile.save(tile_path)
                sliced_paths.append(tile_path)
                index += 1

        print(f"成功切片: 共 {cols} 列 x {rows} 行 = {len(sliced_paths)} 张 {self.tile_size}x{self.tile_size} 纵向优先地图画图块。")
        return sliced_paths
