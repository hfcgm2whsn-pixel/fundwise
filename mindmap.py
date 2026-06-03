# -*- coding: utf-8 -*-
"""
思维导图模块

功能：将结构化文本（如 AI 总结）解析并生成从左向右展开的思维导图（PNG 图片）。
依赖：matplotlib（纯 Python，无需系统级 graphviz）
"""

import os
import re
import platform

import matplotlib
matplotlib.use("Agg")  # 无头模式，不弹出窗口

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.font_manager import FontProperties


# ============================================================
# 颜色方案
# ============================================================
ROOT_COLOR = "#1E88E5"
ROOT_FONT_COLOR = "#FFFFFF"

LEVEL1_COLOR = "#43A047"
LEVEL1_FONT_COLOR = "#FFFFFF"

LEVEL2_COLOR = "#FB8C00"
LEVEL2_FONT_COLOR = "#FFFFFF"

EDGE_COLOR = "#999999"

BACKGROUND_COLOR = "#FAFAFA"


# ============================================================
# 中文字体检测
# ============================================================

def _detect_chinese_font():
    """
    自动检测系统中可用的中文字体名称，供 matplotlib 使用。

    优先级：
      1. Mac —— PingFang SC
      2. Windows —— Microsoft YaHei
      3. Linux —— Noto Sans CJK SC

    Returns:
        str: 字体名称。
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        return "PingFang SC"
    elif system == "Windows":
        return "Microsoft YaHei"
    else:  # Linux
        return "Noto Sans CJK SC"


# ============================================================
# 文本解析
# ============================================================

def parse_summary_to_tree(summary_text):
    """
    解析总结文本，提取结构化树形数据。

    识别以 【】 标记的段落标题，将其作为一级节点，
    段落内的每一行作为二级节点。

    Args:
        summary_text (str): AI 生成的总结文本。

    Returns:
        dict: 树形结构字典，格式如下：
            {
                "root": "视频总结",
                "children": [
                    {
                        "label": "视频主题",
                        "children": ["具体内容行1", "具体内容行2"]
                    },
                    ...
                ]
            }
    """
    if not summary_text or not isinstance(summary_text, str):
        return {"root": "视频总结", "children": []}

    # 用正则按 【xxx】 分割文本
    pattern = r"【([^】]+)】"
    parts = re.split(pattern, summary_text)

    tree = {
        "root": "视频总结",
        "children": [],
    }

    # parts 的结构：[前导文本, 标题1, 内容1, 标题2, 内容2, ...]
    # 跳过第一个元素（前导文本，通常为空或简短描述）
    i = 1
    while i < len(parts):
        section_title = parts[i].strip()
        section_content = parts[i + 1].strip() if (i + 1) < len(parts) else ""

        # 将内容按行拆分，过滤空行
        content_lines = [
            line.strip()
            for line in section_content.split("\n")
            if line.strip()
        ]

        # 构建一级节点
        level1_node = {
            "label": section_title,
            "children": [],
        }

        # 构建二级节点
        for line in content_lines:
            # 去除行首的序号或符号（如 "1." "•" "-" "·" 等）
            cleaned = re.sub(r"^[\d]+[.、)\s]+", "", line)
            cleaned = re.sub(r"^[•\-\*\·]\s*", "", cleaned)
            cleaned = cleaned.strip()
            if cleaned:
                level1_node["children"].append(cleaned)

        tree["children"].append(level1_node)
        i += 2

    return tree


# ============================================================
# 树形绘制
# ============================================================

def _get_text_size(text, font_prop, ax):
    """
    计算文本在给定字体下的像素尺寸。

    Args:
        text (str): 要测量的文本。
        font_prop (FontProperties): 字体属性。
        ax (matplotlib.axes.Axes): 用于获取渲染器的坐标轴。

    Returns:
        tuple: (宽度, 高度)，单位为数据坐标。
    """
    renderer = ax.figure.canvas.get_renderer()
    t = ax.text(0, 0, text, fontproperties=font_prop, visible=False)
    bbox = t.get_window_extent(renderer=renderer)
    t.remove()
    # 将像素转换为数据坐标（通过 transform）
    # 这里返回像素尺寸，后续在布局中统一处理
    return bbox.width, bbox.height


def _draw_tree(ax, tree_data, x=0, y=0, width=10, level=0):
    """
    递归绘制树形结构。

    从左向右展开：根节点在左侧，子节点向右展开。
    不同层级使用不同颜色，节点用圆角矩形框表示，
    父子节点之间用线段连接。

    Args:
        ax (matplotlib.axes.Axes): matplotlib 坐标轴对象。
        tree_data (dict): 树形结构数据。
        x (float): 当前节点左上角的 x 坐标。
        y (float): 当前节点中心的 y 坐标。
        width (float): 当前子树分配的总宽度。
        level (int): 当前层级（0=根，1=一级，2=二级）。

    Returns:
        float: 当前子树实际占用的总高度。
    """
    # ---------- 根据层级选择样式 ----------
    if level == 0:
        fill_color = ROOT_COLOR
        font_color = ROOT_FONT_COLOR
        font_size = 16
        box_pad_x = 0.4
        box_pad_y = 0.25
        font_name = _detect_chinese_font()
    elif level == 1:
        fill_color = LEVEL1_COLOR
        font_color = LEVEL1_FONT_COLOR
        font_size = 13
        box_pad_x = 0.3
        box_pad_y = 0.2
        font_name = _detect_chinese_font()
    else:
        fill_color = LEVEL2_COLOR
        font_color = LEVEL2_FONT_COLOR
        font_size = 11
        box_pad_x = 0.25
        box_pad_y = 0.15
        font_name = _detect_chinese_font()

    font_prop = FontProperties(family=font_name, size=font_size)

    # ---------- 获取当前节点标签 ----------
    if level == 0:
        label = tree_data.get("root", "视频总结")
        children = tree_data.get("children", [])
    else:
        label = tree_data.get("label", "")
        children = tree_data.get("children", [])

    # 截断过长标签
    max_label_len = 20 if level == 2 else 30
    if len(label) > max_label_len:
        label = label[: max_label_len - 2] + "..."

    # ---------- 计算节点框尺寸 ----------
    # 用文本大致估算宽度（每个中文字符约等于 font_size 的宽度）
    char_width = font_size * 0.06  # 数据坐标中的近似字符宽度
    text_width = len(label) * char_width
    box_width = text_width + box_pad_x * 2
    box_height = font_size * 0.06 + box_pad_y * 2

    # ---------- 计算子树布局 ----------
    child_spacing = 0.5  # 子节点之间的垂直间距
    child_x = x + box_width + 1.5  # 子节点起始 x（留出连线空间）

    if children:
        # 计算每个子树需要的高度
        child_heights = []
        for child in children:
            if level == 0:
                # 一级节点：估算子树高度
                sub_children = child.get("children", [])
                est_height = box_height + max(len(sub_children), 1) * (box_height + child_spacing)
                child_heights.append(est_height)
            else:
                # 二级节点（叶子）
                child_heights.append(box_height)

        total_children_height = sum(child_heights) + child_spacing * (len(children) - 1)
    else:
        total_children_height = box_height
        child_heights = []

    # ---------- 确定当前节点 y 坐标 ----------
    if children:
        # 当前节点居中于子树
        node_y = y  # y 已经是分配的中心位置
    else:
        node_y = y

    # ---------- 绘制节点框 ----------
    box = patches.FancyBboxPatch(
        (x, node_y - box_height / 2),
        box_width,
        box_height,
        boxstyle="round,pad=0.1",
        facecolor=fill_color,
        edgecolor=EDGE_COLOR,
        linewidth=1.2,
        zorder=3,
    )
    ax.add_patch(box)

    # ---------- 绘制节点文本 ----------
    ax.text(
        x + box_width / 2,
        node_y,
        label,
        fontproperties=font_prop,
        color=font_color,
        ha="center",
        va="center",
        zorder=4,
    )

    # ---------- 绘制子节点和连线 ----------
    if children:
        # 计算子节点的起始 y 位置（从上到下排列）
        current_y = node_y + total_children_height / 2

        for idx, child in enumerate(children):
            child_h = child_heights[idx]
            child_center_y = current_y - child_h / 2

            if level == 0:
                # 一级节点：递归绘制
                _draw_tree(ax, child, child_x, child_center_y, width / len(children), level + 1)
                # 连线：从根节点右边到子节点左边
                child_box_w = len(child.get("label", "")) * (font_size * 0.06) + 0.3 * 2
                ax.plot(
                    [x + box_width, child_x],
                    [node_y, child_center_y],
                    color=EDGE_COLOR,
                    linewidth=1.5,
                    zorder=1,
                )
            else:
                # 二级节点（叶子）：直接绘制
                child_label = child if isinstance(child, str) else child.get("label", "")
                # 截断过长标签
                if len(child_label) > 20:
                    child_label = child_label[:18] + "..."

                leaf_font_size = 11
                leaf_char_width = leaf_font_size * 0.06
                leaf_text_w = len(child_label) * leaf_char_width
                leaf_box_w = leaf_text_w + 0.25 * 2
                leaf_box_h = leaf_font_size * 0.06 + 0.15 * 2

                leaf_box = patches.FancyBboxPatch(
                    (child_x, child_center_y - leaf_box_h / 2),
                    leaf_box_w,
                    leaf_box_h,
                    boxstyle="round,pad=0.08",
                    facecolor=LEVEL2_COLOR,
                    edgecolor=EDGE_COLOR,
                    linewidth=1.0,
                    zorder=3,
                )
                ax.add_patch(leaf_box)

                leaf_font_prop = FontProperties(
                    family=_detect_chinese_font(), size=leaf_font_size
                )
                ax.text(
                    child_x + leaf_box_w / 2,
                    child_center_y,
                    child_label,
                    fontproperties=leaf_font_prop,
                    color=LEVEL2_FONT_COLOR,
                    ha="center",
                    va="center",
                    zorder=4,
                )

                # 连线
                ax.plot(
                    [x + box_width, child_x],
                    [node_y, child_center_y],
                    color=EDGE_COLOR,
                    linewidth=1.2,
                    zorder=1,
                )

            current_y -= child_h + child_spacing

    return total_children_height


def _compute_tree_bounds(tree_data, level=0):
    """
    递归计算树形结构的边界尺寸（用于设置画布大小）。

    Args:
        tree_data (dict): 树形结构数据。
        level (int): 当前层级。

    Returns:
        tuple: (总宽度, 总高度)
    """
    if level == 0:
        label = tree_data.get("root", "视频总结")
        children = tree_data.get("children", [])
        font_size = 16
        char_width = font_size * 0.06
        box_pad_x = 0.4
        box_pad_y = 0.25
    elif level == 1:
        label = tree_data.get("label", "")
        children = tree_data.get("children", [])
        font_size = 13
        char_width = font_size * 0.06
        box_pad_x = 0.3
        box_pad_y = 0.2
    else:
        return (0, 0)

    box_width = len(label) * char_width + box_pad_x * 2
    box_height = font_size * 0.06 + box_pad_y * 2

    if not children:
        return (box_width, box_height)

    child_results = []
    for child in children:
        cw, ch = _compute_tree_bounds(child, level + 1)
        child_results.append((cw, ch))

    # 子树总宽度 = 当前节点宽度 + 间距 + 最大子树宽度
    gap = 1.5
    max_child_width = max(cw for cw, ch in child_results) if child_results else 0
    total_width = box_width + gap + max_child_width

    # 子树总高度 = 所有子树高度之和 + 间距
    child_spacing = 0.5
    total_child_height = sum(ch for cw, ch in child_results) + child_spacing * (len(child_results) - 1)
    total_height = max(box_height, total_child_height)

    return (total_width, total_height)


# ============================================================
# 主入口
# ============================================================

def generate_mindmap(summary_text, output_path="mindmap.png"):
    """
    将 AI 总结文本生成为从左向右展开的思维导图 PNG 图片。

    流程：
      1. 解析文本为树形结构
      2. 使用 matplotlib 绘制树形思维导图
      3. 保存为 PNG 图片

    Args:
        summary_text (str): AI 生成的总结文本，包含 【】 标记的结构。
        output_path (str): 输出图片文件路径，默认 "mindmap.png"。

    Returns:
        str or None: 生成的图片文件绝对路径；解析或绘制失败时返回 None。
    """
    try:
        # 第一步：解析文本为树形结构
        tree_data = parse_summary_to_tree(summary_text)

        # 检查是否有有效内容
        if not tree_data.get("children"):
            print("[generate_mindmap] 警告：未能从文本中解析到有效结构。")
            return None

        # 第二步：计算画布尺寸
        total_width, total_height = _compute_tree_bounds(tree_data)

        # 添加边距
        margin_x = 2.0
        margin_y = 2.0
        fig_width = max(total_width + margin_x * 2, 12)
        fig_height = max(total_height + margin_y * 2, 6)

        # 限制最大尺寸，避免图片过大
        fig_width = min(fig_width, 40)
        fig_height = min(fig_height, 30)

        # 第三步：创建图形并绘制
        fig, ax = plt.subplots(1, 1, figsize=(fig_width, fig_height))
        ax.set_facecolor(BACKGROUND_COLOR)
        fig.patch.set_facecolor(BACKGROUND_COLOR)

        # 关闭坐标轴
        ax.set_xlim(-margin_x, fig_width - margin_x)
        ax.set_ylim(-fig_height / 2, fig_height / 2)
        ax.set_aspect("equal")
        ax.axis("off")

        # 绘制树形结构
        _draw_tree(ax, tree_data, x=-margin_x + 0.5, y=0, width=fig_width - margin_x * 2, level=0)

        # 第四步：保存图片
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # 确保输出路径以 .png 结尾
        if not output_path.lower().endswith(".png"):
            output_path = output_path + ".png"

        plt.savefig(
            output_path,
            dpi=150,
            bbox_inches="tight",
            facecolor=BACKGROUND_COLOR,
            edgecolor="none",
            pad_inches=0.5,
        )
        plt.close(fig)

        return os.path.abspath(output_path)

    except Exception as e:
        print(f"[generate_mindmap] 生成思维导图失败：{e}")
        return None
