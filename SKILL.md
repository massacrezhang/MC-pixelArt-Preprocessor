---
name: prep-slopecraft-image
description: Minecraft MapArt 图像预处理与自适应抖动优化工具箱。支持纯切片模式与 61 色平面高质量自适应抖动模式（OKLab感知空间、五官暗线保真、平坦背景去噪），产物按 Windows 自然排序统一归档至 PICS/<project_name>/。
---

# MapArt 图像预处理与自适应优化工作流规范

本技能用于为 Minecraft 地图画制作提供标准化的前端图像处理与切片支持。集成面向对象架构，通过统一入口 `main.py` 调度两阶段处理模式，并将结果归档至 `PICS/<project_name>/`。

## 统一环境要求

必须使用统一虚拟环境解释器执行：
```powershell
& "D:\Software\miniforge3\envs\pymc\python.exe" "prep-slopecraft-image/scripts/main.py" [参数]
```

---

## 核心模式说明

### 模式 1：直接切片模式 (`--mode 1`)
- **适用场景**：原画已经过像素画精修或不需要重新调色，仅需快速切块。
- **行为**：保持 100% 原始色彩与像素，原样复制原图到 `PICS/{project}/{project}.png`，并直接裁切为 128x128 纵向优先子图。

### 模式 2：保真优化 + 切片模式 (`--mode 2`，默认推荐)
- **适用场景**：全彩原画、人物插画、风景图需转化为 Minecraft 61色平面地图画。
- **行为**：
  1. 复制保留原始未修改图片；
  2. 采用 **OKLab 感知色彩空间** 结合 **S型往复阻尼误差扩散** 进行抖动混色；
  3. **五官与线条保真（辅助保护）**：在眼睛、睫毛、发丝、唇线处阻断色差冲刷，保持纯净锐利线条；
  4. **大平坦背景去噪**：采用局部方差死区门限过滤，杜绝纯色背景蠕虫状噪点；
  5. 生成 100% 匹配 61 色平面标准色的处理大图 `{project}.processed.png`；
  6. 对处理后大图裁切为 128x128 纵向优先子图。

---

## 成果目录与 Windows 自然排序规范

所有产物统一存放在 `PICS/<project_name>/` 中，在 Windows 资源管理器按名称升序排列下呈现如下顺序：

```text
PICS/<project_name>/
├── <project_name>.png            # ① 原始输入图像副本 (文件名严格保持原样)
├── <project_name>.processed.png  # ② 处理后大图 (仅模式 2，Windows排序紧跟原图正后方)
├── <project_name>_0.png          # ③ 128x128 纵向优先子图 0 (排在所有大图后面)
├── <project_name>_1.png          # ④ 128x128 纵向优先子图 1
└── ...
```

---

## 常用运行命令

### 1. 命令行直接执行

```powershell
# 推荐：模式 2 自动优化并切片
& "D:\Software\miniforge3\envs\pymc\python.exe" "prep-slopecraft-image/scripts/main.py" --input "0831034707/0831034707.png" --mode 2

# 模式 1 纯切片
& "D:\Software\miniforge3\envs\pymc\python.exe" "prep-slopecraft-image/scripts/main.py" --input "0831034707/0831034707.png" --mode 1
```

### 2. 交互式菜单执行
若不带 `--input` 参数直接启动，将进入控制台交互模式：
```powershell
& "D:\Software\miniforge3\envs\pymc\python.exe" "prep-slopecraft-image/scripts/main.py"
```
根据终端提示选择模式 `[1]` 或 `[2]`，直接粘贴或拖入图片路径即可。

---

## 参数微调指导 (`config.py`)

如需针对特定图像微调算法效果，可编辑 `prep-slopecraft-image/scripts/config.py` 或在命令行通过参数动态覆盖：

* `--dither-weight`（默认 `0.85`）：全局抖动强度。调大（如 0.92）渐变更柔和；调小（如 0.75）偏色块感。
* `--edge-threshold`（默认 `0.22`）：边缘识别灵敏度。调小（如 0.16）保护更多细微发丝与暗线。
* `--flat-deadzone`（默认 `0.018`）：平坦区死区门限。调大（如 0.025）背景更纯净绝对无杂点。
* `--no-serpentine`：关闭 S 型扫描，改用传统单向扫描。
