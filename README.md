# Minecraft MapArt Preprocessor & Adaptive Dither Pipeline
### Minecraft 61色平面地图画高质量自适应抖动优化与切片工具

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Minecraft](https://img.shields.io/badge/Minecraft-MapArt-green.svg)](https://minecraft.net/)

专为 Minecraft 地图画创作者打造的高性能图像前置处理工具箱。通过 **OKLab 感知色彩空间**、**S 型往复阻尼误差扩散**、**Scharr 梯度五官边缘保护** 与 **局部方差背景死区去噪** 等复合算法，彻底解决传统误差扩散算法在 Minecraft 极受限色板下导致的**“背景蠕虫噪点多”**、**“人脸五官暗线模糊”**与**“大面积色偏”**等痛点。

---

## 🌟 核心痛点与算法创新

| 传统算法痛点 (如标准 Floyd-Steinberg) | 本项目自适应优化方案 |
| :--- | :--- |
| **纯色/肤色背景蠕虫杂斑**：有限离散色板导致误差持续累积，在平滑过渡区域反复跳跃形成棋盘与蠕虫状高频噪点。 | **局部方差死区门限过滤**：通过统计局部像素离散度，在平坦低方差区域切断误差扩散，锁定纯净大色块。 |
| **面部五官与线条被色差吞噬**：误差跨越边缘无差别传导，导致睫毛、发丝、唇线等暗线细节模糊断裂。 | **Scharr 梯度暗线保真保护**：检测边缘梯度并在高对比度轮廓处阻断误差注入，确保人物五官锐利清晰。 |
| **传统 RGB 欧氏距离色偏**：人眼对不同颜色敏感度不同，传统算法容易将微妙阴影量化为杂色。 | **OKLab 感知色彩空间**：采用感知均匀色彩模型进行最近邻匹配，实现视觉真实感最大化。 |
| **单向扫描带来的对角线纹理**：传统从左至右扫描会产生明显的对角线走针倾斜杂纹。 | **S 型往复阻尼扩散 (Serpentine)**：奇数行从左向右、偶数行从右向左交替往复，配合阻尼系数消除方向性杂斑。 |

---

## 🏗️ 架构设计与模块分工

系统采用模块化面向对象（OOP）架构，各功能类高度内聚、职责单一：

```text
prep-slopecraft-image/
├── scripts/
│   ├── main.py            # 统一入口 (支持 CLI 参数与全中文交互式菜单)
│   ├── config.py          # 全局配置中心 (超参数、61基色定义、网格规格)
│   ├── pipeline.py        # PipelineManager (统筹两阶段模式调度与文件落盘)
│   ├── dither_engine.py   # AdaptiveDitherEngine (OKLab 往复阻尼抖动核心循环)
│   ├── extractor.py       # FeatureExtractor (边缘提取与平坦掩膜计算)
│   ├── palette.py         # PaletteManager (61色平面调色板与色彩空间映射)
│   ├── slicer.py          # ImageSlicer (128x128 纵向优先列切片引擎)
│   └── adaptive_dither.py # 独立原型脚本 (供技术参考)
├── presets/               # 配套 SlopeCraft 61色平面色板预设文件
│   └── config_for_slopecraft.sc_preset_json
├── docs/                  # 深度算法推导与重构记录
│   └── session_notes.md
├── requirements.txt       # Python 依赖清单
└── SKILL.md               # AI Agent 自动化工作流与运行规范
```

---

## 🚀 快速开始

### 1. 环境准备

推荐 Python 3.9+ 环境，安装核心依赖：
```bash
pip install -r requirements.txt
```

### 2. 核心模式说明

* **模式 1：直接切片模式 (`--mode 1`)**
  * 保持 100% 原始像素与色彩，无损切块为 128x128 纵向优先子图。适用于已由像素画师精修的原画。
* **模式 2：保真自适应优化 + 切片模式 (`--mode 2`，默认推荐)**
  * 执行 OKLab 感知抖动、线条保真与背景去噪，生成严格匹配 Minecraft 61 色平面基色的处理大图，并自动进行切块。

### 3. 运行方式

#### 方式 A：命令行直接运行 (批处理推荐)
```bash
# 推荐：模式 2 自动优化并切片
python scripts/main.py --input "path/to/your_image.png" --mode 2

# 模式 1：纯切片模式
python scripts/main.py --input "path/to/your_image.png" --mode 1
```

#### 方式 B：交互式控制台菜单
直接运行不带参数即可进入友好的控制台菜单：
```bash
python scripts/main.py
```
根据终端引导输入 `[1]` 或 `[2]`，直接拖入或粘贴图片路径即可。

---

## 📂 成果目录与 Windows 自然排序规范

所有生成产物统一自动归档至 `PICS/<project_name>/`。在 Windows 资源管理器默认“按名称升序”排列下，呈现完美阅读顺序：

```text
PICS/<project_name>/
├── <project_name>.png            # ① 原始输入图像副本 (文件名严格保持原样)
├── <project_name>.processed.png  # ② 61色处理后大图 (Windows自然排序紧跟原图正后方)
├── <project_name>_0.png          # ③ 128x128 纵向优先切片 0 (排在所有大图后面)
├── <project_name>_1.png          # ④ 128x128 纵向优先切片 1
└── ...
```

---

## 🛠️ 与 SlopeCraft 协同制作地图画闭环

1. **运行本工具**：对目标原图执行模式 2 处理，得到 `<project>.processed.png` 与切片；
2. **打开 SlopeCraft**：
   - 模式选择：**平面地图画 (Flat MapArt)**；
   - 加载预设：载入本项目 `presets/config_for_slopecraft.sc_preset_json`（61 种基础颜色全开）；
   - 抖动算法：选择 **无抖动 (No Dithering / dither 0)**（因为图像已在本工具中完成高保真预抖动处理）；
3. **一键导出**：完美 1:1 还原色彩，导出为 `.litematic` 投影文件或直接生成建筑结构！

---

## ⚙️ 超参数微调指南 (`config.py`)

如需针对特定图像风格微调效果，可在 `scripts/config.py` 修改默认值，或在命令行通过参数动态覆盖：

* `--dither-weight`（默认 `0.85`）：全局抖动强度。调大（如 0.92）色彩过渡更丰富；调小（如 0.75）色块感更强。
* `--edge-threshold`（默认 `0.22`）：边缘识别灵敏度。调小（如 0.16）保护更微弱的发丝与面部暗线。
* `--flat-deadzone`（默认 `0.018`）：平坦区死区门限。调大（如 0.025）背景更纯净，绝对杜绝杂点。
* `--no-serpentine`：关闭 S 型往复，改用单向传统扫描。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。欢迎 Star、Issue 与 Pull Request！
