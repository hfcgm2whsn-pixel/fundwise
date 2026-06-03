"""
FundWise 基金学习助手 - 数据持久化模块
使用 JSON 文件存储问答历史记录和视频总结记录
"""

import json
import os
import uuid
import threading
from datetime import datetime

# 数据目录路径
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CHAT_HISTORY_FILE = os.path.join(DATA_DIR, "chat_history.json")
VIDEO_SUMMARIES_FILE = os.path.join(DATA_DIR, "video_summaries.json")

# 线程锁，防止并发读写
_chat_lock = threading.Lock()
_video_lock = threading.Lock()


def init_storage():
    """初始化存储：创建数据目录和 JSON 文件（如果不存在）"""
    try:
        # 创建数据目录
        os.makedirs(DATA_DIR, exist_ok=True)

        # 初始化 chat_history.json
        if not os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

        # 初始化 video_summaries.json
        if not os.path.exists(VIDEO_SUMMARIES_FILE):
            with open(VIDEO_SUMMARIES_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    except OSError as e:
        print(f"[storage] 初始化存储失败: {e}")
        raise


# ==================== 问答记录管理 ====================

def save_chat_record(question, answer, references=None):
    """
    保存一条问答记录

    Args:
        question (str): 用户的问题
        answer (str): AI 的回答
        references (list): 参考资料链接列表

    Returns:
        dict: 保存的记录（含 id 和 timestamp）
    """
    if references is None:
        references = []

    record = {
        "id": str(uuid.uuid4()),
        "question": question,
        "answer": answer,
        "references": references,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        with _chat_lock:
            # 读取已有记录
            records = _read_json_file(CHAT_HISTORY_FILE)
            # 追加新记录
            records.append(record)
            # 写回文件
            _write_json_file(CHAT_HISTORY_FILE, records)
        return record
    except (OSError, json.JSONDecodeError) as e:
        print(f"[storage] 保存问答记录失败: {e}")
        raise


def get_all_chat_records():
    """
    获取所有问答记录（按时间倒序）

    Returns:
        list: 问答记录列表
    """
    try:
        with _chat_lock:
            records = _read_json_file(CHAT_HISTORY_FILE)
        # 按时间倒序排列
        records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return records
    except (OSError, json.JSONDecodeError) as e:
        print(f"[storage] 获取问答记录失败: {e}")
        raise


def get_chat_record(record_id):
    """
    获取单条问答记录详情

    Args:
        record_id (str): 记录 ID

    Returns:
        dict or None: 匹配的记录，未找到则返回 None
    """
    try:
        with _chat_lock:
            records = _read_json_file(CHAT_HISTORY_FILE)
        for record in records:
            if record.get("id") == record_id:
                return record
        return None
    except (OSError, json.JSONDecodeError) as e:
        print(f"[storage] 获取问答记录详情失败: {e}")
        raise


def delete_chat_record(record_id):
    """
    删除一条问答记录

    Args:
        record_id (str): 记录 ID

    Returns:
        bool: 是否删除成功
    """
    try:
        with _chat_lock:
            records = _read_json_file(CHAT_HISTORY_FILE)
            original_len = len(records)
            records = [r for r in records if r.get("id") != record_id]
            if len(records) == original_len:
                return False  # 未找到对应记录
            _write_json_file(CHAT_HISTORY_FILE, records)
        return True
    except (OSError, json.JSONDecodeError) as e:
        print(f"[storage] 删除问答记录失败: {e}")
        raise


def clear_all_chat_records():
    """清空所有问答记录"""
    try:
        with _chat_lock:
            _write_json_file(CHAT_HISTORY_FILE, [])
    except (OSError, json.JSONDecodeError) as e:
        print(f"[storage] 清空问答记录失败: {e}")
        raise


# ==================== 视频总结记录管理 ====================

def save_video_summary(url, platform, title, summary, mindmap_data=None):
    """
    保存一条视频总结记录

    Args:
        url (str): 原始视频链接
        platform (str): 平台名称
        title (str): 内容标题
        summary (str): AI 总结文本
        mindmap_data (dict or None): 思维导图数据

    Returns:
        dict: 保存的记录（含 id 和 timestamp）
    """
    record = {
        "id": str(uuid.uuid4()),
        "url": url,
        "platform": platform,
        "title": title,
        "summary": summary,
        "mindmap_data": mindmap_data,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        with _video_lock:
            records = _read_json_file(VIDEO_SUMMARIES_FILE)
            records.append(record)
            _write_json_file(VIDEO_SUMMARIES_FILE, records)
        return record
    except (OSError, json.JSONDecodeError) as e:
        print(f"[storage] 保存视频总结失败: {e}")
        raise


def get_all_video_summaries():
    """
    获取所有视频总结记录（按时间倒序）

    Returns:
        list: 视频总结记录列表
    """
    try:
        with _video_lock:
            records = _read_json_file(VIDEO_SUMMARIES_FILE)
        records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return records
    except (OSError, json.JSONDecodeError) as e:
        print(f"[storage] 获取视频总结失败: {e}")
        raise


def get_video_summary(summary_id):
    """
    获取单条视频总结详情

    Args:
        summary_id (str): 总结记录 ID

    Returns:
        dict or None: 匹配的记录，未找到则返回 None
    """
    try:
        with _video_lock:
            records = _read_json_file(VIDEO_SUMMARIES_FILE)
        for record in records:
            if record.get("id") == summary_id:
                return record
        return None
    except (OSError, json.JSONDecodeError) as e:
        print(f"[storage] 获取视频总结详情失败: {e}")
        raise


def delete_video_summary(summary_id):
    """
    删除一条视频总结记录

    Args:
        summary_id (str): 总结记录 ID

    Returns:
        bool: 是否删除成功
    """
    try:
        with _video_lock:
            records = _read_json_file(VIDEO_SUMMARIES_FILE)
            original_len = len(records)
            records = [r for r in records if r.get("id") != summary_id]
            if len(records) == original_len:
                return False  # 未找到对应记录
            _write_json_file(VIDEO_SUMMARIES_FILE, records)
        return True
    except (OSError, json.JSONDecodeError) as e:
        print(f"[storage] 删除视频总结失败: {e}")
        raise


def clear_all_video_summaries():
    """清空所有视频总结记录"""
    try:
        with _video_lock:
            _write_json_file(VIDEO_SUMMARIES_FILE, [])
    except (OSError, json.JSONDecodeError) as e:
        print(f"[storage] 清空视频总结失败: {e}")
        raise


# ==================== 内部工具函数 ====================

def _read_json_file(filepath):
    """
    读取 JSON 文件内容

    Args:
        filepath (str): 文件路径

    Returns:
        list: 解析后的列表数据
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def _write_json_file(filepath, data):
    """
    将数据写入 JSON 文件（格式化输出）

    Args:
        filepath (str): 文件路径
        data (list): 要写入的数据
    """
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
