#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py - MapArt 图像预处理与自适应抖动全局配置中心
集中维护所有算法超参数、Minecraft 61基准色板、切片尺寸与路径常量。
"""

from pathlib import Path
import numpy as np


# =============================================================================
# 1. 工作区与目录路径定义
# =============================================================================
def find_workspace_root(start_path: Path) -> Path:
    """自动向上寻访 MapArt 工作区根目录"""
    curr = start_path.resolve()
    while curr.parent != curr:
        if (curr / "presets").exists() or ((curr / "PICS").exists() and (curr / "prep-slopecraft-image").exists()):
            return curr
        curr = curr.parent
    return start_path.parents[1]


SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = find_workspace_root(SCRIPT_DIR)
PICS_DIR = WORKSPACE_ROOT / "PICS"

# =============================================================================
# 2. 地图画基础物理规格
# =============================================================================
TILE_SIZE = 128  # Minecraft 单张地图固定画幅尺寸 (128x128 像素)

# =============================================================================
# 3. 自适应抖动核心算法超参数
# =============================================================================
DEFAULT_COLOR_MODE = "flat61"  # 默认工作模式: 61色平面地图画 (固定 Shadow=1 因子 220/255)

# 基础抖动强度 (推荐范围 0.70 ~ 0.95，默认 0.85)
# 控制全局色彩混合质感（以视觉效果/抖动为主）。调大渐变更柔和；调小偏纯色块感。
DEFAULT_DITHER_WEIGHT = 0.8

# 五官与线条边缘保护灵敏度 (推荐范围 0.15 ~ 0.40，默认 0.22)
# 保护眼睛、睫毛、唇线、发丝等微弱暗线不被周围色差冲刷（无抖动/纯净线条为辅）。
DEFAULT_EDGE_THRESHOLD = 0.25

# 平坦区/大背景纯色死区门限 (推荐范围 0.010 ~ 0.035，默认 0.018)
# 消除纯色或低方差大背景上的孤立蠕虫斑纹，锁定纯净大色块。
DEFAULT_FLAT_DEADZONE = 0.02

# S型往复扫描开关 (True/False，默认 True)
# 消除传统单向从左到右扫描带来的对角线蠕虫偏向纹理。
DEFAULT_SERPENTINE = True

# =============================================================================
# 4. Minecraft 官方标准 61 种基准地图色 (MapColor 1 ~ 61)
# =============================================================================
BASE_COLORS_RAW = {
    1: (127, 178, 56),    # grass
    2: (247, 233, 163),   # sand
    3: (199, 199, 199),   # wool
    4: (255, 0, 0),       # fire / redstone
    5: (160, 160, 255),   # ice
    6: (167, 167, 167),   # iron
    7: (0, 124, 0),       # foliage
    8: (255, 255, 255),   # snow
    9: (164, 168, 184),   # clay
    10: (151, 109, 77),   # dirt
    11: (112, 112, 112),  # stone
    12: (64, 64, 255),    # water
    13: (143, 119, 72),   # wood
    14: (255, 252, 245),  # quartz
    15: (216, 127, 51),   # color_orange
    16: (178, 76, 216),   # color_magenta
    17: (102, 153, 216),  # color_light_blue
    18: (229, 229, 51),   # color_yellow
    19: (127, 204, 25),   # color_light_green
    20: (242, 127, 165),  # color_pink
    21: (76, 76, 76),     # color_gray
    22: (153, 153, 153),  # color_light_gray
    23: (76, 127, 153),   # color_cyan
    24: (127, 63, 178),   # color_purple
    25: (51, 76, 178),    # color_blue
    26: (102, 76, 51),    # color_brown
    27: (102, 127, 51),   # color_green
    28: (153, 51, 51),    # color_red
    29: (25, 25, 25),     # color_black
    30: (250, 238, 77),   # gold
    31: (92, 219, 213),   # diamond
    32: (74, 128, 255),   # lapis
    33: (0, 217, 58),     # emerald
    34: (129, 86, 49),    # podzol
    35: (112, 2, 0),      # nether
    36: (209, 177, 161),  # terracotta_white
    37: (159, 82, 36),    # terracotta_orange
    38: (149, 87, 108),   # terracotta_magenta
    39: (112, 108, 138),  # terracotta_light_blue
    40: (186, 133, 36),   # terracotta_yellow
    41: (103, 117, 53),   # terracotta_light_green
    42: (160, 77, 78),    # terracotta_pink
    43: (57, 41, 35),     # terracotta_gray
    44: (135, 107, 98),   # terracotta_light_gray
    45: (87, 92, 92),     # terracotta_cyan
    46: (122, 73, 88),    # terracotta_purple
    47: (76, 62, 92),     # terracotta_blue
    48: (76, 50, 35),     # terracotta_brown
    49: (76, 82, 42),     # terracotta_green
    50: (142, 60, 46),    # terracotta_red
    51: (37, 22, 16),     # terracotta_black
    52: (189, 48, 49),    # crimson_nylium
    53: (148, 63, 97),    # crimson_stem
    54: (92, 25, 29),     # crimson_hyphae
    55: (22, 126, 134),   # warped_nylium
    56: (58, 142, 140),   # warped_stem
    57: (86, 44, 62),     # warped_hyphae
    58: (20, 180, 133),   # warped_wart_block
    59: (100, 100, 100),  # deepslate
    60: (216, 175, 147),  # raw_iron
    61: (127, 167, 150),  # glow_lichen
}

# =============================================================================
# 5. OKLab 感知色彩空间线性变换矩阵
# =============================================================================
OKLAB_M1 = np.array([
    [0.4122214708, 0.5363325363, 0.0514459929],
    [0.2119034982, 0.6806995451, 0.1073969566],
    [0.0883024619, 0.2817188376, 0.6299787005]
], dtype=np.float32)

OKLAB_M2 = np.array([
    [0.2104542553, 0.7936177850, -0.0040720468],
    [1.9779984951, -2.4285922050, 0.4505937099],
    [0.0259040371, 0.7827717662, -0.8086757660]
], dtype=np.float32)
