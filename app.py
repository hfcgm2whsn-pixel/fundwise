# -*- coding: utf-8 -*-
"""
FundWise - Streamlit main application.

Integrates fund data query, AI Q&A, video summary,
learning plan generation, and trend analysis.
"""

import os
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
    answer_question,
    interpret_fund_data,
    summarize_content,
    generate_learning_plan,
    analyze_fund_trend,
)
from video_parser import detect_platform, parse_link


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


# ==================== Session State Init ====================
def init_session_state():
    """Initialize all session_state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "mode" not in st.session_state:
        st.session_state.mode = "\u667a\u80fd\u95ee\u7b54"
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if "api_initialized" not in st.session_state:
        st.session_state.api_initialized = False
    if "trend_data" not in st.session_state:
        st.session_state.trend_data = None
    if "video_result" not in st.session_state:
        st.session_state.video_result = None


init_session_state()


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
        value_str: A string representing the change percentage, e.g. "1.23" or "-0.56".

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
    _html = (
        '<div class="info-box">'
        '<strong>\u63d0\u793a\uff1a</strong>'
        '\u8bf7\u5148\u5728\u5de6\u4fa7\u8fb9\u680f\u7684\u300cAPI \u8bbe\u7f6e\u300d'
        '\u4e2d\u914d\u7f6e DeepSeek API Key\uff0c'
        '\u624d\u80fd\u4f7f\u7528 AI \u667a\u80fd\u95ee\u7b54\u3001\u5185\u5bb9\u603b\u7ed3\u3001'
        '\u5b66\u4e60\u8ba1\u5212\u7b49\u529f\u80fd\u3002'
        '</div>'
    )
    st.markdown(_html, unsafe_allow_html=True)


def show_risk_warning():
    """Display a risk disclaimer message."""
    _html = (
        '<div class="risk-warning">'
        '<strong>\u98ce\u9669\u63d0\u793a\uff1a</strong>'
        '\u4ee5\u4e0a\u5185\u5bb9\u4ec5\u4f9b\u53c2\u8003\uff0c'
        '\u4e0d\u6784\u6210\u4efb\u4f55\u6295\u8d44\u5efa\u8bae\u3002'
        '\u57fa\u91d1\u6295\u8d44\u6709\u98ce\u9669\uff0c'
        '\u8fc7\u5f80\u4e1a\u7ee9\u4e0d\u9884\u793a\u672a\u6765\u6536\u76ca\u3002'
        '\u8bf7\u6839\u636e\u81ea\u8eab\u98ce\u9669\u627f\u53d7\u80fd\u529b\u8c28\u614e\u51b3\u7b56\u3002'
        '</div>'
    )
    st.markdown(_html, unsafe_allow_html=True)


# ==================== Sidebar ====================
def render_sidebar():
    """Render the sidebar content including navigation and settings."""

    # App title
    _title_html = (
        '<div style="text-align: center; padding: 16px 0;">'
        '<h1 style="font-size: 1.6rem; margin-bottom: 4px;">'
        '\U0001f4b0 FundWise</h1>'
        '<p style="font-size: 0.85rem; opacity: 0.7;">'
        '\u57fa\u91d1\u5b66\u4e60\u52a9\u624b</p>'
        '</div>'
    )
    st.markdown(_title_html, unsafe_allow_html=True)
    st.markdown("---")

    # Mode selection
    st.markdown("#### \u529f\u80fd\u5bfc\u822a")
    _mode_options = [
        "\u667a\u80fd\u95ee\u7b54",
        "\u67e5\u6da8\u8dcc",
        "\u89c6\u9891\u603b\u7ed3",
        "\u5b66\u4e60\u8ba1\u5212",
        "\u8d70\u52bf\u5206\u6790",
    ]
    mode = st.radio(
        label="\u9009\u62e9\u529f\u80fd",
        options=_mode_options,
        label_visibility="collapsed",
        index=_mode_options.index(st.session_state.mode),
        key="mode_selector",
    )
    st.session_state.mode = mode
    st.markdown("---")

    # API settings
    with st.expander("\u2699\ufe0f API \u8bbe\u7f6e", expanded=False):
        api_key_input = st.text_input(
            label="DeepSeek API Key",
            type="password",
            value=st.session_state.api_key,
            placeholder="\u8bf7\u8f93\u5165\u60a8\u7684 DeepSeek API Key",
            help="\u5728 https://platform.deepseek.com \u83b7\u53d6 API Key",
        )

        if api_key_input != st.session_state.api_key:
            st.session_state.api_key = api_key_input
            st.session_state.api_initialized = False
            if api_key_input:
                if check_api_key():
                    st.success("API Key \u914d\u7f6e\u6210\u529f\uff01")
                else:
                    st.error("API Key \u65e0\u6548\uff0c\u8bf7\u68c0\u67e5\u540e\u91cd\u8bd5")

        if st.session_state.api_initialized:
            st.markdown(
                '<div class="success-box">API \u5df2\u8fde\u63a5</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="error-box">API \u672a\u914d\u7f6e\uff0cAI \u529f\u80fd\u4e0d\u53ef\u7528</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # About section
    with st.expander("\u2139\ufe0f \u5173\u4e8e", expanded=False):
        st.markdown(
            "**FundWise \u57fa\u91d1\u5b66\u4e60\u52a9\u624b**\n\n"
            "\u4e00\u6b3e\u9762\u5411\u57fa\u91d1\u6295\u8d44\u521d\u5b66\u8005\u7684\u667a\u80fd\u5b66\u4e60\u5de5\u5177\uff0c"
            "\u5e2e\u52a9\u4f60\uff1a\n\n"
            "- \u7528\u5927\u767d\u8bdd\u7406\u89e3\u57fa\u91d1\u77e5\u8bc6\n"
            "- \u968f\u65f6\u67e5\u8be2\u57fa\u91d1\u6da8\u8dcc\n"
            "- \u603b\u7ed3\u57fa\u91d1\u5b66\u4e60\u89c6\u9891/\u6587\u7ae0\n"
            "- \u83b7\u53d6\u4e2a\u6027\u5316\u5b66\u4e60\u8ba1\u5212\n"
            "- \u5206\u6790\u57fa\u91d1\u8d70\u52bf\n\n"
            "**\u7248\u672c\uff1a** v1.0 MVP\n\n"
            "**\u6570\u636e\u6765\u6e90\uff1a** \u5929\u5929\u57fa\u91d1\uff08\u4e1c\u65b9\u8d22\u5bcc\uff09\n\n"
            "**AI \u5f15\u64ce\uff1a** DeepSeek"
        )
        st.markdown("---")
        _disclaimer_html = (
            '<div class="risk-warning" style="font-size: 0.8rem;">'
            '<strong>\u514d\u8d23\u58f0\u660e\uff1a</strong>'
            '\u672c\u5de5\u5177\u63d0\u4f9b\u7684\u4fe1\u606f\u548c\u5185\u5bb9'
            '\u4ec5\u4f9b\u5b66\u4e60\u548c\u53c2\u8003\uff0c'
            '\u4e0d\u6784\u6210\u4efb\u4f55\u6295\u8d44\u5efa\u8bae\u3002'
            '\u57fa\u91d1\u6295\u8d44\u6709\u98ce\u9669\uff0c\u6295\u8d44\u9700\u8c28\u614e\u3002'
            '\u7528\u6237\u5e94\u81ea\u884c\u5224\u65ad\u5e76\u627f\u62c5\u6295\u8d44\u98ce\u9669\u3002'
            '</div>'
        )
        st.markdown(_disclaimer_html, unsafe_allow_html=True)


# ==================== Mode 1: Chat Q&A ====================
def render_chat_mode():
    """Render the intelligent Q&A chat interface."""
    _header_html = (
        '<div class="card">'
        '<h2 class="main-title">\U0001f4ac \u667a\u80fd\u95ee\u7b54</h2>'
        '<p class="sub-title">'
        '\u6709\u4efb\u4f55\u5173\u4e8e\u57fa\u91d1\u7684\u95ee\u9898\uff0c'
        '\u5c3d\u7ba1\u95ee\u6211\uff01\u6211\u4f1a\u7528\u5927\u767d\u8bdd\u5e2e\u4f60\u89e3\u7b54\u3002'
        '</p>'
        '</div>'
    )
    st.markdown(_header_html, unsafe_allow_html=True)

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
            _welcome = (
                "\u4f60\u597d\uff01\u6211\u662f **FundWise \u57fa\u91d1\u5b66\u4e60\u52a9\u624b** \U0001f44b\n\n"
                "\u6211\u53ef\u4ee5\u5e2e\u4f60\uff1a\n"
                "- \u89e3\u91ca\u57fa\u91d1\u76f8\u5173\u6982\u5ff5\uff08\u5982\uff1a\u4ec0\u4e48\u662f\u6307\u6570\u57fa\u91d1\uff1f\uff09\n"
                "- \u89e3\u7b54\u6295\u8d44\u5165\u95e8\u95ee\u9898\uff08\u5982\uff1a\u65b0\u624b\u600e\u4e48\u5f00\u59cb\u4e70\u57fa\u91d1\uff1f\uff09\n"
                "- \u5206\u6790\u57fa\u91d1\u6570\u636e\uff08\u5982\uff1a\u67d0\u53ea\u57fa\u91d1\u4eca\u5929\u6da8\u4e86\u8fd8\u662f\u8dcc\u4e86\uff1f\uff09\n\n"
                "\u6709\u4ec0\u4e48\u60f3\u95ee\u7684\uff0c\u76f4\u63a5\u8f93\u5165\u5c31\u597d\uff01"
            )
            st.markdown(_welcome)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": _welcome}
            )

    # User input
    if prompt := st.chat_input("\u8bf7\u8f93\u5165\u4f60\u7684\u95ee\u9898..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        # Call AI for answer
        with st.chat_message("assistant"):
            with st.spinner("\u601d\u8003\u4e2d..."):
                try:
                    # Build conversation history (exclude the last user message)
                    history_for_api = [
                        m for m in st.session_state.chat_history
                        if m["role"] in ("user", "assistant")
                    ][:-1]

                    response = answer_question(
                        prompt, chat_history=history_for_api
                    )
                    st.markdown(response)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": response}
                    )
                except Exception as e:
                    _err = "\u62b1\u6b49\uff0c\u56de\u7b54\u95ee\u9898\u65f6\u51fa\u9519\u4e86\uff1a{}".format(e)
                    st.error(_err)
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": _err}
                    )

    # Clear chat button
    if st.session_state.chat_history:
        if st.button("\u6e05\u7a7a\u5bf9\u8bdd\u8bb0\u5f55", key="clear_chat"):
            st.session_state.chat_history = []
            st.rerun()


# ==================== Mode 2: Fund Query ====================
def render_fund_query_mode():
    """Render the fund query mode for checking fund prices and changes."""
    _header_html = (
        '<div class="card">'
        '<h2 class="main-title">\U0001f4c8 \u67e5\u6da8\u8dcc</h2>'
        '<p class="sub-title">'
        '\u8f93\u5165\u57fa\u91d1\u4ee3\u7801\u6216\u5173\u952e\u8bcd\uff0c'
        '\u5feb\u901f\u67e5\u770b\u57fa\u91d1\u6700\u65b0\u8868\u73b0\u548c\u901a\u4fd7\u89e3\u8bfb\u3002'
        '</p>'
        '</div>'
    )
    st.markdown(_header_html, unsafe_allow_html=True)

    col_query, col_search = st.columns([1, 1])

    with col_query:
        st.markdown("#### \u6309\u57fa\u91d1\u4ee3\u7801\u67e5\u8be2")
        fund_code = st.text_input(
            label="\u57fa\u91d1\u4ee3\u7801",
            placeholder="\u8bf7\u8f93\u51656\u4f4d\u57fa\u91d1\u4ee3\u7801\uff0c\u5982 000001",
            key="fund_code_input",
            label_visibility="collapsed",
        )
        if st.button("\u67e5\u8be2\u57fa\u91d1", key="query_fund_btn", use_container_width=True):
            if not fund_code or not fund_code.strip():
                st.warning("\u8bf7\u8f93\u5165\u57fa\u91d1\u4ee3\u7801")
            elif len(fund_code.strip()) != 6 or not fund_code.strip().isdigit():
                st.error("\u57fa\u91d1\u4ee3\u7801\u5e94\u4e3a6\u4f4d\u6570\u5b57")
            else:
                _query_fund_by_code(fund_code.strip())

    with col_search:
        st.markdown("#### \u6309\u5173\u952e\u8bcd\u641c\u7d22")
        keyword = st.text_input(
            label="\u641c\u7d22\u5173\u952e\u8bcd",
            placeholder="\u8f93\u5165\u57fa\u91d1\u540d\u79f0\u6216\u5173\u952e\u8bcd\uff0c\u5982 \u6caa\u6df1300",
            key="fund_keyword_input",
            label_visibility="collapsed",
        )
        if st.button("\u641c\u7d22\u57fa\u91d1", key="search_fund_btn", use_container_width=True):
            if not keyword or not keyword.strip():
                st.warning("\u8bf7\u8f93\u5165\u641c\u7d22\u5173\u952e\u8bcd")
            else:
                _search_fund_by_keyword(keyword.strip())

    # Display query result
    if "fund_query_result" in st.session_state and st.session_state.fund_query_result:
        _display_fund_result(st.session_state.fund_query_result)

    # Display search result
    if "fund_search_result" in st.session_state and st.session_state.fund_search_result:
        _display_search_result(st.session_state.fund_search_result)


def _query_fund_by_code(fund_code):
    """Query fund information by fund code."""
    _msg = "\u6b63\u5728\u67e5\u8be2\u57fa\u91d1 {} ...".format(fund_code)
    with st.spinner(_msg):
        overview = get_fund_overview(fund_code)

        if not overview["success"]:
            st.error(overview.get("message", "\u67e5\u8be2\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u57fa\u91d1\u4ee3\u7801"))
            st.session_state.fund_query_result = None
            return

        result = {
            "code": fund_code,
            "basic": overview.get("basic_info", {}),
            "realtime": overview.get("realtime", {}),
            "nav_detail": overview.get("nav_detail", {}),
        }
        st.session_state.fund_query_result = result
        st.session_state.fund_search_result = None
        st.rerun()


def _search_fund_by_keyword(keyword):
    """Search funds by keyword."""
    _msg = "\u6b63\u5728\u641c\u7d22 '{}' ...".format(keyword)
    with st.spinner(_msg):
        search_result = search_fund(keyword, page_size=10)

        if not search_result["success"]:
            st.error(search_result.get("message", "\u641c\u7d22\u5931\u8d25"))
            st.session_state.fund_search_result = None
            return

        if not search_result["results"]:
            _warn = "\u672a\u627e\u5230\u4e0e '{}' \u76f8\u5173\u7684\u57fa\u91d1".format(keyword)
            st.warning(_warn)
            st.session_state.fund_search_result = None
            return

        st.session_state.fund_search_result = search_result["results"]
        st.session_state.fund_query_result = None
        st.rerun()


def _display_fund_result(result):
    """Display the fund query result."""
    st.markdown("---")
    st.markdown("### \u67e5\u8be2\u7ed3\u679c")

    basic = result.get("basic", {})
    realtime = result.get("realtime", {})
    nav_detail = result.get("nav_detail", {})

    # Extract fund info
    fund_name = basic.get("fund_name") or realtime.get("fund_name") or "\u672a\u77e5\u57fa\u91d1"
    fund_type = basic.get("fund_type") or "\u672a\u77e5\u7c7b\u578b"
    fund_company = basic.get("fund_company", "")
    setup_date = basic.get("setup_date", "")
    manager = basic.get("manager", "")

    # Extract NAV data
    nav = realtime.get("nav") or nav_detail.get("unit_nav", "")
    nav_date = realtime.get("nav_date") or nav_detail.get("nav_date", "")
    change_percent = realtime.get("change_percent") or nav_detail.get("day_change_percent", "")
    change_amount = realtime.get("change_amount") or nav_detail.get("day_change_amount", "")
    estimate_time = realtime.get("estimate_time", "")
    acc_nav = nav_detail.get("acc_nav", "")

    # Display fund info cards
    col1, col2, col3 = st.columns(3)

    with col1:
        _card1 = (
            '<div class="card">'
            '<div style="font-size: 0.85rem; color: #6b7b9e;">\u57fa\u91d1\u540d\u79f0</div>'
            '<div style="font-size: 1.3rem; font-weight: bold; color: #1a2a4a;">{}</div>'
            '<div style="font-size: 0.85rem; color: #6b7b9e; margin-top: 4px;">{} | {}</div>'
            '</div>'
        ).format(fund_name, result["code"], fund_type)
        st.markdown(_card1, unsafe_allow_html=True)

    with col2:
        change_html = format_change_color(change_percent) if change_percent else "\u6682\u65e0\u6570\u636e"
        _card2 = (
            '<div class="card">'
            '<div style="font-size: 0.85rem; color: #6b7b9e;">\u6700\u65b0\u51c0\u503c</div>'
            '<div style="font-size: 1.6rem; font-weight: bold; color: #1a2a4a;">{}</div>'
            '<div style="font-size: 1.1rem; margin-top: 4px;">\u6da8\u8dcc\u5e45\uff1a{}</div>'
            '</div>'
        ).format(nav if nav else "\u6682\u65e0\u6570\u636e", change_html)
        st.markdown(_card2, unsafe_allow_html=True)

    with col3:
        _card3 = (
            '<div class="card">'
            '<div style="font-size: 0.85rem; color: #6b7b9e;">\u7d2f\u8ba1\u51c0\u503c</div>'
            '<div style="font-size: 1.6rem; font-weight: bold; color: #1a2a4a;">{}</div>'
            '<div style="font-size: 0.85rem; color: #6b7b9e; margin-top: 8px;">'
            '\u65e5\u671f\uff1a{}</div>'
            '</div>'
        ).format(acc_nav if acc_nav else "\u6682\u65e0\u6570\u636e", nav_date if nav_date else "\u6682\u65e0")
        st.markdown(_card3, unsafe_allow_html=True)

    # Detail metrics
    info_cols = st.columns(4)
    with info_cols[0]:
        st.metric(label="\u57fa\u91d1\u516c\u53f8", value=fund_company if fund_company else "\u6682\u65e0")
    with info_cols[1]:
        st.metric(label="\u6210\u7acb\u65e5\u671f", value=setup_date if setup_date else "\u6682\u65e0")
    with info_cols[2]:
        st.metric(label="\u57fa\u91d1\u7ecf\u7406", value=manager if manager else "\u6682\u65e0")
    with info_cols[3]:
        st.metric(label="\u4f30\u503c\u65f6\u95f4", value=estimate_time if estimate_time else "\u6682\u65e0")

    # AI interpretation
    if check_api_key() and nav:
        st.markdown("---")
        st.markdown("### \U0001f916 AI \u901a\u4fd7\u89e3\u8bfb")
        if st.button("\u83b7\u53d6 AI \u89e3\u8bfb", key="interpret_btn"):
            with st.spinner("AI \u6b63\u5728\u89e3\u8bfb\u57fa\u91d1\u6570\u636e..."):
                try:
                    fund_data_for_ai = {
                        "fund_name": fund_name,
                        "fund_code": result["code"],
                        "fund_type": fund_type,
                        "nav": nav,
                        "acc_nav": acc_nav,
                        "nav_change_percent": change_percent,
                        "nav_change": change_amount,
                        "nav_date": nav_date,
                        "fund_company": fund_company,
                        "manager": manager,
                    }
                    interpretation = interpret_fund_data(fund_data_for_ai)
                    st.session_state.fund_interpretation = interpretation
                except Exception as e:
                    st.error("AI \u89e3\u8bfb\u5931\u8d25\uff1a{}".format(e))

        if "fund_interpretation" in st.session_state:
            _interp_html = (
                '<div class="card">{}</div>'
            ).format(st.session_state.fund_interpretation.replace("\n", "<br>"))
            st.markdown(_interp_html, unsafe_allow_html=True)

    show_risk_warning()


def _display_search_result(results):
    """Display the fund search results as a table."""
    st.markdown("---")
    _title = "### \u641c\u7d22\u7ed3\u679c\uff08\u5171 {} \u53ea\uff09".format(len(results))
    st.markdown(_title)

    table_data = []
    for item in results:
        table_data.append({
            "\u57fa\u91d1\u4ee3\u7801": item.get("fund_code", ""),
            "\u57fa\u91d1\u540d\u79f0": item.get("fund_name", ""),
            "\u57fa\u91d1\u7c7b\u578b": item.get("fund_type", ""),
        })

    df = pd.DataFrame(table_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "\u57fa\u91d1\u4ee3\u7801": st.column_config.TextColumn("\u57fa\u91d1\u4ee3\u7801", width="small"),
            "\u57fa\u91d1\u540d\u79f0": st.column_config.TextColumn("\u57fa\u91d1\u540d\u79f0"),
            "\u57fa\u91d1\u7c7b\u578b": st.column_config.TextColumn("\u57fa\u91d1\u7c7b\u578b", width="small"),
        },
    )

    st.info("\u63d0\u793a\uff1a\u590d\u5236\u57fa\u91d1\u4ee3\u7801\u5230\u5de6\u4fa7\u8f93\u5165\u6846\u5373\u53ef\u67e5\u770b\u8be6\u7ec6\u6da8\u8dcc\u4fe1\u606f\u3002")


# ==================== Mode 3: Video Summary ====================
def render_video_summary_mode():
    """Render the video/article summary mode."""
    _header_html = (
        '<div class="card">'
        '<h2 class="main-title">\U0001f517 \u89c6\u9891\u603b\u7ed3</h2>'
        '<p class="sub-title">'
        '\u7c98\u8d34\u57fa\u91d1\u5b66\u4e60\u76f8\u5173\u7684\u89c6\u9891\u6216\u6587\u7ae0\u94fe\u63a5\uff0c'
        'AI \u5e2e\u4f60\u63d0\u53d6\u6838\u5fc3\u5185\u5bb9\u3002'
        '</p>'
        '</div>'
    )
    st.markdown(_header_html, unsafe_allow_html=True)

    # Supported platforms hint
    _platform_html = (
        '<div class="info-box">'
        '<strong>\u652f\u6301\u7684\u5e73\u53f0\uff1a</strong>'
        '\u5c0f\u7ea2\u4e66 | \u6296\u97f3 | B\u7ad9 | \u5fae\u4fe1\u516c\u4f17\u53f7 | \u5176\u4ed6\u7f51\u9875\u94fe\u63a5'
        '</div>'
    )
    st.markdown(_platform_html, unsafe_allow_html=True)

    # URL input
    url = st.text_input(
        label="\u7c98\u8d34\u94fe\u63a5",
        placeholder="\u8bf7\u7c98\u8d34\u89c6\u9891\u6216\u6587\u7ae0\u94fe\u63a5\uff0c\u5982 https://www.bilibili.com/video/BV...",
        key="video_url_input",
        label_visibility="collapsed",
    )

    col_parse, col_summarize = st.columns(2)

    with col_parse:
        if st.button("\u89e3\u6790\u94fe\u63a5", key="parse_link_btn", use_container_width=True):
            if not url or not url.strip():
                st.warning("\u8bf7\u8f93\u5165\u94fe\u63a5")
            else:
                _parse_video_link(url.strip())

    with col_summarize:
        if st.button("AI \u603b\u7ed3", key="summarize_btn", use_container_width=True):
            if not check_api_key():
                show_api_warning()
            elif not st.session_state.video_result:
                st.warning("\u8bf7\u5148\u89e3\u6790\u94fe\u63a5")
            elif not st.session_state.video_result.get("content"):
                st.warning("\u94fe\u63a5\u5185\u5bb9\u4e3a\u7a7a\uff0c\u65e0\u6cd5\u603b\u7ed3")
            else:
                _summarize_video_content()

    # Display video result
    if st.session_state.video_result:
        _display_video_result()


def _parse_video_link(url):
    """Parse a video or article link."""
    with st.spinner("\u6b63\u5728\u89e3\u6790\u94fe\u63a5..."):
        try:
            platform_info = detect_platform(url)
            platform_name = platform_info.get("platform_name", "\u672a\u77e5\u5e73\u53f0")
            content_type = platform_info.get("type", "\u672a\u77e5\u7c7b\u578b")
            _info = "\u8bc6\u522b\u5230\u5e73\u53f0\uff1a{}\uff0c\u5185\u5bb9\u7c7b\u578b\uff1a{}".format(
                platform_name, content_type
            )
            st.info(_info)

            result = parse_link(url)
            st.session_state.video_result = result

            if result.get("success"):
                st.success("\u94fe\u63a5\u89e3\u6790\u6210\u529f\uff01")
            else:
                st.warning(result.get("message", "\u89e3\u6790\u5931\u8d25"))
        except Exception as e:
            st.error("\u89e3\u6790\u94fe\u63a5\u65f6\u51fa\u9519\uff1a{}".format(e))
            st.session_state.video_result = None


def _summarize_video_content():
    """Call AI to summarize the parsed video content."""
    result = st.session_state.video_result
    with st.spinner("AI \u6b63\u5728\u603b\u7ed3\u5185\u5bb9..."):
        try:
            content = result.get("content", "")
            platform_name = result.get("platform_name", "")
            summary = summarize_content(content, platform=platform_name)
            st.session_state.video_summary = summary
        except Exception as e:
            st.error("AI \u603b\u7ed3\u5931\u8d25\uff1a{}".format(e))


def _display_video_result():
    """Display the video parsing and summary results."""
    result = st.session_state.video_result

    st.markdown("---")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("**\u5e73\u53f0\uff1a**")
    with col2:
        st.markdown(result.get("platform_name", "\u672a\u77e5"))

    with col1:
        st.markdown("**\u7c7b\u578b\uff1a**")
    with col2:
        st.markdown(result.get("type", "\u672a\u77e5"))

    if result.get("title"):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("**\u6807\u9898\uff1a**")
        with col2:
            st.markdown("**{}**".format(result["title"]))

    if result.get("content"):
        with st.expander("\u67e5\u770b\u63d0\u53d6\u7684\u539f\u6587\u5185\u5bb9", expanded=False):
            st.text_area(
                label="\u539f\u6587\u5185\u5bb9",
                value=result["content"],
                height=300,
                label_visibility="collapsed",
                disabled=True,
            )

    if result.get("message"):
        st.info(result["message"])

    # AI summary result
    if "video_summary" in st.session_state:
        st.markdown("---")
        st.markdown("### \U0001f916 AI \u5185\u5bb9\u603b\u7ed3")
        _summary_html = (
            '<div class="card">{}</div>'
        ).format(st.session_state.video_summary.replace("\n", "<br>"))
        st.markdown(_summary_html, unsafe_allow_html=True)


# ==================== Mode 4: Learning Plan ====================
def render_learning_plan_mode():
    """Render the learning plan generation mode."""
    _header_html = (
        '<div class="card">'
        '<h2 class="main-title">\U0001f4da \u5b66\u4e60\u8ba1\u5212</h2>'
        '<p class="sub-title">'
        '\u544a\u8bc9\u6211\u4f60\u7684\u6c34\u5e73\u548c\u5174\u8da3\uff0c'
        'AI \u4e3a\u4f60\u5b9a\u5236\u4e13\u5c5e\u7684\u57fa\u91d1\u5b66\u4e60\u8ba1\u5212\u3002'
        '</p>'
        '</div>'
    )
    st.markdown(_header_html, unsafe_allow_html=True)

    # Check API key
    if not check_api_key():
        show_api_warning()
        st.info("\u914d\u7f6e API Key \u540e\u5373\u53ef\u751f\u6210\u5b66\u4e60\u8ba1\u5212\u3002")
        return

    # Level selection
    st.markdown("#### \u7b2c\u4e00\u6b65\uff1a\u9009\u62e9\u4f60\u7684\u6c34\u5e73")
    level_options = {
        "\u96f6\u57fa\u7840": "\u5b8c\u5168\u4e0d\u61c2\u57fa\u91d1\uff0c\u60f3\u4ece\u96f6\u5f00\u59cb\u5b66\u4e60",
        "\u5165\u95e8": "\u4e86\u89e3\u57fa\u672c\u6982\u5ff5\uff0c\u4f46\u8fd8\u4e0d\u6e05\u695a\u600e\u4e48\u5b9e\u64cd",
        "\u8fdb\u9636": "\u6709\u4e00\u5b9a\u7ecf\u9a8c\uff0c\u60f3\u6df1\u5165\u5b66\u4e60\u6295\u8d44\u7b56\u7565",
    }
    level = st.radio(
        label="\u4f60\u7684\u57fa\u91d1\u5b66\u4e60\u6c34\u5e73",
        options=list(level_options.keys()),
        format_func=lambda x: "{} - {}".format(x, level_options[x]),
        horizontal=True,
    )

    # Interest topics
    st.markdown("#### \u7b2c\u4e8c\u6b65\uff1a\u9009\u62e9\u611f\u5174\u8da3\u7684\u4e3b\u9898")
    st.markdown("\u53ef\u4ee5\u9009\u62e9\u4ee5\u4e0b\u9884\u8bbe\u4e3b\u9898\uff0c\u4e5f\u53ef\u4ee5\u81ea\u5df1\u8f93\u5165\uff1a")

    preset_topics = [
        "\u6307\u6570\u57fa\u91d1", "\u5b9a\u6295\u7b56\u7565", "\u503a\u5238\u57fa\u91d1",
        "\u80a1\u7968\u57fa\u91d1", "\u8d27\u5e01\u57fa\u91d1", "ETF", "\u57fa\u91d1\u7ec4\u5408",
    ]
    selected_topics = st.multiselect(
        label="\u9884\u8bbe\u4e3b\u9898\uff08\u53ef\u591a\u9009\uff09",
        options=preset_topics,
        label_visibility="collapsed",
    )

    custom_topic = st.text_input(
        label="\u81ea\u5b9a\u4e49\u4e3b\u9898",
        placeholder="\u8f93\u5165\u5176\u4ed6\u611f\u5174\u8da3\u7684\u4e3b\u9898\uff0c\u7528\u9017\u53f7\u5206\u9694",
        key="custom_topic_input",
    )

    # Merge topics
    all_topics = list(selected_topics)
    if custom_topic:
        custom_list = [t.strip() for t in custom_topic.split(",") if t.strip()]
        all_topics.extend(custom_list)

    # Generate button
    st.markdown("---")
    if st.button("\u751f\u6210\u5b66\u4e60\u8ba1\u5212", key="gen_plan_btn", use_container_width=True):
        if not all_topics:
            st.warning("\u8bf7\u81f3\u5c11\u9009\u62e9\u6216\u8f93\u5165\u4e00\u4e2a\u611f\u5174\u8da3\u7684\u4e3b\u9898")
        else:
            with st.spinner("AI \u6b63\u5728\u4e3a\u4f60\u5236\u5b9a\u5b66\u4e60\u8ba1\u5212..."):
                try:
                    history = []
                    if st.session_state.chat_history:
                        history = [
                            m for m in st.session_state.chat_history
                            if m["role"] in ("user", "assistant")
                        ]
                    plan = generate_learning_plan(
                        user_level=level,
                        interests=all_topics,
                        chat_history=history,
                    )
                    st.session_state.learning_plan = plan
                except Exception as e:
                    st.error("\u751f\u6210\u5b66\u4e60\u8ba1\u5212\u5931\u8d25\uff1a{}".format(e))

    # Display learning plan
    if "learning_plan" in st.session_state:
        st.markdown("---")
        st.markdown("### \u4f60\u7684\u4e13\u5c5e\u5b66\u4e60\u8ba1\u5212")
        _plan_html = (
            '<div class="card">{}</div>'
        ).format(st.session_state.learning_plan.replace("\n", "<br>"))
        st.markdown(_plan_html, unsafe_allow_html=True)

        st.download_button(
            label="\u4e0b\u8f7d\u5b66\u4e60\u8ba1\u5212",
            data=st.session_state.learning_plan,
            file_name="FundWise_\u5b66\u4e60\u8ba1\u5212.txt",
            mime="text/plain",
        )


# ==================== Mode 5: Trend Analysis ====================
def render_trend_analysis_mode():
    """Render the fund trend analysis mode."""
    _header_html = (
        '<div class="card">'
        '<h2 class="main-title">\U0001f4ca \u8d70\u52bf\u5206\u6790</h2>'
        '<p class="sub-title">'
        '\u67e5\u770b\u57fa\u91d1\u8fd1\u671f\u51c0\u503c\u8d70\u52bf\uff0c'
        'AI \u5e2e\u4f60\u5206\u6790\u8d8b\u52bf\u548c\u6ce2\u52a8\u7279\u5f81\u3002'
        '</p>'
        '</div>'
    )
    st.markdown(_header_html, unsafe_allow_html=True)

    col_code, col_days = st.columns([1, 1])

    with col_code:
        trend_fund_code = st.text_input(
            label="\u57fa\u91d1\u4ee3\u7801",
            placeholder="\u8bf7\u8f93\u51656\u4f4d\u57fa\u91d1\u4ee3\u7801\uff0c\u5982 000001",
            key="trend_fund_code_input",
            label_visibility="collapsed",
        )

    with col_days:
        trend_days = st.selectbox(
            label="\u67e5\u8be2\u5929\u6570",
            options=[7, 15, 30, 60, 90, 180],
            index=2,
            format_func=lambda x: "\u6700\u8fd1 {} \u5929".format(x),
            key="trend_days_select",
        )

    if st.button("\u5206\u6790\u8d70\u52bf", key="trend_analysis_btn", use_container_width=True):
        if not trend_fund_code or not trend_fund_code.strip():
            st.warning("\u8bf7\u8f93\u5165\u57fa\u91d1\u4ee3\u7801")
        elif len(trend_fund_code.strip()) != 6 or not trend_fund_code.strip().isdigit():
            st.error("\u57fa\u91d1\u4ee3\u7801\u5e94\u4e3a6\u4f4d\u6570\u5b57")
        else:
            _fetch_trend_data(trend_fund_code.strip(), trend_days)

    # Display trend analysis
    if st.session_state.trend_data:
        _display_trend_analysis()


def _fetch_trend_data(fund_code, days):
    """Fetch fund historical NAV data for trend analysis."""
    _msg = "\u6b63\u5728\u83b7\u53d6\u57fa\u91d1 {} \u6700\u8fd1 {} \u5929\u7684\u51c0\u503c\u6570\u636e...".format(
        fund_code, days
    )
    with st.spinner(_msg):
        basic_info = get_fund_basic_info(fund_code)
        fund_name = basic_info.get("fund_name", "\u57fa\u91d1{}".format(fund_code))

        history = get_fund_history_nav(fund_code, days=days)

        if not history["success"]:
            st.error(history.get("message", "\u83b7\u53d6\u5386\u53f2\u51c0\u503c\u6570\u636e\u5931\u8d25"))
            st.session_state.trend_data = None
            return

        if not history["data"]:
            st.warning("\u672a\u83b7\u53d6\u5230\u5386\u53f2\u51c0\u503c\u6570\u636e")
            st.session_state.trend_data = None
            return

        st.session_state.trend_data = {
            "fund_code": fund_code,
            "fund_name": fund_name,
            "fund_type": basic_info.get("fund_type", ""),
            "days": days,
            "history": history["data"],
        }
        st.rerun()


def _display_trend_analysis():
    """Display the trend analysis results including chart and AI analysis."""
    data = st.session_state.trend_data
    fund_name = data["fund_name"]
    fund_code = data["fund_code"]
    fund_type = data["fund_type"]
    history = data["history"]
    days = data["days"]

    st.markdown("---")

    _title = "### {}\uff08{}\uff09- \u6700\u8fd1 {} \u5929\u8d70\u52bf".format(
        fund_name, fund_code, days
    )
    st.markdown(_title)
    if fund_type:
        st.caption("\u57fa\u91d1\u7c7b\u578b\uff1a{}".format(fund_type))

    # Prepare chart data
    chart_data = []
    for item in reversed(history):
        try:
            nav_value = float(item.get("unit_nav", 0))
            chart_data.append({
                "\u65e5\u671f": item.get("date", ""),
                "\u5355\u4f4d\u51c0\u503c": nav_value,
            })
        except (ValueError, TypeError):
            continue

    if chart_data:
        df = pd.DataFrame(chart_data)
        df.set_index("\u65e5\u671f", inplace=True)

        st.line_chart(
            df,
            use_container_width=True,
            height=400,
            color=["#667eea"],
        )

        # Key statistics
        nav_values = df["\u5355\u4f4d\u51c0\u503c"].values
        latest_nav = nav_values[-1]
        highest_nav = nav_values.max()
        lowest_nav = nav_values.min()

        if nav_values[0] != 0:
            period_change = (latest_nav - nav_values[0]) / nav_values[0] * 100
        else:
            period_change = 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="\u6700\u65b0\u51c0\u503c", value="{:.4f}".format(latest_nav))
        with col2:
            st.metric(
                label="\u533a\u95f4\u6da8\u8dcc\u5e45",
                value="{:+.2f}%".format(period_change),
                delta="{:+.2f}%".format(period_change),
            )
        with col3:
            st.metric(label="\u6700\u9ad8\u51c0\u503c", value="{:.4f}".format(highest_nav))
        with col4:
            st.metric(label="\u6700\u4f4e\u51c0\u503c", value="{:.4f}".format(lowest_nav))

        # Historical data table
        with st.expander("\u67e5\u770b\u5386\u53f2\u51c0\u503c\u6570\u636e", expanded=False):
            table_data = []
            for item in reversed(history):
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

                table_data.append({
                    "\u65e5\u671f": item.get("date", ""),
                    "\u5355\u4f4d\u51c0\u503c": item.get("unit_nav", ""),
                    "\u7d2f\u8ba1\u51c0\u503c": item.get("acc_nav", ""),
                    "\u65e5\u6da8\u8dcc\u5e45": change_display,
                })

            df_table = pd.DataFrame(table_data)
            st.dataframe(
                df_table,
                use_container_width=True,
                hide_index=True,
                height=300,
            )

    # AI trend analysis
    if check_api_key():
        st.markdown("---")
        st.markdown("### \U0001f916 AI \u8d70\u52bf\u5206\u6790")
        if st.button("\u83b7\u53d6 AI \u5206\u6790", key="ai_trend_btn"):
            with st.spinner("AI \u6b63\u5728\u5206\u6790\u8d70\u52bf\u6570\u636e..."):
                try:
                    analysis_data = []
                    for item in reversed(history):
                        analysis_data.append({
                            "date": item.get("date", ""),
                            "nav": item.get("unit_nav", ""),
                            "acc_nav": item.get("acc_nav", ""),
                            "nav_change_percent": item.get("day_change_percent", ""),
                        })
                    analysis = analyze_fund_trend(fund_code, analysis_data)
                    st.session_state.trend_analysis = analysis
                except Exception as e:
                    st.error("AI \u5206\u6790\u5931\u8d25\uff1a{}".format(e))

        if "trend_analysis" in st.session_state:
            _analysis_html = (
                '<div class="card">{}</div>'
            ).format(st.session_state.trend_analysis.replace("\n", "<br>"))
            st.markdown(_analysis_html, unsafe_allow_html=True)

    show_risk_warning()


# ==================== Main ====================
def main():
    """Main entry point: render sidebar and dispatch to the active mode."""

    # Render sidebar
    with st.sidebar:
        render_sidebar()

    # Dispatch to the active mode
    mode = st.session_state.mode

    if mode == "\u667a\u80fd\u95ee\u7b54":
        render_chat_mode()
    elif mode == "\u67e5\u6da8\u8dcc":
        render_fund_query_mode()
    elif mode == "\u89c6\u9891\u603b\u7ed3":
        render_video_summary_mode()
    elif mode == "\u5b66\u4e60\u8ba1\u5212":
        render_learning_plan_mode()
    elif mode == "\u8d70\u52bf\u5206\u6790":
        render_trend_analysis_mode()


# ==================== Entry Point ====================
if __name__ == "__main__":
    main()
