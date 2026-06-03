# -*- coding: utf-8 -*-
"""
导出工具模块

功能：将文本内容或 HTML 内容导出为 PNG 图片。
依赖：Pillow (PIL), 可选 imgkit / html2image
"""

import os
import platform
import textwrap

# 尝试导入 Pillow
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[export_utils] 提示：Pillow 库不可用，导出图片功能将无法使用。请执行 pip install Pillow。")

# 尝试导入 imgkit
try:
    import imgkit
    IMGKIT_AVAILABLE = True
except ImportError:
    IMGKIT_AVAILABLE = False

# 尝试导入 html2image
try:
    from html2image import Html2Image
    H2I_AVAILABLE = True
except ImportError:
    H2I_AVAILABLE = False


def _detect_chinese_font():
    """
    自动检测系统中可用的中文字体路径。

    优先级：
      1. Mac —— PingFang SC
      2. Windows —— Microsoft YaHei
      3. Linux —— Noto Sans CJK SC / WenQuanYi Micro Hei

    Returns:
        str or None: 找到的字体文件路径，未找到则返回 None。
    """
    system = platform.system()

    # 候选字体列表（按优先级排列）
    candidates = []

    if system == "Darwin":  # macOS
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
        ]
    elif system == "Windows":
        candidates = [
            "C:/Windows/Fonts/msyh.ttc",       # Microsoft YaHei
            "C:/Windows/Fonts/msyhbd.ttc",      # Microsoft YaHei Bold
            "C:/Windows/Fonts/simhei.ttf",      # SimHei
            "C:/Windows/Fonts/simsun.ttc",      # SimSun
        ]
    else:  # Linux
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            return path

    # 未找到已知路径，尝试 Pillow 自带的字体回退
    return None


def _get_font(size=20):
    """
    获取指定大小的字体对象，优先使用中文字体。

    Args:
        size (int): 字体大小，默认 20。

    Returns:
        PIL.ImageFont.FreeTypeFont or ImageFont: 字体对象。
    """
    if not PIL_AVAILABLE:
        return None

    font_path = _detect_chinese_font()
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    # 回退到 Pillow 默认字体
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def export_text_to_image(text_content, title="", width=800, bg_color="white", text_color="black"):
    """
    将文本内容渲染为 PNG 图片。

    自动处理换行，支持自定义标题、宽度、背景色和文字颜色。

    Args:
        text_content (str): 要渲染的文本内容。
        title (str): 可选标题，显示在图片顶部。
        width (int): 图片宽度（像素），默认 800。
        bg_color (str): 背景颜色，默认 "white"。
        text_color (str): 文字颜色，默认 "black"。

    Returns:
        bytes or None: PNG 图片的 bytes 数据；Pillow 不可用时返回 None。
    """
    if not PIL_AVAILABLE:
        print("[export_text_to_image] 错误：Pillow 库不可用，无法导出图片。")
        return None

    # ---------- 参数准备 ----------
    padding = 30          # 内边距
    title_font_size = 28
    body_font_size = 18
    line_spacing = 8      # 行间距

    title_font = _get_font(title_font_size)
    body_font = _get_font(body_font_size)

    # ---------- 自动换行 ----------
    usable_width = width - 2 * padding

    def wrap_text(text, font, max_width):
        """对单行文本进行自动换行，返回多行列表。"""
        lines = []
        for paragraph in text.split("\n"):
            if paragraph.strip() == "":
                lines.append("")
                continue
            current_line = ""
            for char in paragraph:
                test_line = current_line + char
                bbox = font.getbbox(test_line)
                if bbox[2] - bbox[0] > max_width and current_line:
                    lines.append(current_line)
                    current_line = char
                else:
                    current_line = test_line
            if current_line:
                lines.append(current_line)
        return lines

    body_lines = wrap_text(text_content, body_font, usable_width)

    # ---------- 计算图片高度 ----------
    # 先测量一行的高度
    dummy_bbox = body_font.getbbox("测试Ag")
    body_line_height = dummy_bbox[3] - dummy_bbox[1] + line_spacing

    total_height = padding  # 顶部内边距

    if title:
        title_bbox = title_font.getbbox(title)
        title_line_height = title_bbox[3] - title_bbox[1] + line_spacing
        total_height += title_line_height + 10  # 标题 + 间距

    total_height += body_line_height * len(body_lines) + padding  # 正文 + 底部内边距

    # ---------- 绘制图片 ----------
    img = Image.new("RGB", (width, total_height), bg_color)
    draw = ImageDraw.Draw(img)

    y_cursor = padding

    # 绘制标题
    if title:
        draw.text((padding, y_cursor), title, fill=text_color, font=title_font)
        title_bbox = title_font.getbbox(title)
        y_cursor += (title_bbox[3] - title_bbox[1]) + line_spacing + 10

    # 绘制正文
    for line in body_lines:
        draw.text((padding, y_cursor), line, fill=text_color, font=body_font)
        line_bbox = body_font.getbbox(line) if line else body_font.getbbox("测试Ag")
        y_cursor += (line_bbox[3] - line_bbox[1]) + line_spacing

    # ---------- 输出 ----------
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def export_html_to_image(html_content, width=800):
    """
    将 HTML 内容渲染为 PNG 图片。

    优先使用 imgkit，其次 html2image，最后降级为纯文本图片。

    Args:
        html_content (str): HTML 字符串。
        width (int): 图片宽度（像素），默认 800。

    Returns:
        bytes or None: PNG 图片的 bytes 数据；所有库均不可用时返回 None。
    """
    # ---- 方式 1：使用 imgkit ----
    if IMGKIT_AVAILABLE:
        try:
            options = {
                "format": "png",
                "width": width,
                "encoding": "UTF-8",
                "enable-local-file-access": None,
            }
            img_bytes = imgkit.from_string(html_content, False, options=options)
            return img_bytes
        except Exception as e:
            print(f"[export_html_to_image] imgkit 渲染失败：{e}，尝试其他方式。")

    # ---- 方式 2：使用 html2image ----
    if H2I_AVAILABLE:
        try:
            hti = Html2Image(output_path="/tmp", size=(width, 600))
            # html2image 需要将 html 写入文件
            html_path = os.path.join("/tmp", "_temp_export.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            screenshots = hti.screenshot(html_file=html_path, save_as="_temp_export.png")
            if screenshots and os.path.exists(screenshots[0]):
                with open(screenshots[0], "rb") as f:
                    img_bytes = f.read()
                # 清理临时文件
                try:
                    os.remove(html_path)
                    os.remove(screenshots[0])
                except Exception:
                    pass
                return img_bytes
        except Exception as e:
            print(f"[export_html_to_image] html2image 渲染失败：{e}，尝试降级方案。")

    # ---- 方式 3：降级为纯文本图片 ----
    print("[export_html_to_image] 提示：imgkit / html2image 均不可用，降级为纯文本图片。")
    # 简单去除 HTML 标签，提取纯文本
    import re
    plain_text = re.sub(r"<[^>]+>", "", html_content)
    plain_text = plain_text.strip()
    return export_text_to_image(plain_text, title="", width=width)
