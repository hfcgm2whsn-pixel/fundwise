"""
FundWise AI 服务模块
接入 DeepSeek API（兼容 OpenAI SDK 格式），提供基金学习相关的 AI 功能
"""

import os
import json
from typing import List, Dict, Optional

from openai import OpenAI

# ============================================================
# 全局客户端实例
# ============================================================
_client: Optional[OpenAI] = None

# DeepSeek API 配置
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


def init_api_client() -> OpenAI:
    """
    初始化 DeepSeek API 客户端
    从环境变量 DEEPSEEK_API_KEY 读取密钥
    返回 OpenAI 客户端实例（兼容 DeepSeek 接口）
    """
    global _client

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")

    if not api_key:
        raise ValueError(
            "未找到 DEEPSEEK_API_KEY 环境变量，"
            "请设置环境变量或在 .env 文件中配置后再启动服务"
        )

    _client = OpenAI(
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL,
    )

    return _client


def _get_client() -> OpenAI:
    """获取已初始化的客户端，若未初始化则自动初始化"""
    global _client
    if _client is None:
        _client = init_api_client()
    return _client


def _chat_completion(
    system_prompt: str,
    user_message: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """
    底层调用 DeepSeek Chat 接口的通用方法

    参数:
        system_prompt: 系统提示词
        user_message: 用户消息
        chat_history: 历史对话记录，每条格式为 {"role": "user"/"assistant", "content": "..."}
        temperature: 生成温度，控制回答的随机性
        max_tokens: 最大生成 token 数

    返回:
        AI 回复的文本内容
    """
    client = _get_client()

    # 构造消息列表
    messages = [{"role": "system", "content": system_prompt}]

    # 追加历史对话
    if chat_history:
        messages.extend(chat_history)

    # 追加当前用户消息
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 提取回复内容
        content = response.choices[0].message.content
        return content.strip() if content else ""

    except Exception as e:
        raise RuntimeError(f"调用 DeepSeek API 失败: {e}") from e


# ============================================================
# 1. 基金知识问答
# ============================================================

def answer_question(question: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    基金知识问答 —— 用大白话回答用户的基金相关问题

    参数:
        question: 用户提出的问题（自然语言）
        chat_history: 历史对话记录，用于多轮对话上下文

    返回:
        AI 回答文本
    """
    if chat_history is None:
        chat_history = []

    system_prompt = (
        "你是 FundWise 基金学习助手，专门帮助零基础用户学习基金知识。\n\n"
        "要求：\n"
        "1. 用通俗易懂的大白话回答，避免使用过多专业术语\n"
        "2. 多举生活中的例子来帮助理解\n"
        "3. 不推荐任何具体的基金产品\n"
        "4. 不预测任何基金的涨跌\n"
        "5. 回答简洁有条理，分段清晰\n"
        "6. 如果涉及风险，务必提醒用户投资有风险\n"
        "7. 面向中国普通投资者，用人民币、A股等熟悉的场景举例"
    )

    return _chat_completion(
        system_prompt=system_prompt,
        user_message=question,
        chat_history=chat_history,
    )


# ============================================================
# 2. 基金涨跌解读
# ============================================================

def interpret_fund_data(fund_data: Dict) -> str:
    """
    基金涨跌解读 —— 用通俗语言解读基金当日表现

    参数:
        fund_data: 基金数据字典，建议包含以下字段：
            - fund_name: 基金名称
            - fund_code: 基金代码
            - nav: 单位净值
            - nav_change: 净值变动额
            - nav_change_percent: 涨跌幅（百分比）
            - type: 基金类型（股票型/混合型/债券型/货币型等）
            - 其他可选字段

    返回:
        解读文本
    """
    system_prompt = (
        "你是一位资深的基金分析师，擅长用通俗易懂的语言解读基金数据。\n\n"
        "要求：\n"
        "1. 用大白话解释这只基金今天的表现\n"
        "2. 涨跌幅用生活化的比喻来帮助理解（比如相当于每天多赚/少赚一杯奶茶钱）\n"
        "3. 分析可能的原因（市场环境、行业板块等），但说明这只是猜测\n"
        "4. 不构成任何投资建议，不推荐买入或卖出\n"
        "5. 必须在末尾加上风险提示：以上解读仅供参考，不构成投资建议\n"
        "6. 回答简洁，控制在 300 字以内"
    )

    # 将基金数据格式化为可读文本
    data_text = json.dumps(fund_data, ensure_ascii=False, indent=2)

    user_message = (
        f"请解读以下基金数据：\n\n{data_text}\n\n"
        "请用通俗语言帮我理解这只基金今天的表现。"
    )

    return _chat_completion(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.6,
        max_tokens=1024,
    )


# ============================================================
# 3. 视频/图文内容总结
# ============================================================

def summarize_content(content_text: str, platform: str = "") -> str:
    """
    视频/图文内容总结 —— 将提取的文本内容生成结构化总结

    参数:
        content_text: 从视频/图文提取的文本内容
        platform: 内容来源平台（如"B站"、"抖音"、"小红书"、"微信公众号"等），可选

    返回:
        结构化总结文本，包含以下板块：
        【视频主题】【核心观点】【适合什么投资者】【一句话总结】
    """
    system_prompt = (
        "你是一位基金学习内容分析专家，擅长从视频或图文内容中提取关键信息。\n\n"
        "要求：\n"
        "1. 严格按照以下结构输出总结：\n"
        "   【视频主题】用一句话概括内容主题\n"
        "   【核心观点】列出 3-5 个核心观点，每个观点用大白话解释\n"
        "   【适合什么投资者】说明这个内容适合什么水平的投资者\n"
        "   【一句话总结】用一句精炼的话总结全文\n"
        "2. 用通俗易懂的语言，避免专业术语堆砌\n"
        "3. 如果内容中包含具体基金推荐或预测，标注为「仅供参考」\n"
        "4. 总结要客观，不添加原文没有的信息"
    )

    platform_hint = f"（内容来自 {platform}）" if platform else ""

    user_message = (
        f"请总结以下基金学习内容{platform_hint}：\n\n"
        f"{content_text}\n\n"
        "请按指定格式生成结构化总结。"
    )

    return _chat_completion(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.4,
        max_tokens=2048,
    )


# ============================================================
# 4. 智能学习建议
# ============================================================

def generate_learning_plan(
    user_level: str,
    interests: List[str],
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    智能学习建议 —— 根据用户水平和兴趣生成个性化学习计划

    参数:
        user_level: 用户水平，如 "零基础"、"入门"、"进阶"、"高手"
        interests: 用户感兴趣的主题列表，如 ["指数基金", "定投", "债券基金"]
        chat_history: 历史对话记录，用于了解用户已学内容和疑问

    返回:
        个性化学习计划文本
    """
    if chat_history is None:
        chat_history = []

    system_prompt = (
        "你是一位基金教育规划师，擅长为不同水平的投资者制定学习计划。\n\n"
        "要求：\n"
        "1. 根据用户的水平和兴趣，制定循序渐进的学习计划\n"
        "2. 每个学习阶段包含：主题、学习内容概要、推荐资源类型（书籍/视频/文章）、预计学习时间\n"
        "3. 用鼓励性的语气，让用户觉得学习基金并不难\n"
        "4. 不推荐具体基金产品\n"
        "5. 计划要实际可行，不要安排过多内容\n"
        "6. 考虑用户已有的对话历史，避免重复已掌握的内容"
    )

    interests_text = "、".join(interests) if interests else "基金基础知识"

    user_message = (
        f"我的基金学习水平：{user_level}\n"
        f"我感兴趣的主题：{interests_text}\n\n"
        "请为我制定一个个性化的基金学习计划。"
    )

    return _chat_completion(
        system_prompt=system_prompt,
        user_message=user_message,
        chat_history=chat_history,
        temperature=0.7,
        max_tokens=2048,
    )


# ============================================================
# 5. 基金走势分析
# ============================================================

def analyze_fund_trend(fund_code: str, history_data: List[Dict]) -> str:
    """
    基金走势分析 —— 分析基金近期趋势、波动特征和适合的投资风格

    参数:
        fund_code: 基金代码
        history_data: 历史净值数据列表，每条记录建议包含：
            - date: 日期
            - nav: 单位净值
            - acc_nav: 累计净值（可选）
            - nav_change_percent: 日涨跌幅（可选）

    返回:
        走势分析文本（包含风险提示）
    """
    system_prompt = (
        "你是一位专业的基金分析师，擅长分析基金走势数据。\n\n"
        "要求：\n"
        "1. 分析近期净值走势：整体趋势（上涨/下跌/震荡）、关键转折点\n"
        "2. 分析波动特征：波动幅度、最大回撤区间、稳定性评价\n"
        "3. 分析适合的投资风格：适合定投还是一次性买入、适合短期还是长期持有\n"
        "4. 用通俗易懂的语言，配合数据说明\n"
        "5. 不预测未来走势，不推荐买入或卖出\n"
        "6. 必须在分析末尾包含以下风险提示（不可省略）：\n"
        "   「风险提示：以上分析仅基于历史数据，不代表未来表现。"
        "基金投资有风险，过往业绩不预示未来收益。"
        "请根据自身风险承受能力谨慎决策。」"
    )

    # 将历史数据格式化为可读文本
    data_text = json.dumps(history_data, ensure_ascii=False, indent=2)

    user_message = (
        f"请分析基金 {fund_code} 的走势：\n\n"
        f"历史净值数据：\n{data_text}\n\n"
        "请从趋势、波动、适合的投资风格三个维度进行分析。"
    )

    return _chat_completion(
        system_prompt=system_prompt,
        user_message=user_message,
        temperature=0.5,
        max_tokens=2048,
    )
