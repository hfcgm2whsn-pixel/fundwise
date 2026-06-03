# -*- coding: utf-8 -*-
"""
FundWise v2.0 - Streamlit main application.

Integrates fund data query, AI Q&A with references, video summary
with mindmap, learning plan with links, multi-fund trend analysis,
persistent storage, and image export.
"""

import os
import re
import streamlit as st
import pandas as pd

# Import project modules
from fund_api import (
    get_fund_basic_info,
    get_fund_realtime_estimate,
    get_fund_history_nav,
    search_fund,
    get_fund_overview,
)
from ai_service import (
    init_api_client,
    answer_question_with_references,
    interpret_fund_data,
    compare_funds,
    summarize_content,
    combine_summaries,
    generate_learning_plan_with_links,
    analyze_fund_trend,
    analyze_multi_fund_trend,
)
from video_parser import detect_platform, parse_link
from storage import (
    init_storage,
    save_chat_record,
    get_all_chat_records,
    get_chat_record,
    delete_chat_record,
    save_video_summary,
    get_all_video_summaries,
    get_video_summary,
    delete_video_summary,
)
from export_utils import export_text_to_image
from mindmap import generate_mindmap


# ==================== Page Config ====================
st.set_page_config(
    page_title="FundWise",
    page_icon="\U0001f4b0",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==================== Custom CSS ====================
_CSS = """
<style>
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8edf5 100%);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a2a4a 0%, #2c3e6b 100%);
    }
    [data-testid="stSidebar"] * {
        color: #e0e6f0 !important;
    }
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stRadio p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }
    .card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
        margin-bottom: 16px;
        border: 1px solid #e8edf5;
    }
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a2a4a;
        margin-bottom: 8px;
    }
    .sub-title {
        font-size: 1rem;
        color: #6b7b9e;
        margin-bottom: 24px;
    }
    .rise {
        color: #e74c3c;
        font-weight: bold;
    }
    .fall {
        color: #27ae60;
        font-weight: bold;
    }
    .flat {
        color: #95a5a6;
        font-weight: bold;
    }
    .stChatMessage {
        border-radius: 12px;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
    }
    .risk-warning {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 12px 16px;
        border-radius: 4px;
        margin-top: 16px;
        color: #856404;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 12px 16px;
        border-radius: 4px;
        color: #155724;
    }
    .info-box {
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 12px 16px;
        border-radius: 4px;
        color: #0c5460;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        padding: 12px 16px;
        border-radius: 4px;
        color: #721c24;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e8edf5;
        transition: border-color 0.3s ease;
    }
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
    }
    .streamlit-expanderHeader {
        font-weight: 600;
    }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)

# ==================== String Constants ====================
# All user-facing Chinese strings are defined here as variables.
_MODE_CHAT = "\u667a\u80fd\u95ee\u7b54"
_MODE_FUND = "\u67e5\u6da8\u8dcc"
_MODE_VIDEO = "\u89c6\u9891\u603b\u7ed3"
_MODE_PLAN = "\u5b66\u4e60\u8ba1\u5212"
_MODE_TREND = "\u8d70\u52bf\u5206\u6790"

_MODE_OPTIONS = [_MODE_CHAT, _MODE_FUND, _MODE_VIDEO, _MODE_PLAN, _MODE_TREND]

_APP_TITLE = "\U0001f4b0 FundWise"
_APP_SUBTITLE = "\u57fa\u91d1\u5b66\u4e60\u52a9\u624b"

_NAV_LABEL = "\u529f\u80fd\u5bfc\u822a"
_NAV_RADIO_LABEL = "\u9009\u62e9\u529f\u80fd"

_API_EXPANDER = "\u2699\ufe0f API \u8bbe\u7f6e"
_API_INPUT_LABEL = "DeepSeek API Key"
_API_INPUT_PLACEHOLDER = "\u8bf7\u8f93\u5165\u60a8\u7684 DeepSeek API Key"
_API_INPUT_HELP = "\u5728 https://platform.deepseek.com \u83b7\u53d6 API Key"
_API_SUCCESS = "API Key \u914d\u7f6e\u6210\u529f\uff01"
_API_FAIL = "API Key \u65e0\u6548\uff0c\u8bf7\u68c0\u67e5\u540e\u91cd\u8bd5"
_API_CONNECTED = "API \u5df2\u8fde\u63a5"
_API_NOT_CONFIGURED = "API \u672a\u914d\u7f6e\uff0cAI \u529f\u80fd\u4e0d\u53ef\u7528"

_ABOUT_EXPANDER = "\u2139\ufe0f \u5173\u4e8e"
_ABOUT_TEXT = (
    "**FundWise \u57fa\u91d1\u5b66\u4e60\u52a9\u624b**\n\n"
    "\u4e00\u6b3e\u9762\u5411\u57fa\u91d1\u6295\u8d44\u521d\u5b66\u8005\u7684\u667a\u80fd\u5b66\u4e60\u5de5\u5177\uff0c"
    "\u5e2e\u52a9\u4f60\uff1a\n\n"
    "- \u7528\u5927\u767d\u8bdd\u7406\u89e3\u57fa\u91d1\u77e5\u8bc6\n"
    "- \u968f\u65f6\u67e5\u8be2\u57fa\u91d1\u6da8\u8dcc\n"
    "- \u603b\u7ed3\u57fa\u91d1\u5b66\u4e60\u89c6\u9891/\u6587\u7ae0\n"
    "- \u83b7\u53d6\u4e2a\u6027\u5316\u5b66\u4e60\u8ba1\u5212\n"
    "- \u5206\u6790\u57fa\u91d1\u8d70\u52bf\n\n"
    "**\u7248\u672c\uff1a** v2.0\n\n"
    "**\u6570\u636e\u6765\u6e90\uff1a** \u5929\u5929\u57fa\u91d1\uff08\u4e1c\u65b9\u8d22\u5bcc\uff09\n\n"
    "**AI \u5f15\u64ce\uff1a** DeepSeek"
)
_DISCLAIMER_TEXT = (
    '<div class="risk-warning" style="font-size: 0.8rem;">'
    '<strong>\u514d\u8d23\u58f0\u660e\uff1a</strong>'
    '\u672c\u5de5\u5177\u63d0\u4f9b\u7684\u4fe1\u606f\u548c\u5185\u5bb9'
    '\u4ec5\u4f9b\u5b66\u4e60\u548c\u53c2\u8003\uff0c'
    '\u4e0d\u6784\u6210\u4efb\u4f55\u6295\u8d44\u5efa\u8bae\u3002'
    '\u57fa\u91d1\u6295\u8d44\u6709\u98ce\u9669\uff0c\u6295\u8d44\u9700\u8c28\u614e\u3002'
    '\u7528\u6237\u5e94\u81ea\u884c\u5224\u65ad\u5e76\u627f\u62c5\u6295\u8d44\u98ce\u9669\u3002'
    '</div>'
)

_API_WARNING_HTML = (
    '<div class="info-box">'
    '<strong>\u63d0\u793a\uff1a</strong>'
    '\u8bf7\u5148\u5728\u5de6\u4fa7\u8fb9\u680f\u7684\u300cAPI \u8bbe\u7f6e\u300d'
    '\u4e2d\u914d\u7f6e DeepSeek API Key\uff0c'
    '\u624d\u80fd\u4f7f\u7528 AI \u667a\u80fd\u95ee\u7b54\u3001\u5185\u5bb9\u603b\u7ed3\u3001'
    '\u5b66\u4e60\u8ba1\u5212\u7b49\u529f\u80fd\u3002'
    '</div>'
)

_RISK_WARNING_HTML = (
    '<div class="risk-warning">'
    '<strong>\u98ce\u9669\u63d0\u793a\uff1a</strong>'
    '\u4ee5\u4e0a\u5185\u5bb9\u4ec5\u4f9b\u53c2\u8003\uff0c'
    '\u4e0d\u6784\u6210\u4efb\u4f55\u6295\u8d44\u5efa\u8bae\u3002'
    '\u57fa\u91d1\u6295\u8d44\u6709\u98ce\u9669\uff0c'
    '\u8fc7\u5f80\u4e1a\u7ee9\u4e0d\u9884\u793a\u672a\u6765\u6536\u76ca\u3002'
    '\u8bf7\u6839\u636e\u81ea\u8eab\u98ce\u9669\u627f\u53d7\u80fd\u529b\u8c28\u614e\u51b3\u7b56\u3002'
    '</div>'
)

# Chat mode strings
_CHAT_HEADER = (
    '<div class="card">'
    '<h2 class="main-title">\U0001f4ac \u667a\u80fd\u95ee\u7b54</h2>'
    '<p class="sub-title">'
    '\u6709\u4efb\u4f55\u5173\u4e8e\u57fa\u91d1\u7684\u95ee\u9898\uff0c'
    '\u5c3d\u7ba1\u95ee\u6211\uff01\u6211\u4f1a\u7528\u5927\u767d\u8bdd\u5e2e\u4f60\u89e3\u7b54\u3002'
    '</p>'
    '</div>'
)
_CHAT_WELCOME = (
    "\u4f60\u597d\uff01\u6211\u662f **FundWise \u57fa\u91d1\u5b66\u4e60\u52a9\u624b** \U0001f44b\n\n"
    "\u6211\u53ef\u4ee5\u5e2e\u4f60\uff1a\n"
    "- \u89e3\u91ca\u57fa\u91d1\u76f8\u5173\u6982\u5ff5\uff08\u5982\uff1a\u4ec0\u4e48\u662f\u6307\u6570\u57fa\u91d1\uff1f\uff09\n"
    "- \u89e3\u7b54\u6295\u8d44\u5165\u95e8\u95ee\u9898\uff08\u5982\uff1a\u65b0\u624b\u600e\u4e48\u5f00\u59cb\u4e70\u57fa\u91d1\uff1f\uff09\n"
    "- \u5206\u6790\u57fa\u91d1\u6570\u636e\uff08\u5982\uff1a\u67d0\u53ea\u57fa\u91d1\u4eca\u5929\u6da8\u4e86\u8fd8\u662f\u8dcc\u4e86\uff1f\uff09\n\n"
    "\u6709\u4ec0\u4e48\u60f3\u95ee\u7684\uff0c\u76f4\u63a5\u8f93\u5165\u5c31\u597d\uff01"
)
_CHAT_INPUT_PLACEHOLDER = "\u8bf7\u8f93\u5165\u4f60\u7684\u95ee\u9898..."
_CHAT_THINKING = "\u601d\u8003\u4e2d..."
_CHAT_ERROR = "\u62b1\u6b54\uff0c\u56de\u7b54\u95ee\u9898\u65f6\u51fa\u9519\u4e86\uff1a{}"
_CHAT_CLEAR_BTN = "\u6e05\u7a7a\u5bf9\u8bdd\u8bb0\u5f55"
_CHAT_HISTORY_BTN = "\u5386\u53f2\u8bb0\u5f55"
_CHAT_NO_HISTORY = "\u6682\u65e0\u5386\u53f2\u8bb0\u5f55"
_CHAT_EXPORT_BTN = "\u5bfc\u51fa\u56fe\u7247"
_CHAT_DELETE_BTN = "\u5220\u9664"
_CHAT_DELETE_CONFIRM = "\u786e\u5b9a\u8981\u5220\u9664\u8fd9\u6761\u8bb0\u5f55\u5417\uff1f"
_CHAT_DELETED = "\u8bb0\u5f55\u5df2\u5220\u9664"
_CHAT_EXPORT_FAIL = "\u5bfc\u51fa\u5931\u8d25\uff0c\u8bf7\u786e\u4fdd\u5df2\u5b89\u88c5 Pillow \u5e93"

# Fund query mode strings
_FUND_HEADER = (
    '<div class="card">'
    '<h2 class="main-title">\U0001f4c8 \u67e5\u6da8\u8dcc</h2>'
    '<p class="sub-title">'
    '\u8f93\u5165\u57fa\u91d1\u4ee3\u7801\uff08\u652f\u6301\u591a\u4e2a\uff09\u6216\u5173\u952e\u8bcd\uff0c'
    '\u5feb\u901f\u67e5\u770b\u57fa\u91d1\u6700\u65b0\u8868\u73b0\u548c AI \u5bf9\u6bd4\u5206\u6790\u3002'
    '</p>'
    '</div>'
)
_FUND_CODE_LABEL = "\u57fa\u91d1\u4ee3\u7801"
_FUND_CODE_PLACEHOLDER = "\u8f93\u5165\u57fa\u91d1\u4ee3\u7801\uff0c\u591a\u4e2a\u7528\u9017\u53f7\u6216\u7a7a\u683c\u5206\u9694\uff08\u6700\u591a10\u4e2a\uff09"
_FUND_QUERY_BTN = "\u67e5\u8be2\u57fa\u91d1"
_FUND_KEYWORD_LABEL = "\u641c\u7d22\u5173\u952e\u8bcd"
_FUND_KEYWORD_PLACEHOLDER = "\u8f93\u5165\u57fa\u91d1\u540d\u79f0\u6216\u5173\u952e\u8bcd\uff0c\u5982 \u6caa\u6df1300"
_FUND_SEARCH_BTN = "\u641c\u7d22\u57fa\u91d1"
_FUND_QUERY_BY_CODE = "\u6309\u57fa\u91d1\u4ee3\u7801\u67e5\u8be2"
_FUND_SEARCH_BY_KEYWORD = "\u6309\u5173\u952e\u8bcd\u641c\u7d22"
_FUND_CODE_INVALID = "\u57fa\u91d1\u4ee3\u7801\u5e94\u4e3a6\u4f4d\u6570\u5b57"
_FUND_INPUT_EMPTY = "\u8bf7\u8f93\u5165\u57fa\u91d1\u4ee3\u7801"
_FUND_TOO_MANY = "\u6700\u591a\u652f\u6301\u67e5\u8be2 10 \u53ea\u57fa\u91d1"
_FUND_QUERYING = "\u6b63\u5728\u67e5\u8be2\u57fa\u91d1 {} ..."
_FUND_QUERY_FAIL = "\u67e5\u8be2\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u57fa\u91d1\u4ee3\u7801"
_FUND_SEARCH_FAIL = "\u641c\u7d22\u5931\u8d25"
_FUND_NO_RESULT = "\u672a\u627e\u5230\u4e0e '{}' \u76f8\u5173\u7684\u57fa\u91d1"
_FUND_SEARCHING = "\u6b63\u5728\u641c\u7d22 '{}' ..."
_FUND_RESULT_TITLE = "\u67e5\u8be2\u7ed3\u679c"
_FUND_SEARCH_TITLE = "\u641c\u7d22\u7ed3\u679c\uff08\u5171 {} \u53ea\uff09"
_FUND_AI_COMPARE_BTN = "AI \u5bf9\u6bd4\u5206\u6790"
_FUND_AI_COMPARE_THINKING = "AI \u6b63\u5728\u5bf9\u6bd4\u5206\u6790..."
_FUND_AI_COMPARE_FAIL = "AI \u5bf9\u6bd4\u5206\u6790\u5931\u8d25\uff1a{}"
_FUND_AI_INTERPRET_BTN = "\u83b7\u53d6 AI \u89e3\u8bfb"
_FUND_AI_INTERPRET_THINKING = "AI \u6b63\u5728\u89e3\u8bfb\u57fa\u91d1\u6570\u636e..."
_FUND_AI_INTERPRET_FAIL = "AI \u89e3\u8bfb\u5931\u8d25\uff1a{}"
_FUND_SEARCH_HINT = "\u63d0\u793a\uff1a\u590d\u5236\u57fa\u91d1\u4ee3\u7801\u5230\u4e0a\u65b9\u8f93\u5165\u6846\u5373\u53ef\u67e5\u770b\u8be6\u7ec6\u6da8\u8dcc\u4fe1\u606f\u3002"

# Video summary mode strings
_VIDEO_HEADER = (
    '<div class="card">'
    '<h2 class="main-title">\U0001f517 \u89c6\u9891\u603b\u7ed3</h2>'
    '<p class="sub-title">'
    '\u7c98\u8d34\u57fa\u91d1\u5b66\u4e60\u76f8\u5173\u7684\u89c6\u9891\u6216\u6587\u7ae0\u94fe\u63a5\uff0c'
    'AI \u5e2e\u4f60\u63d0\u53d6\u6838\u5fc3\u5185\u5bb9\u5e76\u751f\u6210\u601d\u7ef4\u5bfc\u56fe\u3002'
    '</p>'
    '</div>'
)
_VIDEO_PLATFORM_HINT = (
    '<div class="info-box">'
    '<strong>\u652f\u6301\u7684\u5e73\u53f0\uff1a</strong>'
    '\u5c0f\u7ea2\u4e66 | \u6296\u97f3 | B\u7ad9 | \u5fae\u4fe1\u516c\u4f17\u53f7 | \u5176\u4ed6\u7f51\u9875\u94fe\u63a5'
    '</div>'
)
_VIDEO_URL_LABEL = "\u7c98\u8d34\u94fe\u63a5"
_VIDEO_URL_PLACEHOLDER = "\u8bf7\u7c98\u8d34\u89c6\u9891\u6216\u6587\u7ae0\u94fe\u63a5\uff0c\u5982 https://www.bilibili.com/video/BV..."
_VIDEO_PARSE_BTN = "\u89e3\u6790\u94fe\u63a5"
_VIDEO_SUMMARIZE_BTN = "AI \u603b\u7ed3"
_VIDEO_MINDMAP_BTN = "\u751f\u6210\u601d\u7ef4\u5bfc\u56fe"
_VIDEO_EXPORT_BTN = "\u5bfc\u51fa\u56fe\u7247"
_VIDEO_INPUT_EMPTY = "\u8bf7\u8f93\u5165\u94fe\u63a5"
_VIDEO_PARSE_THINKING = "\u6b63\u5728\u89e3\u6790\u94fe\u63a5..."
_VIDEO_SUMMARIZE_THINKING = "AI \u6b63\u5728\u603b\u7ed3\u5185\u5bb9..."
_VIDEO_SUMMARIZE_FAIL = "AI \u603b\u7ed3\u5931\u8d25\uff1a{}"
_VIDEO_PARSE_FAIL = "\u89e3\u6790\u94fe\u63a5\u65f6\u51fa\u9519\uff1a{}"
_VIDEO_NO_CONTENT = "\u94fe\u63a5\u5185\u5bb9\u4e3a\u7a7a\uff0c\u65e0\u6cd5\u603b\u7ed3"
_VIDEO_PARSE_FIRST = "\u8bf7\u5148\u89e3\u6790\u94fe\u63a5"
_VIDEO_PLATFORM_DETECTED = "\u8bc6\u522b\u5230\u5e73\u53f0\uff1a{}\uff0c\u5185\u5bb9\u7c7b\u578b\uff1a{}"
_VIDEO_PARSE_SUCCESS = "\u94fe\u63a5\u89e3\u6790\u6210\u529f\uff01"
_VIDEO_SUMMARY_TITLE = "\U0001f916 AI \u5185\u5bb9\u603b\u7ed3"
_VIDEO_MINDMAP_FAIL = "\u601d\u7ef4\u5bfc\u56fe\u751f\u6210\u5931\u8d25\uff0c\u8bf7\u786e\u4fdd\u5df2\u5b89\u88c5 graphviz"
_VIDEO_EXPORT_FAIL = "\u5bfc\u51fa\u5931\u8d25\uff0c\u8bf7\u786e\u4fdd\u5df2\u5b89\u88c5 Pillow \u5e93"
_VIDEO_HISTORY_BTN = "\u5386\u53f2\u8bb0\u5f55"
_VIDEO_NO_HISTORY = "\u6682\u65e0\u5386\u53f2\u8bb0\u5f55"
_VIDEO_COMBINE_BTN = "\u7efc\u5408\u591a\u7bc7\u603b\u7ed3"
_VIDEO_COMBINE_THINKING = "AI \u6b63\u5728\u7efc\u5408\u591a\u7bc7\u603b\u7ed3..."
_VIDEO_COMBINE_FAIL = "\u7efc\u5408\u5931\u8d25\uff1a{}"
_VIDEO_COMBINE_SELECT = "\u8bf7\u81f3\u5c11\u52fe\u9009 2 \u6761\u8bb0\u5f55"
_VIDEO_DELETE_BTN = "\u5220\u9664"
_VIDEO_DELETED = "\u8bb0\u5f55\u5df2\u5220\u9664"

# Learning plan mode strings
_PLAN_HEADER = (
    '<div class="card">'
    '<h2 class="main-title">\U0001f4da \u5b66\u4e60\u8ba1\u5212</h2>'
    '<p class="sub-title">'
    '\u544a\u8bc9\u6211\u4f60\u7684\u6c34\u5e73\u548c\u5174\u8da3\uff0c'
    'AI \u4e3a\u4f60\u5b9a\u5236\u4e13\u5c5e\u7684\u57fa\u91d1\u5b66\u4e60\u8ba1\u5212\uff08\u5e26\u53c2\u8003\u94fe\u63a5\uff09\u3002'
    '</p>'
    '</div>'
)
_PLAN_LEVEL_LABEL = "\u4f60\u7684\u57fa\u91d1\u5b66\u4e60\u6c34\u5e73"
_PLAN_LEVEL_OPTIONS = {
    "\u96f6\u57fa\u7840": "\u5b8c\u5168\u4e0d\u61c2\u57fa\u91d1\uff0c\u60f3\u4ece\u96f6\u5f00\u59cb\u5b66\u4e60",
    "\u5165\u95e8": "\u4e86\u89e3\u57fa\u672c\u6982\u5ff5\uff0c\u4f46\u8fd8\u4e0d\u6e05\u695a\u600e\u4e48\u5b9e\u64cd",
    "\u8fdb\u9636": "\u6709\u4e00\u5b9a\u7ecf\u9a8c\uff0c\u60f3\u6df1\u5165\u5b66\u4e60\u6295\u8d44\u7b56\u7565",
}
_PLAN_STEP1 = "\u7b2c\u4e00\u6b65\uff1a\u9009\u62e9\u4f60\u7684\u6c34\u5e73"
_PLAN_STEP2 = "\u7b2c\u4e8c\u6b65\uff1a\u9009\u62e9\u611f\u5174\u8da3\u7684\u4e3b\u9898"
_PLAN_TOPIC_HINT = "\u53ef\u4ee5\u9009\u62e9\u4ee5\u4e0b\u9884\u8bbe\u4e3b\u9898\uff0c\u4e5f\u53ef\u4ee5\u81ea\u5df1\u8f93\u5165\uff1a"
_PLAN_PRESET_TOPICS = [
    "\u6307\u6570\u57fa\u91d1", "\u5b9a\u6295\u7b56\u7565", "\u503a\u5238\u57fa\u91d1",
    "\u80a1\u7968\u57fa\u91d1", "\u8d27\u5e01\u57fa\u91d1", "ETF", "\u57fa\u91d1\u7ec4\u5408",
]
_PLAN_CUSTOM_PLACEHOLDER = "\u8f93\u5165\u5176\u4ed6\u611f\u5174\u8da3\u7684\u4e3b\u9898\uff0c\u7528\u9017\u53f7\u5206\u9694"
_PLAN_GEN_BTN = "\u751f\u6210\u5b66\u4e60\u8ba1\u5212"
_PLAN_NO_TOPIC = "\u8bf7\u81f3\u5c11\u9009\u62e9\u6216\u8f93\u5165\u4e00\u4e2a\u611f\u5174\u8da3\u7684\u4e3b\u9898"
_PLAN_GEN_THINKING = "AI \u6b63\u5728\u4e3a\u4f60\u5236\u5b9a\u5b66\u4e60\u8ba1\u5212..."
_PLAN_GEN_FAIL = "\u751f\u6210\u5b66\u4e60\u8ba1\u5212\u5931\u8d25\uff1a{}"
_PLAN_RESULT_TITLE = "\u4f60\u7684\u4e13\u5c5e\u5b66\u4e60\u8ba1\u5212"
_PLAN_DOWNLOAD_BTN = "\u4e0b\u8f7d\u5b66\u4e60\u8ba1\u5212"
_PLAN_EXPORT_BTN = "\u5bfc\u51fa\u56fe\u7247"
_PLAN_EXPORT_FAIL = "\u5bfc\u51fa\u5931\u8d25\uff0c\u8bf7\u786e\u4fdd\u5df2\u5b89\u88c5 Pillow \u5e93"

# Trend analysis mode strings
_TREND_HEADER = (
    '<div class="card">'
    '<h2 class="main-title">\U0001f4ca \u8d70\u52bf\u5206\u6790</h2>'
    '<p class="sub-title">'
    '\u67e5\u770b\u591a\u53ea\u57fa\u91d1\u7684\u51c0\u503c\u8d70\u52bf\u5bf9\u6bd4\uff0c'
    'AI \u5e2e\u4f60\u5206\u6790\u8d8b\u52bf\u548c\u6ce2\u52a8\u7279\u5f81\u3002'
    '</p>'
    '</div>'
)
_TREND_CODE_PLACEHOLDER = "\u8f93\u5165\u57fa\u91d1\u4ee3\u7801\uff0c\u591a\u4e2a\u7528\u9017\u53f7\u6216\u7a7a\u683c\u5206\u9694\uff08\u6700\u591a5\u4e2a\uff09"
_TREND_DAYS_LABEL = "\u67e5\u8be2\u5929\u6570"
_TREND_DAYS_OPTIONS = [7, 15, 30, 60, 90, 180]
_TREND_ANALYSIS_BTN = "\u5206\u6790\u8d70\u52bf"
_TREND_AI_BTN = "\u83b7\u53d6 AI \u5bf9\u6bd4\u5206\u6790"
_TREND_AI_THINKING = "AI \u6b63\u5728\u5bf9\u6bd4\u5206\u6790\u591a\u53ea\u57fa\u91d1\u8d70\u52bf..."
_TREND_AI_FAIL = "AI \u5206\u6790\u5931\u8d25\uff1a{}"
_TREND_CODE_INVALID = "\u57fa\u91d1\u4ee3\u7801\u5e94\u4e3a6\u4f4d\u6570\u5b57"
_TREND_TOO_MANY = "\u6700\u591a\u652f\u6301 5 \u53ea\u57fa\u91d1\u5bf9\u6bd4"
_TREND_INPUT_EMPTY = "\u8bf7\u8f93\u5165\u57fa\u91d1\u4ee3\u7801"
_TREND_FETCHING = "\u6b63\u5728\u83b7\u53d6\u57fa\u91d1 {} \u6700\u8fd1 {} \u5929\u7684\u51c0\u503c\u6570\u636e..."
_TREND_FETCH_FAIL = "\u83b7\u53d6\u5386\u53f2\u51c0\u503c\u6570\u636e\u5931\u8d25"
_TREND_NO_DATA = "\u672a\u83b7\u53d6\u5230\u5386\u53f2\u51c0\u503c\u6570\u636e"

# Common labels
_LABEL_DATE = "\u65e5\u671f"
_LABEL_UNIT_NAV = "\u5355\u4f4d\u51c0\u503c"
_LABEL_ACC_NAV = "\u7d2f\u8ba1\u51c0\u503c"
_LABEL_DAY_CHANGE = "\u65e5\u6da8\u8dcc\u5e45"
_LABEL_FUND_CODE = "\u57fa\u91d1\u4ee3\u7801"
_LABEL_FUND_NAME = "\u57fa\u91d1\u540d\u79f0"
_LABEL_FUND_TYPE = "\u57fa\u91d1\u7c7b\u578b"
_LABEL_FUND_COMPANY = "\u57fa\u91d1\u516c\u53f8"
_LABEL_SETUP_DATE = "\u6210\u7acb\u65e5\u671f"
_LABEL_FUND_MANAGER = "\u57fa\u91d1\u7ecf\u7406"
_LABEL_ESTIMATE_TIME = "\u4f30\u503c\u65f6\u95f4"
_LABEL_LATEST_NAV = "\u6700\u65b0\u51c0\u503c"
_LABEL_CHANGE = "\u6da8\u8dcc\u5e45\uff1a"
_LABEL_PERIOD_CHANGE = "\u533a\u95f4\u6da8\u8dcc\u5e45"
_LABEL_HIGHEST = "\u6700\u9ad8\u51c0\u503c"
_LABEL_LOWEST = "\u6700\u4f4e\u51c0\u503c"
_LABEL_NA = "\u6682\u65e0"
_LABEL_NA_DATA = "\u6682\u65e0\u6570\u636e"
_LABEL_PLATFORM = "\u5e73\u53f0\uff1a"
_LABEL_CONTENT_TYPE = "\u7c7b\u578b\uff1a"
_LABEL_TITLE = "\u6807\u98c8\uff1a"
_LABEL_CONTENT_EXPAND = "\u67e5\u770b\u63d0\u53d6\u7684\u539f\u6587\u5185\u5bb9"
_LABEL_CONTENT_AREA = "\u539f\u6587\u5185\u5bb9"
_LABEL_HISTORY_EXPAND = "\u67e5\u770b\u5386\u53f2\u51c0\u503c\u6570\u636e"
_LABEL_DAYS_FMT = "\u6700\u8fd1 {} \u5929"
_LABEL_QUESTION = "\u95ee\u9898\uff1a"
_LABEL_ANSWER = "\u56de\u7b54\uff1a"
_LABEL_TIME = "\u65f6\u95f4\uff1a"


# ==================== Session State Init ====================
def init_session_state():
    """Initialize all session_state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "mode" not in st.session_state:
        st.session_state.mode = _MODE_CHAT
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if "api_initialized" not in st.session_state:
        st.session_state.api_initialized = False
    if "trend_data" not in st.session_state:
        st.session_state.trend_data = None
    if "video_result" not in st.session_state:
        st.session_state.video_result = None
    if "fund_query_results" not in st.session_state:
        st.session_state.fund_query_results = []
    if "fund_search_result" not in st.session_state:
        st.session_state.fund_search_result = None
    if "trend_analysis" not in st.session_state:
        st.session_state.trend_analysis = None
    if "fund_compare_result" not in st.session_state:
        st.session_state.fund_compare_result = None
    if "video_summary" not in st.session_state:
        st.session_state.video_summary = None
    if "video_mindmap_path" not in st.session_state:
        st.session_state.video_mindmap_path = None
    if "learning_plan" not in st.session_state:
        st.session_state.learning_plan = None
    if "fund_interpretation" not in st.session_state:
        st.session_state.fund_interpretation = None


init_session_state()

# Initialize persistent storage
try:
    init_storage()
except Exception:
    pass  # Storage init failure is non-fatal


# ==================== Helper Functions ====================

def check_api_key():
    """
    Check whether the API key is configured and try to initialize the client.

    Returns:
        bool: True if initialization succeeded.
    """
    if st.session_state.api_initialized:
        return True

    api_key = st.session_state.api_key
    if not api_key:
        return False

    try:
        os.environ["DEEPSEEK_API_KEY"] = api_key
        init_api_client()
        st.session_state.api_initialized = True
        return True
    except ValueError:
        st.session_state.api_initialized = False
        return False


def format_change_color(value_str):
    """
    Return colored HTML span based on the change percentage value.

    Args:
        value_str: A string representing the change percentage.

    Returns:
        str: HTML string with color styling.
    """
    try:
        value = float(value_str)
        if value > 0:
            return '<span class="rise">+{:.2f}%</span>'.format(value)
        elif value < 0:
            return '<span class="fall">{:.2f}%</span>'.format(value)
        else:
            return '<span class="flat">0.00%</span>'
    except (ValueError, TypeError):
        return str(value_str)


def show_api_warning():
    """Display a warning that the API key is not configured."""
    st.markdown(_API_WARNING_HTML, unsafe_allow_html=True)


def show_risk_warning():
    """Display a risk disclaimer message."""
    st.markdown(_RISK_WARNING_HTML, unsafe_allow_html=True)


def parse_fund_codes(input_str):
    """
    Parse a string of fund codes separated by commas or spaces.

    Args:
        input_str: Raw input string containing fund codes.

    Returns:
        list: List of stripped, validated 6-digit fund code strings.
    """
    # Split by comma, space, or Chinese comma
    parts = re.split(r'[,，\s]+', input_str.strip())
    codes = []
    for part in parts:
        part = part.strip()
        if part and len(part) == 6 and part.isdigit():
            codes.append(part)
    return codes


def export_as_image(text_content, title, download_label):
    """
    Export text content as a PNG image and provide a download button.

    Args:
        text_content: The text to render.
        title: Title displayed on the image.
        download_label: Label for the download button.
    """
    try:
        img_bytes = export_text_to_image(text_content, title=title)
        if img_bytes:
            st.download_button(
                label=download_label,
                data=img_bytes,
                file_name="FundWise_export.png",
                mime="image/png",
            )
        else:
            st.warning(_CHAT_EXPORT_FAIL)
    except Exception as e:
        st.warning("{}: {}".format(_CHAT_EXPORT_FAIL, e))


# ==================== Sidebar ====================
def render_sidebar():
    """Render the sidebar content including navigation and settings."""

    # App title
    _title_html = (
        '<div style="text-align: center; padding: 16px 0;">'
        '<h1 style="font-size: 1.6rem; margin-bottom: 4px;">{}</h1>'
        '<p style="font-size: 0.85rem; opacity: 0.7;">{}</p>'
        '</div>'
    ).format(_APP_TITLE, _APP_SUBTITLE)
    st.markdown(_title_html, unsafe_allow_html=True)
    st.markdown("---")

    # Mode selection
    st.markdown("#### {}".format(_NAV_LABEL))
    mode = st.radio(
        label=_NAV_RADIO_LABEL,
        options=_MODE_OPTIONS,
        label_visibility="collapsed",
        index=_MODE_OPTIONS.index(st.session_state.mode),
        key="mode_selector",
    )
    st.session_state.mode = mode
    st.markdown("---")

    # API settings
    with st.expander(_API_EXPANDER, expanded=False):
        api_key_input = st.text_input(
            label=_API_INPUT_LABEL,
            type="password",
            value=st.session_state.api_key,
            placeholder=_API_INPUT_PLACEHOLDER,
            help=_API_INPUT_HELP,
        )

        if api_key_input != st.session_state.api_key:
            st.session_state.api_key = api_key_input
            st.session_state.api_initialized = False
            if api_key_input:
                if check_api_key():
                    st.success(_API_SUCCESS)
                else:
                    st.error(_API_FAIL)

        if st.session_state.api_initialized:
            st.markdown(
                '<div class="success-box">{}</div>'.format(_API_CONNECTED),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="error-box">{}</div>'.format(_API_NOT_CONFIGURED),
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # About section
    with st.expander(_ABOUT_EXPANDER, expanded=False):
        st.markdown(_ABOUT_TEXT)
        st.markdown("---")
        st.markdown(_DISCLAIMER_TEXT, unsafe_allow_html=True)


# ==================== Mode 1: Chat Q&A (v2.0) ====================
def render_chat_mode():
    """Render the intelligent Q&A chat interface with history and export."""
    st.markdown(_CHAT_HEADER, unsafe_allow_html=True)

    # Check API key
    if not check_api_key():
        show_api_warning()
        st.info("\u914d\u7f6e API Key \u540e\u5373\u53ef\u5f00\u59cb\u5bf9\u8bdd\u3002")
        return

    # Display chat history
    for msg in st.session_state.chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        with st.chat_message(role):
            st.markdown(content)

    # Welcome message (only when no history)
    if not st.session_state.chat_history:
        with st.chat_message("assistant"):
            st.markdown(_CHAT_WELCOME)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": _CHAT_WELCOME}
            )

    # User input
    if prompt := st.chat_input(_CHAT_INPUT_PLACEHOLDER):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # Call AI for answer with references
        with st.chat_message("assistant"):
            with st.spinner(_CHAT_THINKING):
                try:
                    # Build conversation history (exclude the last user message)
                    history_for_api = [
                        m for m in st.session_state.chat_history
                        if m["role"] in ("user", "assistant")
                    ][:-1]

                    response = answer_question_with_references(
                        prompt, chat_history=history_for_api
                    )
                    st.markdown(response)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": response}
                    )

                    # Auto-save to storage
                    try:
                        save_chat_record(
                            question=prompt,
                            answer=response,
                            references=[],
                        )
                    except Exception:
                        pass  # Storage save failure is non-fatal

                except Exception as e:
                    _err = _CHAT_ERROR.format(e)
                    st.error(_err)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": _err}
                    )

    # Clear chat button
    if st.session_state.chat_history:
        if st.button(_CHAT_CLEAR_BTN, key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()

    # History records section
    st.markdown("---")
    if st.button(_CHAT_HISTORY_BTN, key="toggle_chat_history"):
        st.session_state.show_chat_history = not st.session_state.get(
            "show_chat_history", False
        )
        st.rerun()

    if st.session_state.get("show_chat_history", False):
        _render_chat_history()


def _render_chat_history():
    """Render the chat history list with view, export, and delete actions."""
    try:
        records = get_all_chat_records()
    except Exception:
        st.warning(_CHAT_NO_HISTORY)
        return

    if not records:
        st.info(_CHAT_NO_HISTORY)
        return

    for record in records:
        record_id = record.get("id", "")
        question = record.get("question", "")
        answer = record.get("answer", "")
        timestamp = record.get("timestamp", "")

        # Display record summary
        with st.expander(
            "{} | {}".format(question[:50], timestamp),
            expanded=False,
        ):
            st.markdown("**{}** {}".format(_LABEL_QUESTION, question))
            st.markdown("**{}**".format(_LABEL_ANSWER))
            st.markdown(answer)
            st.markdown("*{} {}*".format(_LABEL_TIME, timestamp))

            col1, col2 = st.columns(2)
            with col1:
                export_as_image(
                    text_content="Q: {}\n\nA: {}".format(question, answer),
                    title="FundWise Q&A",
                    download_label=_CHAT_EXPORT_BTN,
                )
            with col2:
                if st.button(
                    _CHAT_DELETE_BTN,
                    key="del_chat_{}".format(record_id),
                ):
                    try:
                        delete_chat_record(record_id)
                        st.success(_CHAT_DELETED)
                        st.rerun()
                    except Exception:
                        st.error(_CHAT_DELETED)


# ==================== Mode 2: Fund Query (v2.0) ====================
def render_fund_query_mode():
    """Render the fund query mode with multi-fund support and AI comparison."""
    st.markdown(_FUND_HEADER, unsafe_allow_html=True)

    col_query, col_search = st.columns([2, 1])

    with col_query:
        st.markdown("#### {}".format(_FUND_QUERY_BY_CODE))
        fund_codes_input = st.text_input(
            label=_FUND_CODE_LABEL,
            placeholder=_FUND_CODE_PLACEHOLDER,
            key="fund_code_input",
            label_visibility="collapsed",
        )
        if st.button(
            _FUND_QUERY_BTN,
            key="query_fund_btn",
            use_container_width=True,
        ):
            if not fund_codes_input or not fund_codes_input.strip():
                st.warning(_FUND_INPUT_EMPTY)
            else:
                codes = parse_fund_codes(fund_codes_input)
                if not codes:
                    st.error(_FUND_CODE_INVALID)
                elif len(codes) > 10:
                    st.warning(_FUND_TOO_MANY)
                else:
                    _query_funds_by_codes(codes)

    with col_search:
        st.markdown("#### {}".format(_FUND_SEARCH_BY_KEYWORD))
        keyword = st.text_input(
            label=_FUND_KEYWORD_LABEL,
            placeholder=_FUND_KEYWORD_PLACEHOLDER,
            key="fund_keyword_input",
            label_visibility="collapsed",
        )
        if st.button(
            _FUND_SEARCH_BTN,
            key="search_fund_btn",
            use_container_width=True,
        ):
            if not keyword or not keyword.strip():
                st.warning("\u8bf7\u8f93\u5165\u641c\u7d22\u5173\u952e\u8bcd")
            else:
                _search_fund_by_keyword(keyword.strip())

    # Display multi-fund query results
    if st.session_state.fund_query_results:
        _display_multi_fund_results()

    # Display search result
    if st.session_state.fund_search_result:
        _display_search_result(st.session_state.fund_search_result)


def _query_funds_by_codes(codes):
    """Query multiple funds by their codes and store results."""
    results = []
    for code in codes:
        _msg = _FUND_QUERYING.format(code)
        with st.spinner(_msg):
            overview = get_fund_overview(code)

            if not overview.get("success"):
                st.error(
                    overview.get("message", _FUND_QUERY_FAIL)
                )
                continue

            basic = overview.get("basic_info", {})
            realtime = overview.get("realtime", {})
            nav_detail = overview.get("nav_detail", {})

            results.append({
                "code": code,
                "basic": basic,
                "realtime": realtime,
                "nav_detail": nav_detail,
            })

    st.session_state.fund_query_results = results
    st.session_state.fund_search_result = None
    st.session_state.fund_compare_result = None
    st.session_state.fund_interpretation = None
    st.rerun()


def _search_fund_by_keyword(keyword):
    """Search funds by keyword."""
    _msg = _FUND_SEARCHING.format(keyword)
    with st.spinner(_msg):
        search_result = search_fund(keyword, page_size=10)

        if not search_result.get("success"):
            st.error(search_result.get("message", _FUND_SEARCH_FAIL))
            st.session_state.fund_search_result = None
            return

        if not search_result.get("results"):
            _warn = _FUND_NO_RESULT.format(keyword)
            st.warning(_warn)
            st.session_state.fund_search_result = None
            return

        st.session_state.fund_search_result = search_result["results"]
        st.session_state.fund_query_results = []
        st.rerun()


def _display_multi_fund_results():
    """Display multiple fund query results as a table with AI comparison."""
    results = st.session_state.fund_query_results
    st.markdown("---")
    st.markdown("### {}".format(_FUND_RESULT_TITLE))

    # Build table data
    table_data = []
    fund_data_for_ai = []
    for r in results:
        basic = r.get("basic", {})
        realtime = r.get("realtime", {})
        nav_detail = r.get("nav_detail", {})

        fund_name = (
            basic.get("fund_name")
            or realtime.get("fund_name")
            or _LABEL_NA
        )
        fund_type = basic.get("fund_type", _LABEL_NA)
        nav = realtime.get("nav") or nav_detail.get("unit_nav", _LABEL_NA)
        acc_nav = nav_detail.get("acc_nav", _LABEL_NA)
        change_percent = (
            realtime.get("change_percent")
            or nav_detail.get("day_change_percent", "")
        )

        table_data.append({
            _LABEL_FUND_CODE: r["code"],
            _LABEL_FUND_NAME: fund_name,
            _LABEL_FUND_TYPE: fund_type,
            _LABEL_UNIT_NAV: nav,
            _LABEL_ACC_NAV: acc_nav,
            _LABEL_DAY_CHANGE: change_percent,
        })

        fund_data_for_ai.append({
            "fund_name": fund_name,
            "fund_code": r["code"],
            "fund_type": fund_type,
            "nav": nav,
            "acc_nav": acc_nav,
            "nav_change_percent": change_percent,
            "fund_company": basic.get("fund_company", ""),
            "manager": basic.get("manager", ""),
        })

    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    # AI comparison button (when multiple funds)
    if len(results) > 1 and check_api_key():
        st.markdown("---")
        st.markdown("### \U0001f916 AI \u5bf9\u6bd4\u5206\u6790")
        if st.button(_FUND_AI_COMPARE_BTN, key="ai_compare_btn"):
            with st.spinner(_FUND_AI_COMPARE_THINKING):
                try:
                    comparison = compare_funds(fund_data_for_ai)
                    st.session_state.fund_compare_result = comparison
                except Exception as e:
                    st.error(_FUND_AI_COMPARE_FAIL.format(e))

        if st.session_state.fund_compare_result:
            _html = (
                '<div class="card">{}</div>'
            ).format(
                st.session_state.fund_compare_result.replace("\n", "<br>")
            )
            st.markdown(_html, unsafe_allow_html=True)

    # Single fund AI interpretation
    elif len(results) == 1 and check_api_key():
        r = results[0]
        basic = r.get("basic", {})
        realtime = r.get("realtime", {})
        nav_detail = r.get("nav_detail", {})
        nav = realtime.get("nav") or nav_detail.get("unit_nav", "")

        if nav:
            st.markdown("---")
            st.markdown("### \U0001f916 AI \u901a\u4fd7\u89e3\u8bfb")
            if st.button(_FUND_AI_INTERPRET_BTN, key="interpret_btn"):
                with st.spinner(_FUND_AI_INTERPRET_THINKING):
                    try:
                        fund_data_for_ai = {
                            "fund_name": (
                                basic.get("fund_name")
                                or realtime.get("fund_name")
                                or _LABEL_NA
                            ),
                            "fund_code": r["code"],
                            "fund_type": basic.get("fund_type", ""),
                            "nav": nav,
                            "acc_nav": nav_detail.get("acc_nav", ""),
                            "nav_change_percent": (
                                realtime.get("change_percent")
                                or nav_detail.get("day_change_percent", "")
                            ),
                            "nav_change": (
                                realtime.get("change_amount")
                                or nav_detail.get("day_change_amount", "")
                            ),
                            "nav_date": (
                                realtime.get("nav_date")
                                or nav_detail.get("nav_date", "")
                            ),
                            "fund_company": basic.get("fund_company", ""),
                            "manager": basic.get("manager", ""),
                        }
                        interpretation = interpret_fund_data(fund_data_for_ai)
                        st.session_state.fund_interpretation = interpretation
                    except Exception as e:
                        st.error(_FUND_AI_INTERPRET_FAIL.format(e))

            if st.session_state.fund_interpretation:
                _html = (
                    '<div class="card">{}</div>'
                ).format(
                    st.session_state.fund_interpretation.replace("\n", "<br>")
                )
                st.markdown(_html, unsafe_allow_html=True)

    show_risk_warning()


def _display_search_result(results):
    """Display the fund search results as a table."""
    st.markdown("---")
    _title = _FUND_SEARCH_TITLE.format(len(results))
    st.markdown(_title)

    table_data = []
    for item in results:
        table_data.append({
            _LABEL_FUND_CODE: item.get("fund_code", ""),
            _LABEL_FUND_NAME: item.get("fund_name", ""),
            _LABEL_FUND_TYPE: item.get("fund_type", ""),
        })

    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            _LABEL_FUND_CODE: st.column_config.TextColumn(
                _LABEL_FUND_CODE, width="small"
            ),
            _LABEL_FUND_NAME: st.column_config.TextColumn(
                _LABEL_FUND_NAME
            ),
            _LABEL_FUND_TYPE: st.column_config.TextColumn(
                _LABEL_FUND_TYPE, width="small"
            ),
        },
    )

    st.info(_FUND_SEARCH_HINT)


# ==================== Mode 3: Video Summary (v2.0) ====================
def render_video_summary_mode():
    """Render the video/article summary mode with mindmap and history."""
    st.markdown(_VIDEO_HEADER, unsafe_allow_html=True)
    st.markdown(_VIDEO_PLATFORM_HINT, unsafe_allow_html=True)

    # URL input
    url = st.text_input(
        label=_VIDEO_URL_LABEL,
        placeholder=_VIDEO_URL_PLACEHOLDER,
        key="video_url_input",
        label_visibility="collapsed",
    )

    col_parse, col_summarize = st.columns(2)

    with col_parse:
        if st.button(
            _VIDEO_PARSE_BTN,
            key="parse_link_btn",
            use_container_width=True,
        ):
            if not url or not url.strip():
                st.warning(_VIDEO_INPUT_EMPTY)
            else:
                _parse_video_link(url.strip())

    with col_summarize:
        if st.button(
            _VIDEO_SUMMARIZE_BTN,
            key="summarize_btn",
            use_container_width=True,
        ):
            if not check_api_key():
                show_api_warning()
            elif not st.session_state.video_result:
                st.warning(_VIDEO_PARSE_FIRST)
            elif not st.session_state.video_result.get("content"):
                st.warning(_VIDEO_NO_CONTENT)
            else:
                _summarize_video_content()

    # Display video result
    if st.session_state.video_result:
        _display_video_result()

    # History records section
    st.markdown("---")
    if st.button(_VIDEO_HISTORY_BTN, key="toggle_video_history"):
        st.session_state.show_video_history = not st.session_state.get(
            "show_video_history", False
        )
        st.rerun()

    if st.session_state.get("show_video_history", False):
        _render_video_history()


def _parse_video_link(url):
    """Parse a video or article link."""
    with st.spinner(_VIDEO_PARSE_THINKING):
        try:
            platform_info = detect_platform(url)
            platform_name = platform_info.get("platform_name", _LABEL_NA)
            content_type = platform_info.get("type", _LABEL_NA)
            _info = _VIDEO_PLATFORM_DETECTED.format(
                platform_name, content_type
            )
            st.info(_info)

            result = parse_link(url)
            st.session_state.video_result = result
            st.session_state.video_summary = None
            st.session_state.video_mindmap_path = None

            if result.get("success"):
                st.success(_VIDEO_PARSE_SUCCESS)
            else:
                st.warning(result.get("message", "\u89e3\u6790\u5931\u8d25"))
        except Exception as e:
            st.error(_VIDEO_PARSE_FAIL.format(e))
            st.session_state.video_result = None


def _summarize_video_content():
    """Call AI to summarize the parsed video content and save to storage."""
    result = st.session_state.video_result
    with st.spinner(_VIDEO_SUMMARIZE_THINKING):
        try:
            content = result.get("content", "")
            platform_name = result.get("platform_name", "")
            title = result.get("title", "")
            summary = summarize_content(content, platform=platform_name)
            st.session_state.video_summary = summary

            # Save to storage
            try:
                save_video_summary(
                    url=result.get("url", ""),
                    platform=platform_name,
                    title=title,
                    summary=summary,
                )
            except Exception:
                pass  # Storage save failure is non-fatal

        except Exception as e:
            st.error(_VIDEO_SUMMARIZE_FAIL.format(e))


def _display_video_result():
    """Display the video parsing and summary results with mindmap and export."""
    result = st.session_state.video_result

    st.markdown("---")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("**{}**".format(_LABEL_PLATFORM))
    with col2:
        st.markdown(result.get("platform_name", _LABEL_NA))

    with col1:
        st.markdown("**{}**".format(_LABEL_CONTENT_TYPE))
    with col2:
        st.markdown(result.get("type", _LABEL_NA))

    if result.get("title"):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**{}**".format(_LABEL_TITLE))
        with col2:
            st.markdown("**{}**".format(result["title"]))

    if result.get("content"):
        with st.expander(_LABEL_CONTENT_EXPAND, expanded=False):
            st.text_area(
                label=_LABEL_CONTENT_AREA,
                value=result["content"],
                height=300,
                label_visibility="collapsed",
                disabled=True,
            )

    if result.get("message"):
        st.info(result["message"])

    # AI summary result
    if st.session_state.video_summary:
        st.markdown("---")
        st.markdown("### {}".format(_VIDEO_SUMMARY_TITLE))
        _summary_html = (
            '<div class="card">{}</div>'
        ).format(
            st.session_state.video_summary.replace("\n", "<br>")
        )
        st.markdown(_summary_html, unsafe_allow_html=True)

        # Mindmap and export buttons
        col_mind, col_export = st.columns(2)
        with col_mind:
            if st.button(_VIDEO_MINDMAP_BTN, key="gen_mindmap_btn"):
                try:
                    mindmap_path = generate_mindmap(
                        st.session_state.video_summary
                    )
                    if mindmap_path:
                        st.session_state.video_mindmap_path = mindmap_path
                    else:
                        st.warning(_VIDEO_MINDMAP_FAIL)
                except Exception:
                    st.warning(_VIDEO_MINDMAP_FAIL)

        with col_export:
            export_as_image(
                text_content=st.session_state.video_summary,
                title=result.get("title", "FundWise Video Summary"),
                download_label=_VIDEO_EXPORT_BTN,
            )

        # Display mindmap image
        if st.session_state.video_mindmap_path:
            try:
                st.image(st.session_state.video_mindmap_path)
            except Exception:
                st.warning(_VIDEO_MINDMAP_FAIL)


def _render_video_history():
    """Render the video summary history with multi-select and combine."""
    try:
        records = get_all_video_summaries()
    except Exception:
        st.info(_VIDEO_NO_HISTORY)
        return

    if not records:
        st.info(_VIDEO_NO_HISTORY)
        return

    # Multi-select for combining summaries
    selected_ids = st.multiselect(
        label="\u52fe\u9009\u8981\u7efc\u5408\u7684\u8bb0\u5f55",
        options=[r.get("id", "") for r in records],
        format_func=lambda x: _get_video_record_label(records, x),
        key="video_history_multiselect",
    )

    if len(selected_ids) >= 2 and check_api_key():
        if st.button(_VIDEO_COMBINE_BTN, key="combine_summaries_btn"):
            with st.spinner(_VIDEO_COMBINE_THINKING):
                try:
                    summaries = []
                    for rid in selected_ids:
                        rec = get_video_summary(rid)
                        if rec and rec.get("summary"):
                            summaries.append(rec["summary"])
                    combined = combine_summaries(summaries)
                    st.session_state.video_combined = combined
                except Exception as e:
                    st.error(_VIDEO_COMBINE_FAIL.format(e))
    elif len(selected_ids) == 1:
        st.info(_VIDEO_COMBINE_SELECT)

    # Display combined result
    if st.session_state.get("video_combined"):
        st.markdown("---")
        st.markdown("### \U0001f916 \u7efc\u5408\u603b\u7ed3")
        _html = (
            '<div class="card">{}</div>'
        ).format(st.session_state.video_combined.replace("\n", "<br>"))
        st.markdown(_html, unsafe_allow_html=True)
        export_as_image(
            text_content=st.session_state.video_combined,
            title="FundWise Combined Summary",
            download_label=_VIDEO_EXPORT_BTN,
        )

    # Display individual records
    for record in records:
        record_id = record.get("id", "")
        title = record.get("title", "")
        platform = record.get("platform", "")
        summary = record.get("summary", "")
        timestamp = record.get("timestamp", "")

        with st.expander(
            "{} | {} | {}".format(title or _LABEL_NA, platform, timestamp),
            expanded=False,
        ):
            st.markdown(summary)

            col1, col2 = st.columns(2)
            with col1:
                export_as_image(
                    text_content=summary,
                    title=title or "FundWise Summary",
                    download_label=_VIDEO_EXPORT_BTN,
                )
            with col2:
                if st.button(
                    _VIDEO_DELETE_BTN,
                    key="del_video_{}".format(record_id),
                ):
                    try:
                        delete_video_summary(record_id)
                        st.success(_VIDEO_DELETED)
                        st.rerun()
                    except Exception:
                        st.error(_VIDEO_DELETED)


def _get_video_record_label(records, record_id):
    """Get a display label for a video record given its ID."""
    for r in records:
        if r.get("id") == record_id:
            title = r.get("title", "")
            platform = r.get("platform", "")
            ts = r.get("timestamp", "")
            return "{} | {} | {}".format(
                title[:30] if title else _LABEL_NA, platform, ts
            )
    return record_id


# ==================== Mode 4: Learning Plan (v2.0) ====================
def render_learning_plan_mode():
    """Render the learning plan generation mode with links and export."""
    st.markdown(_PLAN_HEADER, unsafe_allow_html=True)

    # Check API key
    if not check_api_key():
        show_api_warning()
        st.info("\u914d\u7f6e API Key \u540e\u5373\u53ef\u751f\u6210\u5b66\u4e60\u8ba1\u5212\u3002")
        return

    # Level selection
    st.markdown("#### {}".format(_PLAN_STEP1))
    level = st.radio(
        label=_PLAN_LEVEL_LABEL,
        options=list(_PLAN_LEVEL_OPTIONS.keys()),
        format_func=lambda x: "{} - {}".format(
            x, _PLAN_LEVEL_OPTIONS[x]
        ),
        horizontal=True,
    )

    # Interest topics
    st.markdown("#### {}".format(_PLAN_STEP2))
    st.markdown(_PLAN_TOPIC_HINT)

    selected_topics = st.multiselect(
        label="\u9884\u8bbe\u4e3b\u9898\uff08\u53ef\u591a\u9009\uff09",
        options=_PLAN_PRESET_TOPICS,
        label_visibility="collapsed",
    )

    custom_topic = st.text_input(
        label="\u81ea\u5b9a\u4e49\u4e3b\u9898",
        placeholder=_PLAN_CUSTOM_PLACEHOLDER,
        key="custom_topic_input",
    )

    # Merge topics
    all_topics = list(selected_topics)
    if custom_topic:
        custom_list = [t.strip() for t in custom_topic.split(",") if t.strip()]
        all_topics.extend(custom_list)

    # Generate button
    st.markdown("---")
    if st.button(
        _PLAN_GEN_BTN,
        key="gen_plan_btn",
        use_container_width=True,
    ):
        if not all_topics:
            st.warning(_PLAN_NO_TOPIC)
        else:
            with st.spinner(_PLAN_GEN_THINKING):
                try:
                    history = []
                    if st.session_state.chat_history:
                        history = [
                            m for m in st.session_state.chat_history
                            if m["role"] in ("user", "assistant")
                        ]
                    plan = generate_learning_plan_with_links(
                        user_level=level,
                        interests=all_topics,
                        chat_history=history,
                    )
                    st.session_state.learning_plan = plan
                except Exception as e:
                    st.error(_PLAN_GEN_FAIL.format(e))

    # Display learning plan
    if st.session_state.learning_plan:
        st.markdown("---")
        st.markdown("### {}".format(_PLAN_RESULT_TITLE))
        _plan_html = (
            '<div class="card">{}</div>'
        ).format(st.session_state.learning_plan.replace("\n", "<br>"))
        st.markdown(_plan_html, unsafe_allow_html=True)

        col_download, col_export = st.columns(2)
        with col_download:
            st.download_button(
                label=_PLAN_DOWNLOAD_BTN,
                data=st.session_state.learning_plan,
                file_name="FundWise_\u5b66\u4e60\u8ba1\u5212.txt",
                mime="text/plain",
            )
        with col_export:
            export_as_image(
                text_content=st.session_state.learning_plan,
                title="FundWise Learning Plan",
                download_label=_PLAN_EXPORT_BTN,
            )


# ==================== Mode 5: Trend Analysis (v2.0) ====================
def render_trend_analysis_mode():
    """Render the multi-fund trend analysis mode with comparison chart."""
    st.markdown(_TREND_HEADER, unsafe_allow_html=True)

    col_code, col_days = st.columns([2, 1])

    with col_code:
        trend_codes_input = st.text_input(
            label=_FUND_CODE_LABEL,
            placeholder=_TREND_CODE_PLACEHOLDER,
            key="trend_fund_code_input",
            label_visibility="collapsed",
        )

    with col_days:
        trend_days = st.selectbox(
            label=_TREND_DAYS_LABEL,
            options=_TREND_DAYS_OPTIONS,
            index=2,
            format_func=lambda x: _LABEL_DAYS_FMT.format(x),
            key="trend_days_select",
        )

    if st.button(
        _TREND_ANALYSIS_BTN,
        key="trend_analysis_btn",
        use_container_width=True,
    ):
        if not trend_codes_input or not trend_codes_input.strip():
            st.warning(_TREND_INPUT_EMPTY)
        else:
            codes = parse_fund_codes(trend_codes_input)
            if not codes:
                st.error(_TREND_CODE_INVALID)
            elif len(codes) > 5:
                st.warning(_TREND_TOO_MANY)
            else:
                _fetch_multi_trend_data(codes, trend_days)

    # Display trend analysis
    if st.session_state.trend_data:
        _display_multi_trend_analysis()


def _fetch_multi_trend_data(fund_codes, days):
    """Fetch historical NAV data for multiple funds."""
    all_trend_data = []
    for code in fund_codes:
        _msg = _TREND_FETCHING.format(code, days)
        with st.spinner(_msg):
            basic_info = get_fund_basic_info(code)
            fund_name = basic_info.get("fund_name", "\u57fa\u91d1{}".format(code))

            history = get_fund_history_nav(code, days=days)

            if not history.get("success"):
                st.error(
                    history.get("message", _TREND_FETCH_FAIL)
                )
                continue

            if not history.get("data"):
                st.warning(_TREND_NO_DATA)
                continue

            all_trend_data.append({
                "fund_code": code,
                "fund_name": fund_name,
                "fund_type": basic_info.get("fund_type", ""),
                "days": days,
                "history": history["data"],
            })

    st.session_state.trend_data = all_trend_data
    st.session_state.trend_analysis = None
    st.rerun()


def _display_multi_trend_analysis():
    """Display multi-fund trend comparison chart and AI analysis."""
    all_data = st.session_state.trend_data

    st.markdown("---")

    # Prepare chart data for all funds
    chart_df = pd.DataFrame()
    color_palette = [
        "#667eea", "#f093fb", "#4facfe", "#43e97b", "#fa709a",
    ]

    for idx, data in enumerate(all_data):
        fund_name = data["fund_name"]
        fund_code = data["fund_code"]
        history = data["history"]

        rows = []
        for item in reversed(history):
            try:
                nav_value = float(item.get("unit_nav", 0))
                rows.append({
                    _LABEL_DATE: item.get("date", ""),
                    "{}({})".format(fund_name, fund_code): nav_value,
                })
            except (ValueError, TypeError):
                continue

        if rows:
            fund_df = pd.DataFrame(rows)
            fund_df.set_index(_LABEL_DATE, inplace=True)
            if chart_df.empty:
                chart_df = fund_df
            else:
                chart_df = chart_df.join(fund_df, how="outer")

    if not chart_df.empty:
        st.line_chart(
            chart_df,
            use_container_width=True,
            height=400,
            color=color_palette[:len(all_data)],
        )

        # Key statistics for each fund
        for data in all_data:
            fund_name = data["fund_name"]
            fund_code = data["fund_code"]
            history = data["history"]
            days = data["days"]

            nav_values = []
            for item in reversed(history):
                try:
                    nav_values.append(float(item.get("unit_nav", 0)))
                except (ValueError, TypeError):
                    continue

            if nav_values:
                latest_nav = nav_values[-1]
                highest_nav = max(nav_values)
                lowest_nav = min(nav_values)

                if nav_values[0] != 0:
                    period_change = (
                        (latest_nav - nav_values[0]) / nav_values[0] * 100
                    )
                else:
                    period_change = 0

                st.markdown(
                    "**{}({})** - {}".format(
                        fund_name, fund_code,
                        _LABEL_DAYS_FMT.format(days)
                    )
                )
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        label=_LABEL_LATEST_NAV,
                        value="{:.4f}".format(latest_nav),
                    )
                with col2:
                    st.metric(
                        label=_LABEL_PERIOD_CHANGE,
                        value="{:+.2f}%".format(period_change),
                        delta="{:+.2f}%".format(period_change),
                    )
                with col3:
                    st.metric(
                        label=_LABEL_HIGHEST,
                        value="{:.4f}".format(highest_nav),
                    )
                with col4:
                    st.metric(
                        label=_LABEL_LOWEST,
                        value="{:.4f}".format(lowest_nav),
                    )

        # Historical data table
        with st.expander(_LABEL_HISTORY_EXPAND, expanded=False):
            all_table_data = []
            for data in all_data:
                fund_name = data["fund_name"]
                fund_code = data["fund_code"]
                for item in reversed(data["history"]):
                    change_pct = item.get("day_change_percent", "")
                    try:
                        change_val = float(change_pct)
                        if change_val > 0:
                            change_display = "+{:.2f}%".format(change_val)
                        elif change_val < 0:
                            change_display = "{:.2f}%".format(change_val)
                        else:
                            change_display = "0.00%"
                    except (ValueError, TypeError):
                        change_display = change_pct if change_pct else "-"

                    all_table_data.append({
                        _LABEL_FUND_CODE: fund_code,
                        _LABEL_FUND_NAME: fund_name,
                        _LABEL_DATE: item.get("date", ""),
                        _LABEL_UNIT_NAV: item.get("unit_nav", ""),
                        _LABEL_ACC_NAV: item.get("acc_nav", ""),
                        _LABEL_DAY_CHANGE: change_display,
                    })

            if all_table_data:
                df_table = pd.DataFrame(all_table_data)
                st.dataframe(
                    df_table,
                    use_container_width=True,
                    hide_index=True,
                    height=300,
                )

    # AI multi-fund trend analysis
    if check_api_key() and len(all_data) > 1:
        st.markdown("---")
        st.markdown("### \U0001f916 AI \u5bf9\u6bd4\u5206\u6790")
        if st.button(_TREND_AI_BTN, key="ai_multi_trend_btn"):
            with st.spinner(_TREND_AI_THINKING):
                try:
                    fund_data_list = []
                    for data in all_data:
                        analysis_data = []
                        for item in reversed(data["history"]):
                            analysis_data.append({
                                "date": item.get("date", ""),
                                "nav": item.get("unit_nav", ""),
                                "acc_nav": item.get("acc_nav", ""),
                                "nav_change_percent": item.get(
                                    "day_change_percent", ""
                                ),
                            })
                        fund_data_list.append({
                            "fund_code": data["fund_code"],
                            "fund_name": data["fund_name"],
                            "fund_type": data["fund_type"],
                            "history": analysis_data,
                        })
                    analysis = analyze_multi_fund_trend(fund_data_list)
                    st.session_state.trend_analysis = analysis
                except Exception as e:
                    st.error(_TREND_AI_FAIL.format(e))

        if st.session_state.trend_analysis:
            _html = (
                '<div class="card">{}</div>'
            ).format(
                st.session_state.trend_analysis.replace("\n", "<br>")
            )
            st.markdown(_html, unsafe_allow_html=True)

    # Single fund AI analysis fallback
    elif check_api_key() and len(all_data) == 1:
        data = all_data[0]
        st.markdown("---")
        st.markdown("### \U0001f916 AI \u8d70\u52bf\u5206\u6790")
        if st.button("\u83b7\u53d6 AI \u5206\u6790", key="ai_trend_btn"):
            with st.spinner("AI \u6b63\u5728\u5206\u6790\u8d70\u52bf\u6570\u636e..."):
                try:
                    analysis_data = []
                    for item in reversed(data["history"]):
                        analysis_data.append({
                            "date": item.get("date", ""),
                            "nav": item.get("unit_nav", ""),
                            "acc_nav": item.get("acc_nav", ""),
                            "nav_change_percent": item.get(
                                "day_change_percent", ""
                            ),
                        })
                    analysis = analyze_fund_trend(
                        data["fund_code"], analysis_data
                    )
                    st.session_state.trend_analysis = analysis
                except Exception as e:
                    st.error("AI \u5206\u6790\u5931\u8d25\uff1a{}".format(e))

        if st.session_state.trend_analysis:
            _html = (
                '<div class="card">{}</div>'
            ).format(
                st.session_state.trend_analysis.replace("\n", "<br>")
            )
            st.markdown(_html, unsafe_allow_html=True)

    show_risk_warning()


# ==================== Main ====================
def main():
    """Main entry point: render sidebar and dispatch to the active mode."""

    # Render sidebar
    with st.sidebar:
        render_sidebar()

    # Dispatch to the active mode
    mode = st.session_state.mode

    if mode == _MODE_CHAT:
        render_chat_mode()
    elif mode == _MODE_FUND:
        render_fund_query_mode()
    elif mode == _MODE_VIDEO:
        render_video_summary_mode()
    elif mode == _MODE_PLAN:
        render_learning_plan_mode()
    elif mode == _MODE_TREND:
        render_trend_analysis_mode()


# ==================== Entry Point ====================
if __name__ == "__main__":
    main()
