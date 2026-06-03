# -*- coding: utf-8 -*-
"""
基金数据模块 - 接入天天基金（eastmoney）公开API
提供基金基本信息查询、实时净值查询、历史净值查询、基金搜索等功能
"""

import re
import json
import requests
from datetime import datetime, timedelta
from typing import Optional


# ==================== 常量配置 ====================

# 请求超时时间（秒）
REQUEST_TIMEOUT = 10

# 请求头，模拟浏览器访问
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://fund.eastmoney.com/",
}

# 天天基金API端点
API_FUND_ESTIMATE = "http://fundgz.1234567.com.cn/js/{fund_code}.js"  # 实时估值（JSONP）
API_FUND_DETAIL = "https://fund.eastmoney.com/pingzhongdata/{fund_code}.js"  # 净值详情
API_FUND_BASIC_INFO = "https://fundf10.eastmoney.com/jbgk_{fund_code}.html"  # 基本信息HTML
API_FUND_SEARCH = (
    "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchPageByWord.ashx"
)  # 基金搜索
API_FUND_NET_VALUE_HISTORY = (
    "https://api.fund.eastmoney.com/f10/lsjz"
)  # 历史净值接口


# ==================== 工具函数 ====================

def _request_get(url: str, params: Optional[dict] = None, encoding: str = "utf-8") -> Optional[str]:
    """
    通用GET请求封装，统一处理网络异常

    Args:
        url: 请求地址
        params: 查询参数
        encoding: 响应编码

    Returns:
        响应文本，请求失败返回None
    """
    try:
        resp = requests.get(
            url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT
        )
        resp.encoding = encoding
        if resp.status_code == 200:
            return resp.text
        return None
    except requests.RequestException:
        return None


def _validate_fund_code(fund_code: str) -> bool:
    """
    校验基金代码格式（6位数字）

    Args:
        fund_code: 基金代码

    Returns:
        格式是否合法
    """
    return bool(re.match(r"^\d{6}$", str(fund_code).strip()))


def _parse_jsonp(text: str) -> Optional[dict]:
    """
    解析JSONP响应，提取其中的JSON数据

    天天基金JSONP格式示例: jsonpgz({"fundcode":"000001",...})

    Args:
        text: JSONP响应文本

    Returns:
        解析后的字典，失败返回None
    """
    if not text:
        return None
    try:
        # 匹配 JSONP 回调函数中的 JSON 内容
        match = re.search(r"\((\{.*\})\)", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


# ==================== 核心功能函数 ====================

def get_fund_basic_info(fund_code: str) -> dict:
    """
    查询基金基本信息（基金名称、基金类型、基金公司、成立日期等）

    通过解析 fundf10 基本信息页面获取数据。

    Args:
        fund_code: 6位基金代码

    Returns:
        dict 格式的基金基本信息，包含以下字段：
        {
            "success": bool,          # 是否成功
            "fund_code": str,         # 基金代码
            "fund_name": str,         # 基金名称
            "fund_type": str,         # 基金类型（如：混合型、股票型、债券型等）
            "fund_company": str,       # 基金公司/管理人
            "setup_date": str,         # 成立日期
            "manager": str,            # 基金经理
            "message": str             # 错误信息（失败时）
        }
    """
    result = {
        "success": False,
        "fund_code": fund_code,
        "fund_name": "",
        "fund_type": "",
        "fund_company": "",
        "setup_date": "",
        "manager": "",
        "message": "",
    }

    # 校验基金代码格式
    if not _validate_fund_code(fund_code):
        result["message"] = f"基金代码格式错误：{fund_code}，应为6位数字"
        return result

    # 方式一：通过 pingzhongdata JS 获取基金名称和类型
    detail_url = API_FUND_DETAIL.format(fund_code=fund_code)
    detail_text = _request_get(detail_url, encoding="utf-8")

    if detail_text:
        # 提取基金名称
        name_match = re.search(r'var fS_name\s*=\s*"([^"]+)"', detail_text)
        if name_match:
            result["fund_name"] = name_match.group(1)

        # 提取基金类型
        type_match = re.search(r'var fS_code\s*=\s*"([^"]+)"', detail_text)
        # 通过 pingzhongdata 获取类型信息
        type_match2 = re.search(r'var fund_type\s*=\s*"?(\d+)"?', detail_text)
        if type_match2:
            fund_type_code = type_match2.group(1)
            # 基金类型映射
            type_map = {
                "0": "未知",
                "1": "股票型",
                "2": "混合型",
                "3": "债券型",
                "4": "货币型",
                "5": "指数型",
                "6": "QDII",
                "7": "FOF",
                "8": "理财型",
            }
            result["fund_type"] = type_map.get(fund_type_code, "其他")

    # 方式二：通过基本信息HTML页面获取基金公司、成立日期、基金经理
    info_url = API_FUND_BASIC_INFO.format(fund_code=fund_code)
    info_html = _request_get(info_url, encoding="utf-8")

    if info_html:
        # 提取基金公司（管理人）
        company_match = re.search(
            r'基金管理人.*?<[^>]*>([^<]+)', info_html, re.DOTALL
        )
        if company_match:
            result["fund_company"] = company_match.group(1).strip()

        # 提取成立日期
        date_match = re.search(
            r'成立日期.*?<[^>]*>([^<]+)', info_html, re.DOTALL
        )
        if date_match:
            result["setup_date"] = date_match.group(1).strip()

        # 提取基金经理
        manager_match = re.search(
            r'基金经理.*?<[^>]*>([^<]+)', info_html, re.DOTALL
        )
        if manager_match:
            result["manager"] = manager_match.group(1).strip()

        # 如果方式一未获取到基金名称，尝试从HTML页面获取
        if not result["fund_name"]:
            title_match = re.search(r'<title>([^<]+)</title>', info_html)
            if title_match:
                result["fund_name"] = title_match.group(1).strip()

    # 判断是否获取到了有效数据
    if result["fund_name"]:
        result["success"] = True
    else:
        result["message"] = f"未找到基金代码 {fund_code} 对应的基金信息，请检查基金代码是否正确"

    return result


def get_fund_realtime_estimate(fund_code: str) -> dict:
    """
    查询基金实时估值/最新净值和涨跌幅

    通过天天基金实时估值接口获取数据。
    注意：该接口返回的是估值数据，交易日的盘中数据为实时估值，收盘后为最新净值。

    Args:
        fund_code: 6位基金代码

    Returns:
        dict 格式的实时数据，包含以下字段：
        {
            "success": bool,          # 是否成功
            "fund_code": str,         # 基金代码
            "fund_name": str,         # 基金名称
            "nav": str,               # 最新净值/估值
            "nav_date": str,          # 净值日期
            "change_percent": str,   # 涨跌幅（%）
            "change_amount": str,     # 涨跌额
            "estimate_time": str,     # 估值时间
            "message": str            # 错误信息（失败时）
        }
    """
    result = {
        "success": False,
        "fund_code": fund_code,
        "fund_name": "",
        "nav": "",
        "nav_date": "",
        "change_percent": "",
        "change_amount": "",
        "estimate_time": "",
        "message": "",
    }

    # 校验基金代码格式
    if not _validate_fund_code(fund_code):
        result["message"] = f"基金代码格式错误：{fund_code}，应为6位数字"
        return result

    # 调用实时估值接口
    url = API_FUND_ESTIMATE.format(fund_code=fund_code)
    text = _request_get(url, encoding="utf-8")

    if not text:
        result["message"] = f"请求基金 {fund_code} 实时数据失败，请检查网络连接或基金代码"
        return result

    # 解析JSONP响应
    data = _parse_jsonp(text)
    if not data:
        result["message"] = f"解析基金 {fund_code} 实时数据失败，返回数据格式异常"
        return result

    # 提取数据
    result["success"] = True
    result["fund_name"] = data.get("name", "")
    result["fund_code"] = data.get("fundcode", fund_code)
    result["nav"] = data.get("gsz", "")  # 估算净值
    result["nav_date"] = data.get("jzrq", "")  # 净值日期
    result["change_percent"] = data.get("gszzl", "")  # 估算涨跌幅（%）
    result["change_amount"] = data.get("gszze", "")  # 估算涨跌额
    result["estimate_time"] = data.get("gztime", "")  # 估值时间

    return result


def get_fund_nav_detail(fund_code: str) -> dict:
    """
    查询基金净值详情（最新净值、累计净值、涨跌幅等）

    通过 pingzhongdata JS 接口获取更详细的净值数据。

    Args:
        fund_code: 6位基金代码

    Returns:
        dict 格式的净值详情，包含以下字段：
        {
            "success": bool,              # 是否成功
            "fund_code": str,             # 基金代码
            "fund_name": str,             # 基金名称
            "unit_nav": str,              # 单位净值
            "acc_nav": str,               # 累计净值
            "nav_date": str,              # 净值日期
            "day_change_percent": str,    # 日涨跌幅（%）
            "day_change_amount": str,     # 日涨跌额
            "message": str                # 错误信息（失败时）
        }
    """
    result = {
        "success": False,
        "fund_code": fund_code,
        "fund_name": "",
        "unit_nav": "",
        "acc_nav": "",
        "nav_date": "",
        "day_change_percent": "",
        "day_change_amount": "",
        "message": "",
    }

    # 校验基金代码格式
    if not _validate_fund_code(fund_code):
        result["message"] = f"基金代码格式错误：{fund_code}，应为6位数字"
        return result

    url = API_FUND_DETAIL.format(fund_code=fund_code)
    text = _request_get(url, encoding="utf-8")

    if not text:
        result["message"] = f"请求基金 {fund_code} 净值详情失败，请检查网络连接或基金代码"
        return result

    # 提取基金名称
    name_match = re.search(r'var fS_name\s*=\s*"([^"]+)"', text)
    if name_match:
        result["fund_name"] = name_match.group(1)

    # 提取单位净值数据（Data_netWorthTrend 数组中最后一个元素）
    trend_match = re.search(
        r'var Data_netWorthTrend\s*=\s*(\[.*?\]);', text, re.DOTALL
    )
    if trend_match:
        try:
            trend_data = json.loads(trend_match.group(1))
            if trend_data:
                latest = trend_data[-1]
                result["unit_nav"] = str(latest.get("y", ""))
                # 时间戳转换为日期
                timestamp = latest.get("x", 0)
                if timestamp:
                    result["nav_date"] = datetime.fromtimestamp(
                        timestamp / 1000
                    ).strftime("%Y-%m-%d")
                # 涨跌额和涨跌幅
                result["day_change_amount"] = str(
                    latest.get("equityReturn", "")
                )
                # 计算涨跌幅
                if len(trend_data) >= 2:
                    prev = trend_data[-2].get("y", 0)
                    curr = latest.get("y", 0)
                    if prev and curr:
                        change_pct = round(
                            (curr - prev) / prev * 100, 4
                        )
                        result["day_change_percent"] = str(change_pct)
        except (json.JSONDecodeError, IndexError, KeyError, ZeroDivisionError):
            pass

    # 提取累计净值数据（Data_ACWorthTrend 数组中最后一个元素）
    acc_match = re.search(
        r'var Data_ACWorthTrend\s*=\s*(\[.*?\]);', text, re.DOTALL
    )
    if acc_match:
        try:
            acc_data = json.loads(acc_match.group(1))
            if acc_data:
                result["acc_nav"] = str(acc_data[-1].get("y", ""))
        except (json.JSONDecodeError, IndexError, KeyError):
            pass

    # 判断是否获取到了有效数据
    if result["unit_nav"] or result["fund_name"]:
        result["success"] = True
    else:
        result["message"] = f"未找到基金 {fund_code} 的净值数据，请检查基金代码是否正确"

    return result


def get_fund_history_nav(
    fund_code: str, days: int = 30, page_size: int = 50
) -> dict:
    """
    查询基金历史净值数据（用于走势分析）

    通过天天基金历史净值API分页获取数据。

    Args:
        fund_code: 6位基金代码
        days: 查询最近N天的数据，默认30天
        page_size: 每页数据条数，默认50条

    Returns:
        dict 格式的历史净值数据，包含以下字段：
        {
            "success": bool,          # 是否成功
            "fund_code": str,         # 基金代码
            "total_records": int,     # 总记录数
            "data": [                 # 历史净值列表（按日期倒序）
                {
                    "date": str,           # 净值日期
                    "unit_nav": str,       # 单位净值
                    "acc_nav": str,        # 累计净值
                    "day_change_percent": str,  # 日涨跌幅（%）
                },
                ...
            ],
            "message": str            # 错误信息（失败时）
        }
    """
    result = {
        "success": False,
        "fund_code": fund_code,
        "total_records": 0,
        "data": [],
        "message": "",
    }

    # 校验基金代码格式
    if not _validate_fund_code(fund_code):
        result["message"] = f"基金代码格式错误：{fund_code}，应为6位数字"
        return result

    # 参数校验
    if days <= 0:
        days = 30
    if page_size <= 0 or page_size > 200:
        page_size = 50

    # 计算查询的起始日期
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # 计算需要请求的页数
    # 先请求第一页获取总记录数
    all_records = []
    page_index = 1

    while True:
        params = {
            "callback": "jQuery",
            "fundCode": fund_code,
            "pageIndex": page_index,
            "pageSize": page_size,
            "startDate": start_date,
            "endDate": end_date,
        }

        text = _request_get(
            API_FUND_NET_VALUE_HISTORY, params=params, encoding="utf-8"
        )

        if not text:
            if not all_records:
                result["message"] = (
                    f"请求基金 {fund_code} 历史净值失败，请检查网络连接或基金代码"
                )
            break

        # 解理JSONP响应
        data = _parse_jsonp(text)
        if not data:
            if not all_records:
                result["message"] = (
                    f"解析基金 {fund_code} 历史净值数据失败"
                )
            break

        # 获取数据列表和总记录数
        data_list = data.get("Data", {}).get("LSJZList", [])
        total = data.get("TotalCount", 0)

        if not data_list:
            break

        for item in data_list:
            record = {
                "date": item.get("FSRQ", ""),  # 净值日期
                "unit_nav": item.get("DWJZ", ""),  # 单位净值
                "acc_nav": item.get("LJJZ", ""),  # 累计净值
                "day_change_percent": item.get("JZZZL", ""),  # 日涨跌幅（%）
            }
            all_records.append(record)

        # 如果已经获取了所有数据，退出循环
        if len(all_records) >= total or len(data_list) < page_size:
            break

        page_index += 1

    if all_records:
        result["success"] = True
        result["total_records"] = len(all_records)
        result["data"] = all_records
    elif not result["message"]:
        result["message"] = (
            f"未找到基金 {fund_code} 在指定时间段内的历史净值数据"
        )

    return result


def search_fund(keyword: str, page_size: int = 10) -> dict:
    """
    基金搜索：根据关键词模糊搜索匹配的基金代码和名称

    通过天天基金搜索接口获取结果。

    Args:
        keyword: 搜索关键词（基金代码、基金名称或拼音缩写）
        page_size: 返回结果数量上限，默认10条

    Returns:
        dict 格式的搜索结果，包含以下字段：
        {
            "success": bool,          # 是否成功
            "keyword": str,           # 搜索关键词
            "total": int,             # 匹配总数
            "results": [              # 搜索结果列表
                {
                    "fund_code": str,     # 基金代码
                    "fund_name": str,     # 基金名称
                    "fund_type": str,     # 基金类型
                    "pinyin": str,        # 拼音缩写
                },
                ...
            ],
            "message": str            # 错误信息（失败时）
        }
    """
    result = {
        "success": False,
        "keyword": keyword,
        "total": 0,
        "results": [],
        "message": "",
    }

    # 校验关键词
    if not keyword or not keyword.strip():
        result["message"] = "搜索关键词不能为空"
        return result

    keyword = keyword.strip()

    # 参数校验
    if page_size <= 0 or page_size > 50:
        page_size = 10

    params = {
        "m": 1,
        "key": keyword,
        "pageindex": 0,
        "pagesize": page_size,
        "fundtype": "",
        "gpdm": "",
    }

    text = _request_get(API_FUND_SEARCH, params=params, encoding="utf-8")

    if not text:
        result["message"] = "搜索请求失败，请检查网络连接"
        return result

    # 解析搜索结果
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        result["message"] = "解析搜索结果失败，返回数据格式异常"
        return result

    # 提取基金列表
    datas = data.get("Datas", [])
    if not isinstance(datas, list):
        result["message"] = "搜索结果数据格式异常"
        return result

    # 基金类型映射
    type_map = {
        "0": "未知",
        "1": "股票型",
        "2": "混合型",
        "3": "债券型",
        "4": "货币型",
        "5": "指数型",
        "6": "QDII",
        "7": "FOF",
        "8": "理财型",
    }

    for item in datas:
        fund_info = {
            "fund_code": item.get("CODE", ""),  # 基金代码
            "fund_name": item.get("NAME", ""),  # 基金名称
            "fund_type": type_map.get(
                item.get("FundType", ""), "其他"
            ),  # 基金类型
            "pinyin": item.get("PINYIN", ""),  # 拼音缩写
        }
        result["results"].append(fund_info)

    result["total"] = len(result["results"])
    result["success"] = True

    if not result["results"]:
        result["message"] = f"未找到与 '{keyword}' 相关的基金"

    return result


# ==================== 便捷组合查询函数 ====================

def get_fund_overview(fund_code: str) -> dict:
    """
    获取基金综合概览信息（基本信息 + 实时净值 + 最新涨跌幅）

    组合调用多个接口，返回一份完整的基金概览数据。

    Args:
        fund_code: 6位基金代码

    Returns:
        dict 格式的综合概览，包含以下字段：
        {
            "success": bool,              # 是否成功（至少一个接口返回了数据）
            "fund_code": str,             # 基金代码
            "basic_info": dict,           # 基本信息子字典
            "realtime": dict,             # 实时估值子字典
            "nav_detail": dict,           # 净值详情子字典
            "message": str                # 错误信息（失败时）
        }
    """
    overview = {
        "success": False,
        "fund_code": fund_code,
        "basic_info": {},
        "realtime": {},
        "nav_detail": {},
        "message": "",
    }

    # 校验基金代码格式
    if not _validate_fund_code(fund_code):
        overview["message"] = f"基金代码格式错误：{fund_code}，应为6位数字"
        return overview

    # 依次调用各接口
    overview["basic_info"] = get_fund_basic_info(fund_code)
    overview["realtime"] = get_fund_realtime_estimate(fund_code)
    overview["nav_detail"] = get_fund_nav_detail(fund_code)

    # 只要有一个接口成功，就认为整体成功
    if (
        overview["basic_info"].get("success")
        or overview["realtime"].get("success")
        or overview["nav_detail"].get("success")
    ):
        overview["success"] = True
    else:
        overview["message"] = f"无法获取基金 {fund_code} 的任何信息，请检查基金代码是否正确"

    return overview


# ==================== 模块测试入口 ====================

if __name__ == "__main__":
    # 简单测试：查询几个常见基金的信息
    test_codes = ["000001", "110011", "161725"]

    print("=" * 60)
    print("基金数据模块测试")
    print("=" * 60)

    for code in test_codes:
        print(f"\n--- 基金代码: {code} ---")

        # 测试基本信息
        info = get_fund_basic_info(code)
        print(f"  基本信息: {'成功' if info['success'] else '失败 - ' + info['message']}")
        if info["success"]:
            print(f"    名称: {info['fund_name']}")
            print(f"    类型: {info['fund_type']}")
            print(f"    公司: {info['fund_company']}")

        # 测试实时估值
        rt = get_fund_realtime_estimate(code)
        print(f"  实时估值: {'成功' if rt['success'] else '失败 - ' + rt['message']}")
        if rt["success"]:
            print(f"    净值: {rt['nav']}")
            print(f"    涨跌幅: {rt['change_percent']}%")

        # 测试历史净值
        hist = get_fund_history_nav(code, days=7)
        print(f"  历史净值: {'成功' if hist['success'] else '失败 - ' + hist['message']}")
        if hist["success"]:
            print(f"    记录数: {hist['total_records']}")

    # 测试搜索
    print(f"\n--- 搜索测试: 关键词 '沪深300' ---")
    search_result = search_fund("沪深300", page_size=5)
    print(f"  搜索结果: {'成功' if search_result['success'] else '失败'}")
    if search_result["success"]:
        print(f"  匹配数量: {search_result['total']}")
        for item in search_result["results"][:3]:
            print(f"    {item['fund_code']} - {item['fund_name']} ({item['fund_type']})")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
