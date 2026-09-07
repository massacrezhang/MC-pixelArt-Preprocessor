#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
adaptive_dither.py - Minecraft 61色平面地图画高质量自适应抖动引擎

特性：
1. 默认 61 色平面地图画（严格对齐 Minecraft 原版 Shadow=1 因子 220/255 渲染）。
2. OKLab 感知色彩空间度量，彻底根治传统 CIELAB 引起的蓝色偏紫、浅色泛绿等大面积背景偏色。
3. 抖动为主、纯净色块与五官边缘保真为辅的自适应融合架构：
   - 绝大部分区域（~85%）全功率平滑抖动，呈现极佳的光影与细节混色视觉质感；
   - 关键五官与边缘（眼睛、睫毛、发丝、唇线）动态阻断误差扩散，保持线稿极致锐利（无抖动效果）；
   - 大面积纯色平坦背景应用死区门限过滤，杜绝孤立蠕虫斑纹。
4. S 型往复扫描（Serpentine Scan），打破单向扫描引起的对角线瑕疵偏向。
5. 非侵入式输出：绝不修改原文件夹，统一保存至 `PICTEMP_{project}/`。
"""

import os
import sys
import io
import time
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 兼容 Windows 控制台 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass


# =============================================================================
# 【核心参数微调区 / PARAMETER CONFIGURATION】
# 您可以直接修改以下字典中的默认数值，或在命令行运行脚本时传入对应参数覆盖
# =============================================================================
CONFIG = {
    # 1. 默认色彩模式：61色平面地图画 (flat61)
    # 严格按照 Minecraft 原版基色 * 220 // 255 计算基准色板
    "COLOR_MODE": "flat61",

    # 2. 基础抖动强度 (推荐范围 0.70 ~ 0.95，默认 0.85)
    # 作用：控制全局色彩混合质感（以视觉效果/抖动为主）。
    # - 调大（如 0.92）：色彩过渡更柔和、渐变更加细腻；
    # - 调小（如 0.75）：减少细碎杂点，画面更偏色块感。
    "DITHER_WEIGHT": 0.85,

    # 3. 五官与关键线条边缘保护阈值 (推荐范围 0.15 ~ 0.40，默认 0.22)
    # 作用：保护眼睛、睫毛、唇线、发丝等微弱线条不被周围色差冲刷（无抖动/纯净线条为辅）。
    # - 调小（如 0.16）：对微弱边缘更敏感，保护更多细小暗线；
    # - 调大（如 0.30）：只保护极强烈的大轮廓边缘。
    "EDGE_THRESHOLD": 0.22,

    # 4. 平坦区/大背景纯色死区门限 (推荐范围 0.010 ~ 0.035，默认 0.018)
    # 作用：消除纯色或低方差大背景上的孤立蠕虫斑纹，锁定纯净大色块。
    # - 调大（如 0.025）：背景更平整、绝对无杂色噪点；
    # - 调小（如 0.010）：允许背景有微弱色阶掺混。
    "FLAT_DEADZONE": 0.018,

    # 5. S型往复扫描开关 (True/False，默认 True)
    # 作用：消除传统从左向右单向扫描造成的对角线蠕虫条纹偏向。
    "SERPENTINE": True,
}


# =============================================================================
# Minecraft 官方标准 61 种基准地图色 (MapColor 1 ~ 61)
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


def get_flat61_palette():
    """
    生成 61 色平面地图画调色板 (RGB 与 ID)
    严格遵循 Minecraft 平面地图画公式: round(base_rgb * 220.0 / 255.0)
    """
    palette_rgb = []
    palette_ids = []
    for cid in sorted(BASE_COLORS_RAW.keys()):
        base_r, base_g, base_b = BASE_COLORS_RAW[cid]
        r = int(round(base_r * 220.0 / 255.0))
        g = int(round(base_g * 220.0 / 255.0))
        b = int(round(base_b * 220.0 / 255.0))
        palette_rgb.append((r, g, b))
        palette_ids.append(cid)
    return np.array(palette_rgb, dtype=np.uint8), palette_ids


# =============================================================================
# OKLab 感知色彩空间转换矩阵与矢量函数
# =============================================================================
M1 = np.array([
    [0.4122214708, 0.5363325363, 0.0514459929],
    [0.2119034982, 0.6806995451, 0.1073969566],
    [0.0883024619, 0.2817188376, 0.6299787005]
], dtype=np.float32)

M2 = np.array([
    [0.2104542553, 0.7936177850, -0.0040720468],
    [1.9779984951, -2.4285922050, 0.4505937099],
    [0.0259040371, 0.7827717662, -0.8086757660]
], dtype=np.float32)


def srgb_to_oklab(rgb_array: np.ndarray) -> np.ndarray:
    """
    将 sRGB [0, 255] 转换为 OKLab [L, a, b]
    支持任意 (..., 3) 形状
    """
    rgb = rgb_array.astype(np.float32) / 255.0
    # sRGB -> linear sRGB
    mask = rgb <= 0.04045
    linear = np.empty_like(rgb)
    linear[mask] = rgb[mask] / 12.92
    linear[~mask] = ((rgb[~mask] + 0.055) / 1.055) ** 2.4

    # linear sRGB -> LMS
    lms = linear @ M1.T
    lms = np.cbrt(np.maximum(lms, 0.0))

    # LMS -> OKLab
    lab = lms @ M2.T
    return lab


# =============================================================================
# 双通道特征提取：边缘掩膜 (Edge Mask) 与平坦掩膜 (Flat Mask)
# =============================================================================
def extract_feature_masks(img_bgr: np.ndarray, edge_thresh: float, flat_deadzone: float):
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
    edge_mask = np.clip((grad_norm - edge_thresh * 0.4) / (edge_thresh * 1.2 + 1e-6), 0.0, 1.0)
    edge_mask = cv2.GaussianBlur(edge_mask, (3, 3), 0.5)

    # 2. 局部平坦区提取 (5x5 局部标准差)
    mean = cv2.blur(gray.astype(np.float32), (5, 5))
    mean_sq = cv2.blur((gray.astype(np.float32))**2, (5, 5))
    std = np.sqrt(np.maximum(mean_sq - mean**2, 0.0))

    # 当局部标准差极小时判定为大面积纯色/平坦区
    flat_mask = np.clip(1.0 - std / 5.0, 0.0, 1.0)

    return edge_mask.astype(np.float32), flat_mask.astype(np.float32)


# =============================================================================
# 核心引擎：自适应抖动与保真量化循环
# =============================================================================
def process_adaptive_dither(
    img_bgr: np.ndarray,
    palette_rgb: np.ndarray,
    palette_oklab: np.ndarray,
    dither_weight: float = 0.85,
    edge_threshold: float = 0.22,
    flat_deadzone: float = 0.018,
    use_serpentine: bool = True
) -> np.ndarray:
    """
    在 OKLab 空间下执行带有边缘阻断与背景死区的 S 型往复自适应抖动
    """
    h, w = img_bgr.shape[:2]
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    # 1. 提取结构特征
    edge_mask, flat_mask = extract_feature_masks(img_bgr, edge_threshold, flat_deadzone)

    # 2. 转入 OKLab 空间
    img_oklab = srgb_to_oklab(img_rgb)

    # 3. 初始化误差缓冲区 (带边界 padding 防止越界)
    err_buf = np.zeros((h + 2, w + 2, 3), dtype=np.float32)
    output_rgb = np.zeros((h, w, 3), dtype=np.uint8)

    num_palette = len(palette_oklab)
    p_oklab = palette_oklab  # (N, 3)
    p_rgb = palette_rgb      # (N, 3)

    # 遍历像素 (Serpentine 往复扫描)
    for y in range(h):
        is_reverse = use_serpentine and (y % 2 == 1)
        x_range = range(w - 1, -1, -1) if is_reverse else range(w)

        for x in x_range:
            # 当前像素真实颜色 + 累加扩散误差
            curr_c = img_oklab[y, x] + err_buf[y + 1, x + 1]

            # 寻找 OKLab 空间最近邻方块
            # (N, 3) 快速差值平方和
            diff = p_oklab - curr_c
            dists_sq = np.sum(diff * diff, axis=-1)
            best_idx = int(np.argmin(dists_sq))

            best_oklab = p_oklab[best_idx]
            best_rgb = p_rgb[best_idx]
            output_rgb[y, x] = best_rgb

            # 计算量化误差
            err = curr_c - best_oklab
            err_norm = np.sqrt(np.sum(err * err))

            # 4. 自适应阻断与死区吸收逻辑
            m_edge = edge_mask[y, x]
            m_flat = flat_mask[y, x]

            # 4.1 大面积平坦区死区门限：如果误差不大且处于纯平背景，吸收误差避免蠕虫杂斑
            if m_flat > 0.4 and err_norm < (flat_deadzone * 1.5):
                err = err * (1.0 - m_flat)

            # 4.2 边缘保护调制：五官与线条处阻断扩散 (无抖动保真)
            if m_edge > 0.45:
                eff_weight = 0.0  # 彻底阻断，不向周围扩散
            else:
                eff_weight = dither_weight * (1.0 - 0.9 * m_edge)

            err_diffuse = err * eff_weight

            # 5. 阻尼误差分配 (向右/左及下方扩散)
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


# =============================================================================
# 对比图生成器：原图 vs 处理后图并排拼接
# =============================================================================
def create_comparison_board(
    orig_bgr: np.ndarray,
    processed_rgb: np.ndarray,
    project_name: str,
    color_mode_name: str = "Minecraft 61-Color Flat"
) -> np.ndarray:
    """
    生成原图与处理后图的高清并排横向对比画板
    """
    h, w = orig_bgr.shape[:2]
    orig_rgb = cv2.cvtColor(orig_bgr, cv2.COLOR_BGR2RGB)

    # 创建并排大图 (原图 | 处理后)
    pad = 20
    header_h = 70
    board_w = w * 2 + pad * 3
    board_h = h + header_h + pad * 2

    # 深色现代质感背景
    board = np.full((board_h, board_w, 3), (28, 30, 36), dtype=np.uint8)

    # 放置图像
    y_start = header_h + pad
    x_orig = pad
    x_proc = pad * 2 + w

    board[y_start:y_start + h, x_orig:x_orig + w] = orig_rgb
    board[y_start:y_start + h, x_proc:x_proc + w] = processed_rgb

    # 绘制边框
    cv2.rectangle(board, (x_orig - 1, y_start - 1), (x_orig + w, y_start + h), (70, 75, 90), 1)
    cv2.rectangle(board, (x_proc - 1, y_start - 1), (x_proc + w, y_start + h), (70, 75, 90), 1)

    # 转换为 PIL 绘制清晰文字标题
    pil_img = Image.fromarray(board)
    draw = ImageDraw.Draw(pil_img)

    title_text = f"Project: {project_name} | Mode: {color_mode_name} | Size: {w}x{h}"
    left_sub = "Original Input Image"
    right_sub = "Adaptive Dithered (Edges Crisp + Smooth Blending)"

    # 默认基本字体
    try:
        font_main = ImageFont.load_default()
    except Exception:
        font_main = None

    draw.text((pad, 16), title_text, fill=(240, 242, 245), font=font_main)
    draw.text((x_orig, header_h - 10), left_sub, fill=(180, 185, 195), font=font_main)
    draw.text((x_proc, header_h - 10), right_sub, fill=(90, 210, 140), font=font_main)

    res_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return res_bgr


# =============================================================================
# 单图完整处理与非侵入式输出流水线
# =============================================================================
def run_pipeline_for_image(
    input_path: Path,
    workspace_root: Path,
    dither_weight: float = None,
    edge_threshold: float = None,
    flat_deadzone: float = None
):
    """
    处理单幅图片并保存至独立的 PICTEMP_{project} 目录
    """
    if not input_path.exists():
        raise FileNotFoundError(f"未找到输入图片: {input_path}")

    project_name = input_path.stem
    print(f"\n==================================================")
    print(f"开始处理项目: {project_name}")
    print(f"输入路径: {input_path}")

    # 读取输入图
    img_bgr = cv2.imread(str(input_path))
    if img_bgr is None:
        raise ValueError(f"无法使用 OpenCV 读取图像: {input_path}")

    h, w = img_bgr.shape[:2]
    print(f"图像尺寸: {w}x{h} (折合 {w//128}x{h//128} 张地图画图块)")

    # 载入 61 色平面调色板与 OKLab 坐标
    p_rgb, p_ids = get_flat61_palette()
    p_oklab = srgb_to_oklab(p_rgb)
    print(f"已加载 Minecraft 61色平面基准色板 (共 {len(p_rgb)} 种标准方块色)")

    # 提取参数
    dw = dither_weight if dither_weight is not None else CONFIG["DITHER_WEIGHT"]
    et = edge_threshold if edge_threshold is not None else CONFIG["EDGE_THRESHOLD"]
    fd = flat_deadzone if flat_deadzone is not None else CONFIG["FLAT_DEADZONE"]
    use_serpentine = CONFIG["SERPENTINE"]

    print(f"当前运行参数: DITHER_WEIGHT={dw}, EDGE_THRESHOLD={et}, FLAT_DEADZONE={fd}, SERPENTINE={use_serpentine}")

    t0 = time.time()
    # 执行核心算法
    processed_rgb = process_adaptive_dither(
        img_bgr=img_bgr,
        palette_rgb=p_rgb,
        palette_oklab=p_oklab,
        dither_weight=dw,
        edge_threshold=et,
        flat_deadzone=fd,
        use_serpentine=use_serpentine
    )
    t1 = time.time()
    print(f"自适应量化与抖动处理完成，耗时: {t1 - t0:.2f} 秒")

    # 创建独立的备份输出文件夹 PICTEMP_{project}
    out_dir = workspace_root / f"PICTEMP_{project_name}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 保存单独完整大图
    proc_bgr = cv2.cvtColor(processed_rgb, cv2.COLOR_RGB2BGR)
    proc_path = out_dir / f"{project_name}_processed.png"
    cv2.imwrite(str(proc_path), proc_bgr)
    print(f"[产物1] 完整处理大图已保存: {proc_path}")

    # 2. 保存原图 vs 处理后 对比图
    compare_bgr = create_comparison_board(img_bgr, processed_rgb, project_name)
    compare_path = out_dir / f"{project_name}_compare.png"
    cv2.imwrite(str(compare_path), compare_bgr)
    print(f"[产物2] 高清对比画板已保存: {compare_path}")

    # 验证色彩集合是否 100% 严格符合 61 种平面色
    unique_colors = np.unique(processed_rgb.reshape(-1, 3), axis=0)
    print(f"生成图像包含的有效颜色种数: {len(unique_colors)} / 61 种")

    return {
        "project": project_name,
        "out_dir": str(out_dir),
        "processed_file": str(proc_path),
        "compare_file": str(compare_path),
        "unique_colors": len(unique_colors),
        "time_cost": round(t1 - t0, 2)
    }


# =============================================================================
# CLI 命令行入口
# =============================================================================
def main():
    parser = argparse.ArgumentParser(description="Minecraft 61色平面地图画高质量自适应抖动引擎")
    parser.add_argument("--input", "-i", type=str, help="输入图片路径 (例如 024627DD919/024627DD919.png)")
    parser.add_argument("--dither-weight", "-w", type=float, default=None, help=f"基础抖动强度 (默认: {CONFIG['DITHER_WEIGHT']})")
    parser.add_argument("--edge-threshold", "-e", type=float, default=None, help=f"边缘保护灵敏度 (默认: {CONFIG['EDGE_THRESHOLD']})")
    parser.add_argument("--flat-deadzone", "-d", type=float, default=None, help=f"背景纯色死区门限 (默认: {CONFIG['FLAT_DEADZONE']})")

    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    # 向上寻找 MapArt 工作区根目录
    workspace_root = script_dir.parents[1]

    if args.input:
        in_path = Path(args.input)
        if not in_path.is_absolute():
            in_path = workspace_root / in_path
        run_pipeline_for_image(
            in_path,
            workspace_root,
            dither_weight=args.dither_weight,
            edge_threshold=args.edge_threshold,
            flat_deadzone=args.flat_deadzone
        )
    else:
        print("未指定 --input 参数。您可以在命令行传入 --input path/to/image.png")
        print("示例: python adaptive_dither.py --input 0831034707/0831034707.png")


if __name__ == "__main__":
    main()
