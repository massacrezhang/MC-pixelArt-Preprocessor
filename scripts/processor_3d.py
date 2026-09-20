#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
processor_3d.py - 3D 立体地图画色彩空间、坐标映射与自适应抖动量化模块
负责加载与解析 presets/pic3d.png 色板，建立全部 183 种立体制图色与 16x16 调色板坐标的双向映射，
并在 OKLab 感知空间下执行 S 型往复自适应抖动量化。
"""

from pathlib import Path
import cv2
import numpy as np
from PIL import Image

from config import (
    PIC3D_PATH,
    DEFAULT_DITHER_WEIGHT,
    DEFAULT_EDGE_THRESHOLD,
    DEFAULT_FLAT_DEADZONE,
    DEFAULT_SERPENTINE
)
from palette import PaletteManager
from extractor import FeatureExtractor


class Palette3DManager:
    """
    Minecraft 3D 立体地图画调色板与坐标映射管理器
    解析 pic3d.png (16x16) 并维护全部 183 种三维有效色（阴影 0, 1, 2）与坐标映射关系。
    """

    def __init__(self, pic3d_path: Path = None):
        self.pic3d_path = Path(pic3d_path) if pic3d_path is not None else PIC3D_PATH
        if not self.pic3d_path.exists():
            raise FileNotFoundError(f"未找到 3D 调色板预设文件: {self.pic3d_path}")

        self.coord_to_info: dict[tuple[int, int], dict] = {}
        self.rgb_to_coord: dict[tuple[int, int, int], tuple[int, int]] = {}
        self.map_color_to_coord: dict[int, tuple[int, int]] = {}

        self.palette_rgb: np.ndarray = None       # (183, 3) uint8
        self.palette_coords: np.ndarray = None    # (183, 2) int32
        self.palette_map_ids: np.ndarray = None   # (183,) int32
        self.palette_oklab: np.ndarray = None     # (183, 3) float32

        # 快速向量化查找表 (256x256x256)
        self._rgb_to_coord_lut = np.full((256, 256, 256, 2), -1, dtype=np.int16)
        self._rgb_to_map_id_lut = np.full((256, 256, 256), -1, dtype=np.int16)

        self._load_from_pic3d()

    def _load_from_pic3d(self):
        """解析 pic3d.png 图像，建立坐标与 MapColor 的双向双射"""
        pil_img = Image.open(self.pic3d_path).convert("RGBA")
        img_arr = np.array(pil_img)
        h, w = img_arr.shape[:2]

        rgb_list = []
        coord_list = []
        id_list = []

        for y in range(h):
            for x in range(w):
                alpha = img_arr[y, x, 3]
                if alpha > 0:
                    r, g, b = int(img_arr[y, x, 0]), int(img_arr[y, x, 1]), int(img_arr[y, x, 2])
                    map_color = y * 16 + x
                    base_id = map_color // 4
                    shadow = map_color % 4

                    info = {
                        "coord": (x, y),
                        "rgb": (r, g, b),
                        "map_color": map_color,
                        "base_id": base_id,
                        "shadow": shadow
                    }

                    self.coord_to_info[(x, y)] = info
                    self.rgb_to_coord[(r, g, b)] = (x, y)
                    self.map_color_to_coord[map_color] = (x, y)

                    rgb_list.append((r, g, b))
                    coord_list.append((x, y))
                    id_list.append(map_color)

                    self._rgb_to_coord_lut[r, g, b] = (x, y)
                    self._rgb_to_map_id_lut[r, g, b] = map_color

        self.palette_rgb = np.array(rgb_list, dtype=np.uint8)
        self.palette_coords = np.array(coord_list, dtype=np.int32)
        self.palette_map_ids = np.array(id_list, dtype=np.int32)
        self.palette_oklab = PaletteManager.srgb_to_oklab(self.palette_rgb)

    def get_coord_by_rgb(self, r: int, g: int, b: int) -> tuple[int, int] | None:
        """通过 RGB 颜色查找在 pic3d.png 中的 (x, y) 坐标"""
        return self.rgb_to_coord.get((r, g, b))

    def get_info_by_coord(self, x: int, y: int) -> dict | None:
        """通过 (x, y) 坐标获取该色彩的完整 Minecraft 元信息"""
        return self.coord_to_info.get((x, y))

    def get_coord_by_map_color(self, map_color: int) -> tuple[int, int] | None:
        """通过 MapColor ID 获取 (x, y) 坐标"""
        return self.map_color_to_coord.get(map_color)

    def image_to_coords(self, processed_rgb: np.ndarray) -> np.ndarray:
        """
        将 183 色标准 RGB 图像向量化映射为坐标矩阵
        输入: (H, W, 3) uint8 RGB
        输出: (H, W, 2) int16 坐标矩阵，每个像素值为 (x, y) 属于 [0, 15]
        """
        r = processed_rgb[..., 0]
        g = processed_rgb[..., 1]
        b = processed_rgb[..., 2]
        return self._rgb_to_coord_lut[r, g, b]

    def image_to_map_color_ids(self, processed_rgb: np.ndarray) -> np.ndarray:
        """
        将 183 色标准 RGB 图像向量化映射为 MapColor ID 矩阵
        输入: (H, W, 3) uint8 RGB
        输出: (H, W) int16 MapColor 数组
        """
        r = processed_rgb[..., 0]
        g = processed_rgb[..., 1]
        b = processed_rgb[..., 2]
        return self._rgb_to_map_id_lut[r, g, b]

    def get_color_distribution(self, processed_rgb: np.ndarray) -> dict:
        """统计处理后图像中各个 3D 色彩的使用频率与覆盖情况"""
        unique_rgbs, counts = np.unique(processed_rgb.reshape(-1, 3), axis=0, return_counts=True)
        stats = []
        for rgb_vec, cnt in zip(unique_rgbs, counts):
            rgb_tuple = (int(rgb_vec[0]), int(rgb_vec[1]), int(rgb_vec[2]))
            coord = self.rgb_to_coord.get(rgb_tuple)
            info = self.coord_to_info.get(coord, {})
            stats.append({
                "rgb": rgb_tuple,
                "coord": coord,
                "map_color": info.get("map_color"),
                "base_id": info.get("base_id"),
                "shadow": info.get("shadow"),
                "pixel_count": int(cnt)
            })
        return {
            "total_pixels": processed_rgb.shape[0] * processed_rgb.shape[1],
            "unique_color_count": len(unique_rgbs),
            "palette_capacity": len(self.palette_rgb),
            "details": stats
        }


class AdaptiveDitherEngine3D:
    """
    3D 立体地图画自适应抖动核心引擎
    基于 183 色立体调色板与 OKLab 感知色彩空间，执行 S 型往复阻尼误差扩散与五官/背景自适应保护。
    """

    def __init__(
        self,
        palette_3d: Palette3DManager = None,
        dither_weight: float = DEFAULT_DITHER_WEIGHT,
        edge_threshold: float = DEFAULT_EDGE_THRESHOLD,
        flat_deadzone: float = DEFAULT_FLAT_DEADZONE,
        use_serpentine: bool = DEFAULT_SERPENTINE
    ):
        self.palette_3d = palette_3d if palette_3d is not None else Palette3DManager()
        self.extractor = FeatureExtractor(edge_threshold=edge_threshold, flat_deadzone=flat_deadzone)
        self.dither_weight = dither_weight
        self.edge_threshold = edge_threshold
        self.flat_deadzone = flat_deadzone
        self.use_serpentine = use_serpentine

    def process(self, img_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        对输入 BGR 图像执行 3D 183 色自适应量化与抖动处理
        返回: (output_rgb, coord_map)
          - output_rgb: 100% 严格符合 pic3d.png 183 色的 (H, W, 3) uint8 图像
          - coord_map: 每个像素对应在 pic3d.png 中的 (x, y) 坐标矩阵 (H, W, 2)
        """
        h, w = img_bgr.shape[:2]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # 1. 提取结构保真掩膜
        edge_mask, flat_mask = self.extractor.extract_masks(img_bgr)

        # 2. 转换到 OKLab 感知空间
        img_oklab = PaletteManager.srgb_to_oklab(img_rgb)

        # 3. 初始化量化与误差缓冲区 (带边界 padding 防止溢出)
        err_buf = np.zeros((h + 2, w + 2, 3), dtype=np.float32)
        output_rgb = np.zeros((h, w, 3), dtype=np.uint8)

        p_oklab = self.palette_3d.palette_oklab
        p_rgb = self.palette_3d.palette_rgb

        # 4. 逐行 S 型往复自适应抖动扫描
        for y in range(h):
            is_reverse = self.use_serpentine and (y % 2 == 1)
            x_range = range(w - 1, -1, -1) if is_reverse else range(w)

            for x in x_range:
                # 当前真实感知色彩 + 上游传导误差
                curr_c = img_oklab[y, x] + err_buf[y + 1, x + 1]

                # 在 183 种立体色板中快速检索欧氏距离最近的颜色
                diff = p_oklab - curr_c
                dists_sq = np.sum(diff * diff, axis=-1)
                best_idx = int(np.argmin(dists_sq))

                best_oklab = p_oklab[best_idx]
                best_rgb = p_rgb[best_idx]
                output_rgb[y, x] = best_rgb

                # 计算量化误差
                err = curr_c - best_oklab
                err_norm = np.sqrt(np.sum(err * err))

                # 自适应门限调节
                m_edge = edge_mask[y, x]
                m_flat = flat_mask[y, x]

                # 平坦背景死区门限：平坦区域吸收微弱误差，避免产生蠕虫噪点
                if m_flat > 0.4 and err_norm < (self.flat_deadzone * 1.5):
                    err = err * (1.0 - m_flat)

                # 边缘保护：五官线条与强对比度轮廓阻断误差扩散
                if m_edge > 0.45:
                    eff_weight = 0.0
                else:
                    eff_weight = self.dither_weight * (1.0 - 0.9 * m_edge)

                err_diffuse = err * eff_weight

                # S 型往复误差传导权重分配
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

        # 5. 快速反向映射生成全图坐标矩阵
        coord_map = self.palette_3d.image_to_coords(output_rgb)

        return output_rgb, coord_map


def process_image_3d(
    img_bgr: np.ndarray,
    palette_3d: Palette3DManager = None,
    dither_weight: float = DEFAULT_DITHER_WEIGHT,
    edge_threshold: float = DEFAULT_EDGE_THRESHOLD,
    flat_deadzone: float = DEFAULT_FLAT_DEADZONE,
    use_serpentine: bool = DEFAULT_SERPENTINE
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    3D 图像处理统一便捷调用函数
    返回: (processed_rgb, coord_map, stats)
    """
    engine = AdaptiveDitherEngine3D(
        palette_3d=palette_3d,
        dither_weight=dither_weight,
        edge_threshold=edge_threshold,
        flat_deadzone=flat_deadzone,
        use_serpentine=use_serpentine
    )
    processed_rgb, coord_map = engine.process(img_bgr)
    stats = engine.palette_3d.get_color_distribution(processed_rgb)
    return processed_rgb, coord_map, stats
