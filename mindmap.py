# -*- coding: utf-8 -*-
"""
思维导图模块

功能：将结构化文本（如 AI 总结）解析并生成从左向右展开的思维导图（PNG 图片）。
依赖：graphviz（可选）
"""

import os
import re

# 尝试导入 graphviz
try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False
    print("[mindmap] 提示：graphviz 库不可用，思维导图功能将无法使用。请执行 pip install graphviz。")


# ============================================================
# 颜色方案
# ============================================================
# 根节点 —— 蓝色
ROOT_COLOR = "#4A90D9"
ROOT_FONT_COLOR = "#FFFFFF"

# 一级节点 —— 绿色
LEVEL1_COLOR = "#5CB85C"
LEVEL1_FONT_COLOR = "#FFFFFF"

# 二级节点 —— 橙色
LEVEL2_COLOR = "#F0AD4E"
LEVEL2_FONT_COLOR = "#FFFFFF"

# 边样式 —— 灰色
EDGE_COLOR = "#999999"


def _detect_chinese_font():
    """
    自动检测系统中可用的中文字体路径，供 graphviz 使用。

    优先级：
      1. Mac —— PingFang SC
      2. Windows —— Microsoft YaHei
      3. Linux —— Noto Sans CJK SC / WenQuanYi Micro Hei

    Returns:
        str or None: 字体名称或路径。
    """
    import platform

    system = platform.system()

    if system == "Darwin":  # macOS
        return "PingFang SC"
    elif system == "Windows":
        return "Microsoft YaHei"
    else:  # Linux
        # 检查常见字体路径
        linux_fonts = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        ]
        for fp in linux_fonts:
            if os.path.exists(fp):
                return fp
        return "Noto Sans CJK SC"


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
                "label": "视频总结",
                "children": [
                    {
                        "label": "视频主题",
                        "children": [
                            {"label": "具体内容行1"},
                            {"label": "具体内容行2"},
                        ]
                    },
                    ...
                ]
            }
    """
    # 用正则按 【xxx】 分割文本
    # 匹配模式：【标题】后面的内容直到下一个 【 或文本末尾
    pattern = r"【([^】]+)】"
    parts = re.split(pattern, summary_text)

    tree = {
        "label": "视频总结",
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
                level1_node["children"].append({"label": cleaned})

        tree["children"].append(level1_node)
        i += 2

    return tree


def build_graphviz_graph(tree_data):
    """
    将树形数据构建为 Graphviz 的 Digraph 对象（从左向右展开）。

    Args:
        tree_data (dict): 由 parse_summary_to_tree 返回的树形结构。

    Returns:
        graphviz.Digraph: 构建好的图对象。
    """
    if not GRAPHVIZ_AVAILABLE:
        return None

    # 创建有向图，从左向右展开
    dot = graphviz.Digraph(
        name="mindmap",
        format="png",
        graph_attr={
            "rankdir": "LR",          # 从左向右
            "bgcolor": "#FAFAFA",     # 浅灰背景
            "dpi": "150",             # 分辨率
            "splines": "ortho",       # 正交边
            "nodesep": "0.4",
            "ranksep": "1.0",
            "pad": "0.5",
        },
        node_attr={
            "shape": "box",           # 方形节点
            "style": "rounded,filled",  # 圆角 + 填充
            "fontname": _detect_chinese_font(),
            "fontsize": "14",
            "margin": "0.2,0.1",
        },
        edge_attr={
            "color": EDGE_COLOR,
            "arrowhead": "vee",       # 箭头样式
            "arrowsize": "0.8",
        },
    )

    # ---------- 递归添加节点和边 ----------
    def add_nodes(node, parent_id=None, level=0):
        """
        递归地将树节点添加到图中。

        Args:
            node (dict): 当前树节点。
            parent_id (str or None): 父节点 ID。
            level (int): 当前层级（0=根，1=一级，2=二级）。
        """
        # 生成唯一 ID
        node_id = f"node_{id(node)}_{level}"

        # 根据层级选择颜色
        if level == 0:
            fill_color = ROOT_COLOR
            font_color = ROOT_FONT_COLOR
            font_size = "18"
            pen_width = "2.0"
        elif level == 1:
            fill_color = LEVEL1_COLOR
            font_color = LEVEL1_FONT_COLOR
            font_size = "15"
            pen_width = "1.5"
        else:
            fill_color = LEVEL2_COLOR
            font_color = LEVEL2_FONT_COLOR
            font_size = "13"
            pen_width = "1.0"

        # 截断过长的标签
        label = node.get("label", "")
        if len(label) > 30:
            label = label[:28] + "..."

        # 添加节点
        dot.node(
            node_id,
            label=label,
            fillcolor=fill_color,
            fontcolor=font_color,
            fontsize=font_size,
            penwidth=pen_width,
        )

        # 添加边（从父节点到当前节点）
        if parent_id is not None:
            dot.edge(parent_id, node_id)

        # 递归处理子节点
        children = node.get("children", [])
        for child in children:
            add_nodes(child, parent_id=node_id, level=level + 1)

    # 从根节点开始构建
    add_nodes(tree_data)

    return dot


def generate_mindmap(summary_text, output_path="mindmap.png"):
    """
    将 AI 总结文本生成为从左向右展开的思维导图 PNG 图片。

    流程：
      1. 解析文本为树形结构
      2. 构建 Graphviz 图
      3. 渲染为 PNG 并保存

    Args:
        summary_text (str): AI 生成的总结文本，包含 【】 标记的结构。
        output_path (str): 输出图片文件路径，默认 "mindmap.png"。

    Returns:
        str or None: 生成的图片文件绝对路径；graphviz 不可用时返回 None。
    """
    if not GRAPHVIZ_AVAILABLE:
        print("[generate_mindmap] 错误：graphviz 库不可用，无法生成思维导图。")
        return None

    # 第一步：解析文本为树形结构
    tree_data = parse_summary_to_tree(summary_text)

    # 第二步：构建 Graphviz 图
    dot = build_graphviz_graph(tree_data)
    if dot is None:
        return None

    # 第三步：渲染并保存
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # graphviz.render 会自动添加格式后缀，所以去掉用户给的后缀
    render_path = os.path.splitext(output_path)[0]

    try:
        rendered_file = dot.render(filename=render_path, cleanup=True)
        # rendered_file 可能带 .png 后缀，确保返回正确路径
        if not rendered_file.endswith(".png"):
            rendered_file = rendered_file + ".png"
        return os.path.abspath(rendered_file)
    except Exception as e:
        print(f"[generate_mindmap] 渲染失败：{e}")
        return None
