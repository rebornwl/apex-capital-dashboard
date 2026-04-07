#!/usr/bin/env python3
"""
巅峰资本 - 数据质量检测脚本
检查 holdings.md 的数据基准日是否过期，生成过期预警信息。
供 update_cloud.py 和 GitHub Actions 调用。
"""

import re
import os
from datetime import datetime, timedelta

HOLDINGS_MD = os.path.join(os.getenv("GITHUB_WORKSPACE", "."), "portfolio", "holdings.md")

def count_trading_days_between(start_date, end_date):
    """
    计算两个日期之间的交易日天数（排除周末）。
    start_date 和 end_date 均为 datetime 对象。
    """
    count = 0
    current = start_date + timedelta(days=1)
    while current <= end_date:
        if current.weekday() < 5:  # 周一到周五
            count += 1
        current += timedelta(days=1)
    return count

def check_data_freshness():
    """
    检查 holdings.md 的数据新鲜度。
    返回: {
        "base_date": "2026-04-03",
        "stale_days": 3,  # 过期的交易日数
        "warning_level": "orange",  # yellow/orange/red/none
        "warning_msg": "..."
    }
    """
    result = {
        "base_date": None,
        "stale_days": 0,
        "warning_level": "none",
        "warning_msg": "",
        "is_stale": False,
    }

    if not os.path.exists(HOLDINGS_MD):
        result["warning_level"] = "red"
        result["warning_msg"] = "CRITICAL: holdings.md 文件不存在"
        result["is_stale"] = True
        return result

    with open(HOLDINGS_MD, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析数据基准日
    match = re.search(r'数据基准日[：:]\s*(\d{4}-\d{2}-\d{2})', content)
    if not match:
        result["warning_level"] = "red"
        result["warning_msg"] = "CRITICAL: 无法解析数据基准日"
        result["is_stale"] = True
        return result

    base_date_str = match.group(1)
    base_date = datetime.strptime(base_date_str, "%Y-%m-%d")
    today = datetime.now()
    today_date = datetime(today.year, today.month, today.day)

    result["base_date"] = base_date_str
    stale_days = count_trading_days_between(base_date, today_date)
    result["stale_days"] = stale_days

    # 预警级别判定
    if stale_days <= 1:
        result["warning_level"] = "none"
        result["warning_msg"] = ""
        result["is_stale"] = False
    elif stale_days == 2:
        result["warning_level"] = "yellow"
        result["warning_msg"] = f"⚠️ 数据基准日为 {base_date_str}（{stale_days}个交易日前），建议更新"
        result["is_stale"] = True
    elif stale_days == 3:
        result["warning_level"] = "orange"
        result["warning_msg"] = f"🟠 数据已过期{stale_days}个交易日（基准日：{base_date_str}），请尽快更新持仓数据"
        result["is_stale"] = True
    else:
        result["warning_level"] = "red"
        result["warning_msg"] = f"🔴 数据严重过期！已{stale_days}个交易日未更新（基准日：{base_date_str}），当前数据不可靠"
        result["is_stale"] = True

    return result

if __name__ == "__main__":
    result = check_data_freshness()
    status_icon = {"none": "✅", "yellow": "🟡", "orange": "🟠", "red": "🔴"}
    print(f"{status_icon.get(result['warning_level'], '❓')} 数据新鲜度检查")
    print(f"  基准日：{result['base_date']}")
    print(f"  过期天数：{result['stale_days']} 个交易日")
    print(f"  预警级别：{result['warning_level']}")
    if result['warning_msg']:
        print(f"  预警信息：{result['warning_msg']}")
    else:
        print(f"  数据正常 ✅")
