# -*- coding: utf-8 -*-
"""
视频/图文链接解析模块
支持识别和解析小红书、抖音、B站、微信公众号等平台的链接内容
提取标题、正文文字等信息，供 AI 模块进行内容总结和分析
"""

import re
import json
import logging
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

# ==================== 日志配置 ====================

logger = logging.getLogger(__name__)

# ==================== 常量配置 ====================

# 请求超时时间（秒）
REQUEST_TIMEOUT = 15

# 通用请求头，模拟浏览器访问
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

# 小红书专用请求头
XHS_HEADERS = {
    **HEADERS,
    "Referer": "https://www.xiaohongshu.com/",
}

# 抖音专用请求头
DOUYIN_HEADERS = {
    **HEADERS,
    "Referer": "https://www.douyin.com/",
}

# B站专用请求头
BILIBILI_HEADERS = {
    **HEADERS,
    "Referer": "https://www.bilibili.com/",
}

# 微信公众号专用请求头
WECHAT_HEADERS = {
    **HEADERS,
    "Referer": "https://mp.weixin.qq.com/",
}

# 平台域名匹配规则
PLATFORM_RULES = [
    {
        "name": "小红书",
        "platform": "xiaohongshu",
        "patterns": [
            r"xiaohongshu\.com",
            r"xhslink\.com",
        ],
        "default_type": "图文",
    },
    {
        "name": "抖音",
        "platform": "douyin",
        "patterns": [
            r"douyin\.com",
            r"iesdouyin\.com",
        ],
        "default_type": "视频",
    },
    {
        "name": "B站",
        "platform": "bilibili",
        "patterns": [
            r"bilibili\.com",
            r"b23\.tv",
        ],
        "default_type": "视频",
    },
    {
        "name": "微信公众号",
        "platform": "wechat",
        "patterns": [
            r"mp\.weixin\.qq\.com",
            r"weixin\.qq\.com",
        ],
        "default_type": "图文",
    },
]

# 需要移除的 HTML 标签（广告、导航、页脚等无关内容）
REMOVE_TAGS = [
    "script", "style", "nav", "footer", "header",
    "aside", "iframe", "noscript", "svg",
]

# 需要移除的 CSS 类名关键词（广告和无关内容）
REMOVE_CLASS_KEYWORDS = [
    "ad", "ads", "advert", "banner", "sidebar",
    "footer", "header", "nav", "menu", "comment",
    "related", "recommend", "share", "social",
    "popup", "modal", "cookie", "tracking",
]


# ==================== 工具函数 ====================

def _safe_request(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = REQUEST_TIMEOUT,
    encoding: str = "utf-8",
) -> Optional[str]:
    """
    安全的 HTTP GET 请求封装，统一处理网络异常

    Args:
        url: 请求地址
        headers: 自定义请求头，为空时使用通用请求头
        timeout: 超时时间（秒）
        encoding: 响应编码

    Returns:
        响应文本，请求失败返回 None
    """
    req_headers = headers or HEADERS

    try:
        resp = requests.get(
            url,
            headers=req_headers,
            timeout=timeout,
            allow_redirects=True,
        )
        resp.encoding = encoding

        if resp.status_code == 200:
            return resp.text

        logger.warning(
            "请求 %s 返回状态码 %d", url, resp.status_code
        )
        return None

    except requests.exceptions.Timeout:
        logger.warning("请求 %s 超时", url)
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("请求 %s 连接失败", url)
        return None
    except requests.RequestException as e:
        logger.warning("请求 %s 异常: %s", url, e)
        return None


def _clean_html(html: str) -> str:
    """
    清洗 HTML 内容，移除无关标签和元素，提取纯文本

    Args:
        html: 原始 HTML 文本

    Returns:
        清洗后的纯文本
    """
    soup = BeautifulSoup(html, "lxml")

    # 移除不需要的标签
    for tag_name in REMOVE_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 移除含有广告/无关关键词 class 的元素
    for tag in soup.find_all(True):
        class_attr = tag.get("class", [])
        if isinstance(class_attr, str):
            class_attr = [class_attr]
        for keyword in REMOVE_CLASS_KEYWORDS:
            if any(keyword.lower() in cls.lower() for cls in class_attr):
                tag.decompose()
                break

    # 提取文本并清理空白
    text = soup.get_text(separator="\n")

    # 合并多个连续空行为单个空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 移除行首行尾空白
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)

    return text.strip()


def _extract_title(html: str) -> str:
    """
    从 HTML 中提取页面标题

    优先从 <title> 标签提取，其次尝试 og:title 或 h1 标签

    Args:
        html: HTML 文本

    Returns:
        页面标题，提取失败返回空字符串
    """
    soup = BeautifulSoup(html, "lxml")

    # 尝试 og:title（社交媒体分享标题，通常更准确）
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    # 尝试 <title> 标签
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title = title_tag.string.strip()
        # 去除常见的后缀（如 " - 小红书"、" | B站" 等）
        title = re.split(r"\s*[-_|]\s*(?:小红书|B站|bilibili|抖音|微信公众号|微信文章)\s*$", title)[0]
        return title.strip()

    # 尝试 h1 标签
    h1_tag = soup.find("h1")
    if h1_tag:
        return h1_tag.get_text(strip=True)

    return ""


def _extract_meta_description(html: str) -> str:
    """
    从 HTML 中提取 meta description

    Args:
        html: HTML 文本

    Returns:
        描述文本
    """
    soup = BeautifulSoup(html, "lxml")

    # 尝试 og:description
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        return og_desc["content"].strip()

    # 尝试标准 meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        return meta_desc["content"].strip()

    return ""


def _normalize_url(url: str) -> str:
    """
    标准化 URL，确保格式正确

    Args:
        url: 原始 URL

    Returns:
        标准化后的 URL
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _extract_json_from_script(html: str, var_name: str = "") -> Optional[dict]:
    """
    从 HTML 的 <script> 标签中提取 JSON 数据

    许多平台会在页面中嵌入 JSON 数据（如 SSR 数据），此函数用于提取。

    Args:
        html: HTML 文本
        var_name: 变量名关键词，用于定位目标 script 标签

    Returns:
        解析后的字典，失败返回 None
    """
    soup = BeautifulSoup(html, "lxml")

    for script in soup.find_all("script"):
        script_text = script.string
        if not script_text:
            continue

        # 如果指定了变量名，只检查包含该关键词的 script
        if var_name and var_name not in script_text:
            continue

        # 尝试匹配 JSON 对象
        # 匹配模式：变量 = {...} 或直接 {...}
        patterns = [
            re.compile(r'(?:=|:)\s*(\{[^;]*\})\s*[;,]?', re.DOTALL),
            re.compile(r'(\{["\'][\s\S]*?"\s*:\s*[\s\S]*?\})', re.DOTALL),
        ]

        for pattern in patterns:
            match = pattern.search(script_text)
            if match:
                try:
                    data = json.loads(match.group(1))
                    return data
                except (json.JSONDecodeError, AttributeError):
                    continue

    return None


# ==================== 平台识别 ====================

def detect_platform(url: str) -> Dict[str, str]:
    """
    识别链接所属平台和内容类型

    通过 URL 域名匹配来判断平台，并根据 URL 路径特征判断内容类型。

    Args:
        url: 待识别的链接

    Returns:
        字典格式：
        {
            "platform": "平台标识（xiaohongshu/douyin/bilibili/wechat/unknown）",
            "platform_name": "平台中文名",
            "type": "内容类型（视频/图文/unknown）"
        }
    """
    url = _normalize_url(url)
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    path = parsed.path or ""

    result = {
        "platform": "unknown",
        "platform_name": "其他",
        "type": "unknown",
    }

    # 遍历平台规则进行匹配
    for rule in PLATFORM_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, hostname, re.IGNORECASE):
                result["platform"] = rule["platform"]
                result["platform_name"] = rule["name"]
                result["type"] = rule["default_type"]

                # 根据路径特征细化内容类型
                result["type"] = _detect_content_type(
                    rule["platform"], path, url
                )
                return result

    return result


def _detect_content_type(platform: str, path: str, url: str) -> str:
    """
    根据平台和 URL 路径特征判断具体的内容类型

    Args:
        platform: 平台标识
        path: URL 路径
        url: 完整 URL

    Returns:
        内容类型（"视频" / "图文" / "unknown"）
    """
    if platform == "xiaohongshu":
        # 小红书笔记路径通常包含 /explore/ 或 /discovery/item/
        if re.search(r"/(explore|discovery/item|note)", path):
            return "图文"
        return "图文"

    elif platform == "douyin":
        # 抖音视频路径通常包含 /video/
        if "/video/" in path:
            return "视频"
        # 抖音图文路径
        if "/note/" in path:
            return "图文"
        return "视频"

    elif platform == "bilibili":
        # B站视频路径通常包含 /video/BV 或 /video/av
        if re.search(r"/video/(BV[\w]+|av\d+)", path):
            return "视频"
        # B站专栏文章
        if "/read/" in path or "/article" in path:
            return "图文"
        return "视频"

    elif platform == "wechat":
        # 微信公众号文章通常是 /s/ 开头的短链接
        if re.search(r"/s/[a-zA-Z0-9_]+", path):
            return "图文"
        return "图文"

    return "unknown"


# ==================== 小红书笔记解析 ====================

def parse_xiaohongshu(url: str) -> Dict:
    """
    解析小红书笔记链接，提取标题和正文内容

    小红书页面通常通过 SSR 渲染数据，笔记内容嵌入在页面的
    script 标签中。本函数尝试多种方式提取内容。

    Args:
        url: 小红书笔记链接

    Returns:
        字典格式：
        {
            "platform": "xiaohongshu",
            "type": "图文",
            "title": "笔记标题",
            "content": "笔记正文内容",
            "success": True/False,
            "message": "错误信息（失败时）"
        }
    """
    result = {
        "platform": "xiaohongshu",
        "type": "图文",
        "title": "",
        "content": "",
        "success": False,
        "message": "",
    }

    url = _normalize_url(url)

    # 请求页面
    html = _safe_request(url, headers=XHS_HEADERS)
    if not html:
        result["message"] = "无法访问小红书页面，可能链接已失效或受到反爬限制"
        return result

    # 提取标题
    result["title"] = _extract_title(html)

    # 方式一：尝试从 SSR 数据中提取笔记内容
    # 小红书通常将笔记数据嵌入在 window.__INITIAL_STATE__ 中
    content_text = _extract_xhs_from_ssr(html)

    # 方式二：尝试从 meta 标签提取描述
    if not content_text:
        content_text = _extract_meta_description(html)

    # 方式三：从页面正文中提取
    if not content_text:
        content_text = _extract_xhs_from_body(html)

    if content_text:
        result["content"] = content_text
        result["success"] = True
    else:
        result["message"] = (
            "成功访问小红书页面，但未能提取到笔记内容。"
            "可能原因：笔记需要登录查看、笔记已被删除、或触发了反爬机制。"
        )

    return result


def _extract_xhs_from_ssr(html: str) -> str:
    """
    从小红书 SSR 数据中提取笔记内容

    小红书页面通常包含 window.__INITIAL_STATE__ 变量，
    其中存储了笔记的完整数据。

    Args:
        html: 页面 HTML

    Returns:
        提取到的文本内容
    """
    soup = BeautifulSoup(html, "lxml")

    for script in soup.find_all("script"):
        script_text = script.string
        if not script_text or "__INITIAL_STATE__" not in script_text:
            continue

        # 尝试提取 JSON 数据
        try:
            # 匹配 __INITIAL_STATE__= 后面的 JSON
            match = re.search(
                r'__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*$',
                script_text,
                re.DOTALL,
            )
            if not match:
                continue

            # 清理 JSON 中的 undefined 值（JavaScript 特有）
            json_str = match.group(1)
            json_str = re.sub(r'\bundefined\b', 'null', json_str)

            data = json.loads(json_str)

            # 尝试从数据结构中提取笔记内容
            # 路径可能因版本不同而变化，尝试多种路径
            note_data = (
                data.get("note", {})
                .get("noteDetailMap", {})
            )

            if note_data:
                # 获取第一个笔记的数据
                first_key = next(iter(note_data), None)
                if first_key:
                    note_info = (
                        note_data[first_key]
                        .get("note", {})
                    )
                    if note_info:
                        title = note_info.get("title", "")
                        desc = note_info.get("desc", "")
                        parts = []
                        if title:
                            parts.append(title)
                        if desc:
                            parts.append(desc)

                        # 提取图片描述
                        image_list = note_info.get("imageList", [])
                        for img in image_list:
                            img_desc = img.get("info", {}).get("desc", "")
                            if img_desc:
                                parts.append(f"[图片: {img_desc}]")

                        return "\n".join(parts) if parts else ""

        except (json.JSONDecodeError, KeyError, TypeError, StopIteration):
            continue

    return ""


def _extract_xhs_from_body(html: str) -> str:
    """
    从小红书页面正文中提取笔记内容

    当 SSR 数据提取失败时，尝试从页面 DOM 结构中提取。

    Args:
        html: 页面 HTML

    Returns:
        提取到的文本内容
    """
    soup = BeautifulSoup(html, "lxml")

    # 尝试查找笔记内容容器
    # 小红书的正文通常在特定的 class 容器中
    content_selectors = [
        {"class_": "note-text"},
        {"class_": "desc"},
        {"class_": "content"},
        {"class_": "note-content"},
        {"attrs": {"data-v": True}},  # Vue 组件
    ]

    for selector in content_selectors:
        elements = soup.find_all("div", **selector)
        for elem in elements:
            text = elem.get_text(strip=True)
            if len(text) > 20:  # 过滤掉太短的内容
                return text

    # 兜底：提取页面主要文本内容
    return _clean_html(html)


# ==================== 抖音视频解析 ====================

def parse_douyin(url: str) -> Dict:
    """
    解析抖音视频链接，提取标题和描述信息

    注意：抖音对视频内容有较强的反爬保护。
    本函数尝试从页面中提取视频标题和描述文字，
    但完整的视频内容提取需要语音转文字 API（ASR），
    这部分功能留待后续扩展。

    Args:
        url: 抖音视频链接

    Returns:
        字典格式：
        {
            "platform": "douyin",
            "type": "视频",
            "title": "视频标题",
            "content": "视频描述/提示信息",
            "success": True/False,
            "message": "错误信息（失败时）"
        }
    """
    result = {
        "platform": "douyin",
        "type": "视频",
        "title": "",
        "content": "",
        "success": False,
        "message": "",
    }

    url = _normalize_url(url)

    # 请求页面
    html = _safe_request(url, headers=DOUYIN_HEADERS)
    if not html:
        result["message"] = "无法访问抖音页面，可能链接已失效或受到反爬限制"
        return result

    # 提取标题
    result["title"] = _extract_title(html)

    # 尝试从 SSR 数据中提取视频描述
    content_text = _extract_douyin_from_ssr(html)

    # 尝试从 meta 标签提取描述
    if not content_text:
        content_text = _extract_meta_description(html)

    if content_text:
        result["content"] = content_text
        result["success"] = True
        result["message"] = (
            "已提取到视频标题和描述信息。"
            "注意：完整的视频内容需要语音转文字功能，当前仅支持提取文字描述。"
        )
    else:
        # 即使没有提取到详细内容，如果有标题也算部分成功
        if result["title"]:
            result["success"] = True
            result["content"] = f"视频标题：{result['title']}"
            result["message"] = (
                "仅提取到视频标题，未能获取详细描述。"
                "抖音对内容有较强的反爬保护，完整内容提取需要语音转文字功能。"
            )
        else:
            result["message"] = (
                "无法提取抖音视频内容。"
                "可能原因：视频需要登录查看、触发了反爬机制、或链接已失效。"
                "建议：可以直接粘贴视频的文字描述或字幕内容进行分析。"
            )

    return result


def _extract_douyin_from_ssr(html: str) -> str:
    """
    从抖音 SSR 数据中提取视频描述

    抖音页面通常在 <script id="RENDER_DATA"> 中嵌入 JSON 数据。

    Args:
        html: 页面 HTML

    Returns:
        提取到的描述文本
    """
    soup = BeautifulSoup(html, "lxml")

    # 抖音通常使用 RENDER_DATA 脚本标签
    for script in soup.find_all("script"):
        script_id = script.get("id", "")
        script_text = script.string or ""

        # 匹配 RENDER_DATA
        if "RENDER_DATA" in script_id or "renderData" in script_text:
            try:
                # RENDER_DATA 的值通常是 URL 编码的 JSON
                match = re.search(
                    r'(?:RENDER_DATA|renderData)\s*=\s*["\'](.+?)["\']',
                    script_text,
                )
                if not match:
                    continue

                from urllib.parse import unquote
                json_str = unquote(match.group(1))
                json_str = re.sub(r'\bundefined\b', 'null', json_str)

                data = json.loads(json_str)

                # 尝试提取视频描述
                desc = ""
                # 路径一：直接在顶层
                if isinstance(data, dict):
                    desc = data.get("desc", "")

                # 路径二：嵌套在 detail 中
                if not desc:
                    for key, val in data.items():
                        if isinstance(val, dict):
                            desc = (
                                val.get("detail", {})
                                .get("desc", "")
                            )
                            if desc:
                                break

                if desc:
                    return desc

            except (json.JSONDecodeError, KeyError, TypeError):
                continue

    return ""


# ==================== B站视频解析 ====================

def parse_bilibili(url: str) -> Dict:
    """
    解析B站视频链接，提取标题、简介和分P标题

    B站的视频简介通常可以通过页面直接获取，
    但视频弹幕和字幕需要额外接口。

    Args:
        url: B站视频链接

    Returns:
        字典格式：
        {
            "platform": "bilibili",
            "type": "视频",
            "title": "视频标题",
            "content": "视频简介/提示信息",
            "success": True/False,
            "message": "错误信息（失败时）"
        }
    """
    result = {
        "platform": "bilibili",
        "type": "视频",
        "title": "",
        "content": "",
        "success": False,
        "message": "",
    }

    url = _normalize_url(url)

    # 提取 BV 号或 AV 号
    bv_match = re.search(r"(BV[\w]+)", url)
    av_match = re.search(r"av(\d+)", url)

    video_id = bv_match.group(1) if bv_match else None
    if not video_id and av_match:
        video_id = f"av{av_match.group(1)}"

    if not video_id:
        result["message"] = "无法从链接中提取B站视频ID"
        return result

    # 请求页面
    html = _safe_request(url, headers=BILIBILI_HEADERS)
    if not html:
        result["message"] = "无法访问B站页面，可能链接已失效或受到反爬限制"
        return result

    # 提取标题
    result["title"] = _extract_title(html)

    # 提取视频简介
    content_parts = []

    # 方式一：从 meta description 提取
    desc = _extract_meta_description(html)
    if desc:
        content_parts.append(desc)

    # 方式二：从页面 script 标签中的初始数据提取
    if not content_parts:
        detail_desc = _extract_bilibili_detail(html)
        if detail_desc:
            content_parts.append(detail_desc)

    # 方式三：从页面正文提取
    if not content_parts:
        body_text = _extract_bilibili_from_body(html)
        if body_text:
            content_parts.append(body_text)

    if content_parts:
        result["content"] = "\n".join(content_parts)
        result["success"] = True

        if not result["title"]:
            result["title"] = f"B站视频 {video_id}"

        result["message"] = (
            "已提取到视频标题和简介信息。"
            "注意：完整的视频内容需要字幕提取或语音转文字功能，当前仅支持提取文字简介。"
        )
    else:
        result["message"] = (
            "无法提取B站视频内容。"
            "可能原因：视频需要登录查看、触发了反爬机制、或链接已失效。"
        )

    return result


def _extract_bilibili_detail(html: str) -> str:
    """
    从B站页面 script 标签中提取视频简介

    Args:
        html: 页面 HTML

    Returns:
        视频简介文本
    """
    soup = BeautifulSoup(html, "lxml")

    for script in soup.find_all("script"):
        script_text = script.string
        if not script_text:
            continue

        # B站通常在 __INITIAL_STATE__ 中嵌入数据
        if "__INITIAL_STATE__" not in script_text:
            continue

        try:
            match = re.search(
                r'__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*$',
                script_text,
                re.DOTALL,
            )
            if not match:
                continue

            json_str = match.group(1)
            json_str = re.sub(r'\bundefined\b', 'null', json_str)

            data = json.loads(json_str)

            # 提取视频简介
            desc = (
                data.get("videoData", {})
                .get("desc", "")
            )
            if desc:
                return desc

            # 备用路径
            desc = (
                data.get("detail", {})
                .get("desc", "")
            )
            if desc:
                return desc

        except (json.JSONDecodeError, KeyError, TypeError):
            continue

    return ""


def _extract_bilibili_from_body(html: str) -> str:
    """
    从B站页面正文中提取视频简介

    Args:
        html: 页面 HTML

    Returns:
        提取到的文本
    """
    soup = BeautifulSoup(html, "lxml")

    # B站简介通常在特定的 class 容器中
    desc_selectors = [
        {"class_": "video-desc"},
        {"class_": "desc-info"},
        {"class_": "info-desc"},
        {"itemprop": "description"},
    ]

    for selector in desc_selectors:
        elem = soup.find(**selector)
        if elem:
            text = elem.get_text(strip=True)
            if text:
                return text

    return ""


# ==================== 微信公众号文章解析 ====================

def parse_wechat(url: str) -> Dict:
    """
    解析微信公众号文章链接，提取标题和正文内容

    微信公众号文章通常可以直接获取 HTML 内容，
    但部分文章可能需要通过微信客户端打开。

    Args:
        url: 微信公众号文章链接

    Returns:
        字典格式：
        {
            "platform": "wechat",
            "type": "图文",
            "title": "文章标题",
            "content": "文章正文",
            "success": True/False,
            "message": "错误信息（失败时）"
        }
    """
    result = {
        "platform": "wechat",
        "type": "图文",
        "title": "",
        "content": "",
        "success": False,
        "message": "",
    }

    url = _normalize_url(url)

    # 请求页面
    html = _safe_request(url, headers=WECHAT_HEADERS)
    if not html:
        result["message"] = "无法访问微信公众号文章，可能链接已失效或需要通过微信客户端打开"
        return result

    # 提取标题
    result["title"] = _extract_title(html)

    # 提取正文内容
    content_text = _extract_wechat_content(html)

    if content_text:
        result["content"] = content_text
        result["success"] = True
    else:
        # 尝试通用提取
        content_text = _clean_html(html)
        if content_text and len(content_text) > 50:
            result["content"] = content_text
            result["success"] = True
        else:
            result["message"] = (
                "无法提取微信公众号文章内容。"
                "可能原因：文章已被删除、需要通过微信客户端打开、或触发了反爬机制。"
            )

    return result


def _extract_wechat_content(html: str) -> str:
    """
    从微信公众号文章 HTML 中提取正文内容

    微信公众号文章的正文通常在 id="js_content" 的 div 中。

    Args:
        html: 页面 HTML

    Returns:
        文章正文文本
    """
    soup = BeautifulSoup(html, "lxml")

    # 微信公众号文章正文容器
    content_div = soup.find("div", id="js_content")
    if content_div:
        # 移除正文中的无关元素
        for tag in content_div.find_all(["script", "style", "iframe"]):
            tag.decompose()

        text = content_div.get_text(separator="\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(lines).strip()

    return ""


# ==================== 通用网页内容提取 ====================

def parse_webpage(url: str) -> Dict:
    """
    通用网页内容提取，使用 BeautifulSoup 提取网页正文

    对于无法识别平台的链接，使用通用方法提取页面内容。
    会自动去除广告、导航等无关元素。

    Args:
        url: 网页链接

    Returns:
        字典格式：
        {
            "platform": "unknown",
            "type": "unknown",
            "title": "页面标题",
            "content": "页面正文",
            "success": True/False,
            "message": "错误信息（失败时）"
        }
    """
    result = {
        "platform": "unknown",
        "type": "unknown",
        "title": "",
        "content": "",
        "success": False,
        "message": "",
    }

    url = _normalize_url(url)

    # 请求页面
    html = _safe_request(url)
    if not html:
        result["message"] = "无法访问该网页，请检查链接是否有效或网络连接是否正常"
        return result

    # 提取标题
    result["title"] = _extract_title(html)

    # 提取正文
    content_text = _clean_html(html)

    # 如果提取到的内容太短，尝试从 meta description 补充
    if len(content_text) < 50:
        meta_desc = _extract_meta_description(html)
        if meta_desc:
            content_text = meta_desc

    if content_text and len(content_text) > 10:
        result["content"] = content_text
        result["success"] = True
    else:
        result["message"] = "无法从该网页中提取有效内容，页面可能为空或需要特殊权限访问"

    return result


# ==================== 统一解析入口 ====================

def parse_link(url: str) -> Dict:
    """
    统一链接解析入口

    自动识别链接所属平台，调用对应的解析函数，
    返回统一格式的解析结果。

    解析流程：
    1. 识别平台和内容类型
    2. 根据平台调用专用解析函数
    3. 未识别平台则使用通用网页提取
    4. 统一返回格式

    Args:
        url: 待解析的链接

    Returns:
        统一格式的字典：
        {
            "platform": "平台标识",
            "platform_name": "平台中文名",
            "type": "内容类型（视频/图文）",
            "title": "标题",
            "content": "正文内容",
            "success": True/False,
            "message": "错误或提示信息"
        }

    示例:
        >>> result = parse_link("https://www.bilibili.com/video/BV1xx411c7mD")
        >>> print(result["platform"])
        'bilibili'
    """
    # 参数校验
    if not url or not isinstance(url, str):
        return {
            "platform": "unknown",
            "platform_name": "其他",
            "type": "unknown",
            "title": "",
            "content": "",
            "success": False,
            "message": "链接不能为空",
        }

    url = url.strip()
    if not url:
        return {
            "platform": "unknown",
            "platform_name": "其他",
            "type": "unknown",
            "title": "",
            "content": "",
            "success": False,
            "message": "链接不能为空",
        }

    # 识别平台
    platform_info = detect_platform(url)
    platform = platform_info["platform"]

    logger.info(
        "解析链接: %s, 识别平台: %s, 类型: %s",
        url,
        platform_info["platform_name"],
        platform_info["type"],
    )

    # 根据平台调用对应的解析函数
    parsers = {
        "xiaohongshu": parse_xiaohongshu,
        "douyin": parse_douyin,
        "bilibili": parse_bilibili,
        "wechat": parse_wechat,
    }

    parser = parsers.get(platform)
    if parser:
        try:
            result = parser(url)
        except Exception as e:
            logger.error("解析链接异常: %s, 错误: %s", url, e)
            result = {
                "platform": platform,
                "platform_name": platform_info["platform_name"],
                "type": platform_info["type"],
                "title": "",
                "content": "",
                "success": False,
                "message": f"解析过程发生异常: {e}",
            }
    else:
        # 未识别平台，使用通用网页提取
        try:
            result = parse_webpage(url)
        except Exception as e:
            logger.error("通用解析异常: %s, 错误: %s", url, e)
            result = {
                "platform": "unknown",
                "platform_name": "其他",
                "type": "unknown",
                "title": "",
                "content": "",
                "success": False,
                "message": f"解析过程发生异常: {e}",
            }

    # 补充平台中文名
    if "platform_name" not in result:
        result["platform_name"] = platform_info["platform_name"]

    # 如果内容类型未确定，使用识别结果
    if result.get("type") == "unknown" and platform_info["type"] != "unknown":
        result["type"] = platform_info["type"]

    return result


# ==================== 模块测试入口 ====================

if __name__ == "__main__":
    # 配置日志输出
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=" * 60)
    print("视频/图文链接解析模块测试")
    print("=" * 60)

    # 测试链接
    test_urls = [
        "https://www.xiaohongshu.com/explore/1234567890",
        "https://www.douyin.com/video/1234567890123456789",
        "https://www.bilibili.com/video/BV1xx411c7mD",
        "https://mp.weixin.qq.com/s/abcdefghijklmnopqrstuvwxyz",
        "https://example.com/article/fund-guide",
    ]

    for url in test_urls:
        print(f"\n--- 测试链接: {url} ---")

        # 测试平台识别
        platform_info = detect_platform(url)
        print(
            f"  平台: {platform_info['platform_name']} "
            f"({platform_info['platform']}), "
            f"类型: {platform_info['type']}"
        )

        # 测试统一解析
        result = parse_link(url)
        print(f"  解析结果: {'成功' if result['success'] else '失败'}")
        if result["success"]:
            print(f"  标题: {result['title'][:50]}...")
            content_preview = result["content"][:100] if result["content"] else "无"
            print(f"  内容预览: {content_preview}...")
        else:
            print(f"  信息: {result['message'][:80]}...")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
