#!/usr/bin/env python3
"""OCR截图解析并更新holdings.md - 巅峰资本持仓同步核心脚本"""
import re, os, json, sys
from datetime import datetime, timedelta


def parse_ocr_data(ocr_text, old_content):
    """从OCR文本中提取基金数据"""
    lines = ocr_text.split('\n')
    funds_normal = []
    funds_pension = []
    current_section = "normal"
    total_normal = None
    total_pension = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测账户切换
        if '养老金' in line and ('账户' in line or '持仓' in line):
            current_section = "pension"
            print(f"  切换到养老金账户")
            continue
        if ('普通' in line or '账户一' in line) and '账户' in line:
            current_section = "normal"
            print(f"  切换到普通账户")
            continue

        # 提取基金代码（6位数字）
        code_match = re.search(r'(?<!\d)([01]\d{5})(?!\d)', line)
        if not code_match:
            code_match = re.search(r'(?<!\d)([3-9]\d{5})(?!\d)', line)

        if code_match:
            code = code_match.group(1)
            # 排除日期格式
            if code.startswith(('202', '201', '203')):
                continue

            numbers = re.findall(r'[+-]?[\d,]+\.\d{2}', line)
            percentages = re.findall(r'[+-]?\d+\.?\d*%', line)
            name_match = re.search(r'\d{6}\s*([^\d+\-¥,%]{2,30})', line)
            fund_name = name_match.group(1).strip() if name_match else ""

            print(f"  基金: {code} {fund_name[:15]} | 数值: {numbers}")

            if len(numbers) >= 3:
                fund = {
                    'code': code,
                    'name': fund_name,
                    'numbers': numbers,
                    'percentages': percentages,
                }
                if current_section == "pension":
                    funds_pension.append(fund)
                else:
                    funds_normal.append(fund)

        # 提取总资产
        total_match = re.search(r'总资产[^\d]*([\d,]+\.\d{2})', line)
        if total_match:
            val = total_match.group(1)
            if current_section == "pension":
                total_pension = val
            else:
                total_normal = val

    return funds_normal, funds_pension, total_normal, total_pension


def extract_old_funds(old_content):
    """从旧的holdings.md中提取已知基金信息"""
    old_fund_codes = set()
    old_fund_names = {}
    for m in re.finditer(r'\|\s*\d+\s*\|\s*(\d{6})\s*\|\s*([^|]+?)\s*\|', old_content):
        code = m.group(1)
        name = m.group(2).strip()
        old_fund_codes.add(code)
        old_fund_names[code] = name
    return old_fund_codes, old_fund_names


def generate_holdings_md(funds_normal, funds_pension, old_content, ocr_text):
    """生成新的holdings.md内容"""
    old_fund_codes, old_fund_names = extract_old_funds(old_content)
    pension_codes = {"017268", "017294", "017353", "022951", "022979"}
    known_normal = old_fund_codes - pension_codes

    ocr_normal_codes = set(f["code"] for f in funds_normal)
    ocr_pension_codes = set(f["code"] for f in funds_pension)

    missing_from_ocr = known_normal - ocr_normal_codes
    extra_in_ocr = ocr_normal_codes - known_normal

    issues = []
    warnings = []

    if len(funds_normal) < 15:
        issues.append(f"普通账户只识别到 {len(funds_normal)} 支基金（期望 20 支），可能遗漏")
    if len(funds_normal) > 25:
        warnings.append(f"普通账户识别到 {len(funds_normal)} 支基金（期望 20 支），可能有误识别")
    if missing_from_ocr:
        issues.append(f"以下已知基金未识别到：{', '.join(sorted(missing_from_ocr))}")
    if extra_in_ocr:
        warnings.append(f"识别到未知基金代码：{', '.join(sorted(extra_in_ocr))}")

    ocr_normal_map = {f["code"]: f for f in funds_normal}
    ocr_pension_map = {f["code"]: f for f in funds_pension}

    # 普通账户行
    new_normal_rows = []
    for f in funds_normal:
        code = f["code"]
        name = old_fund_names.get(code, f["name"] if f["name"] else "未知基金")
        nums = f["numbers"]
        total_amt = nums[0] if len(nums) >= 1 else "?"
        daily_ret = nums[1] if len(nums) >= 2 else "?"
        hold_ret = nums[2] if len(nums) >= 3 else "?"
        pct = f["percentages"][0] if f["percentages"] else "?"
        row = f"| {len(new_normal_rows)+1} | {code} | {name} | 待确认 | {total_amt} | {daily_ret} | {hold_ret} | {pct} |"
        new_normal_rows.append(row)

    # 补全遗漏的基金
    for code in known_normal:
        if code not in ocr_normal_map:
            name = old_fund_names.get(code, "未知")
            warnings.append(f"基金 {code} {name} 未识别到，保留旧数据")
            old_match = re.search(
                rf'\|\s*\d+\s*\|\s*{code}\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|',
                old_content
            )
            if old_match:
                row = f"| {len(new_normal_rows)+1} | {code} | {old_match.group(1).strip()} | {old_match.group(2).strip()} | {old_match.group(3).strip()} | {old_match.group(4).strip()} | {old_match.group(5).strip()} | {old_match.group(6).strip()} |"
                new_normal_rows.append(row)

    # 养老金账户行
    new_pension_rows = []
    for f in funds_pension:
        code = f["code"]
        name = old_fund_names.get(code, f["name"] if f["name"] else "未知基金")
        nums = f["numbers"]
        total_amt = nums[0] if len(nums) >= 1 else "?"
        daily_ret = nums[1] if len(nums) >= 2 else "?"
        hold_ret = nums[2] if len(nums) >= 3 else "?"
        pct = f["percentages"][0] if f["percentages"] else "?"
        row = f"| {len(new_pension_rows)+1} | {code} | {name} | 养老FOF | {total_amt} | {daily_ret} | {hold_ret} | {pct} |"
        new_pension_rows.append(row)

    # 养老金未识别时保留旧数据
    if not new_pension_rows:
        warnings.append("养老金账户数据未识别，保留旧数据")
        pension_section = re.search(r'## 账户二.*?(?=## 总资产|$)', old_content, re.DOTALL)
        if pension_section:
            for m in re.finditer(r'\|\s*\d+\s*\|(\s*\d{6}\s*\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+\|[^|]+)\|', pension_section.group()):
                new_pension_rows.append(f"| {len(new_pension_rows)+1}{m.group(1)} |")

    # 计算基准日
    now_utc = datetime.utcnow()
    now_cn = now_utc + timedelta(hours=8)
    weekday = now_cn.weekday()
    if weekday >= 5:
        base_date = now_cn - timedelta(days=weekday - 4)
    elif now_cn.hour < 15:
        days_back = 1 if weekday > 0 else 3
        base_date = now_cn - timedelta(days=days_back)
    else:
        base_date = now_cn
    date_str = base_date.strftime("%Y-%m-%d")

    # 计算合计
    def parse_num(s):
        if s == "?":
            return 0
        return float(s.replace(",", "").replace("+", ""))

    normal_total = sum(parse_num(row.split("|")[5].strip()) for row in new_normal_rows)
    pension_total = sum(parse_num(row.split("|")[5].strip()) for row in new_pension_rows)
    grand_total = normal_total + pension_total
    normal_daily = sum(parse_num(row.split("|")[6].strip()) for row in new_normal_rows)
    pension_daily = sum(parse_num(row.split("|")[6].strip()) for row in new_pension_rows)
    normal_hold = sum(parse_num(row.split("|")[7].strip()) for row in new_normal_rows)
    pension_hold = sum(parse_num(row.split("|")[7].strip()) for row in new_pension_rows)

    cum_match = re.search(r'累计总收益[：:]*([+-]?[\d,]+\.\d{2})', old_content)
    cumulative = cum_match.group(1) if cum_match else "+30,187.71"

    # 拼接新的 holdings.md
    sep = "\n"
    normal_header = "| 序号 | 基金代码 | 基金名称 | 类型 | 总金额(¥) | 日收益(¥) | 持有收益(¥) | 持有收益率 |"
    normal_sep_row = "|-----|---------|---------|------|-----------|----------|------------|----------|"
    pension_header = normal_header
    pension_sep_row = normal_sep_row

    parts = []
    parts.append("# 持仓台账 — 巅峰资本管理有限公司")
    parts.append("# Portfolio Agent 管理 | 建立时间：2026-04-06")
    parts.append(f"# 数据基准日：{date_str}")
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## 账户一：普通基金账户")
    parts.append("")
    parts.append(normal_header)
    parts.append(normal_sep_row)
    for row in new_normal_rows:
        parts.append(row)
    parts.append("")
    parts.append(f"**账户一小计：¥{normal_total:,.2f}**")
    parts.append(f"- {date_str[5:]}日盈亏：{normal_daily:+,.2f}¥")
    parts.append(f"- 持有总收益：{normal_hold:+,.2f}¥")
    parts.append(f"- 累计总收益：{cumulative}¥")
    parts.append("")

    if warnings:
        parts.append("> ⚠️ OCR识别备注：")
        for w in warnings:
            parts.append(f"> - {w}")
        parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("## 账户二：个人养老金账户")
    parts.append("")
    parts.append(pension_header)
    parts.append(pension_sep_row)
    for row in new_pension_rows:
        parts.append(row)
    parts.append("")
    parts.append(f"**账户二小计：¥{pension_total:,.2f}**")
    parts.append(f"- {date_str[5:]}日盈亏：{pension_daily:+,.2f}¥")
    parts.append(f"- 持有总收益：{pension_hold:+,.2f}¥")
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## 总资产汇总")
    parts.append("")
    parts.append("| 项目 | 金额 |")
    parts.append("|-----|------|")
    parts.append(f"| 普通账户 | ¥{normal_total:,.2f} |")
    parts.append(f"| 养老金账户 | ¥{pension_total:,.2f} |")
    parts.append(f"| **总资产** | **¥{grand_total:,.2f}** |")
    parts.append(f"| 今日盈亏 | {normal_daily + pension_daily:+,.2f}¥ |")
    parts.append(f"| 普通账户持有收益 | {normal_hold:+,.2f}¥ |")
    parts.append(f"| 普通账户累计收益 | {cumulative}¥ |")
    parts.append(f"| 养老金账户持有收益 | {pension_hold:+,.2f}¥ |")
    parts.append("")
    parts.append("---")
    parts.append(f"*数据基准：{date_str} | Portfolio Agent 更新 | OCR云端自动识别*")
    parts.append("")

    new_content = sep.join(parts)

    return new_content, {
        "updated": True,
        "date": date_str,
        "normal_count": len(new_normal_rows),
        "pension_count": len(new_pension_rows),
        "normal_total": f"{normal_total:,.2f}",
        "pension_total": f"{pension_total:,.2f}",
        "grand_total": f"{grand_total:,.2f}",
        "normal_daily": f"{normal_daily:+,.2f}",
        "pension_daily": f"{pension_daily:+,.2f}",
        "normal_hold": f"{normal_hold:+,.2f}",
        "pension_hold": f"{pension_hold:+,.2f}",
        "issues": issues,
        "warnings": warnings,
        "missing_funds": sorted(list(missing_from_ocr)),
        "extra_funds": sorted(list(extra_in_ocr)),
        "funds_normal": [{"code": f["code"], "name": f["name"][:20], "nums": f["numbers"]} for f in funds_normal],
        "funds_pension": [{"code": f["code"], "name": f["name"][:20], "nums": f["numbers"]} for f in funds_pension],
    }


def main():
    ocr_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ocr_combined.txt"
    holdings_file = sys.argv[2] if len(sys.argv) > 2 else "portfolio/holdings.md"

    with open(ocr_file, "r", encoding="utf-8") as f:
        ocr_text = f.read()
    with open(holdings_file, "r", encoding="utf-8") as f:
        old_content = f.read()

    print("=" * 60)
    print("OCR 原始文本（前2000字符）：")
    print("-" * 60)
    print(ocr_text[:2000])
    print("-" * 60)

    funds_normal, funds_pension, total_normal, total_pension = parse_ocr_data(ocr_text, old_content)

    print(f"\n识别结果：普通 {len(funds_normal)} 支，养老金 {len(funds_pension)} 支")

    if len(funds_normal) < 15 and len(funds_pension) == 0:
        print("\nOCR 数据严重不足，不更新 holdings.md")
        status = {
            "updated": False,
            "funds_normal_count": len(funds_normal),
            "funds_pension_count": len(funds_pension),
        }
        with open("/tmp/update_status.json", "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        with open("/tmp/base_date.txt", "w") as f:
            f.write("unknown")
        return

    new_content, status = generate_holdings_md(funds_normal, funds_pension, old_content, ocr_text)

    with open(holdings_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\nholdings.md 已更新")
    print(f"  普通账户: {status['normal_count']} 支，合计 ¥{status['normal_total']}")
    print(f"  养老金账户: {status['pension_count']} 支，合计 ¥{status['pension_total']}")
    print(f"  总资产: ¥{status['grand_total']}")

    with open("/tmp/update_status.json", "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    with open("/tmp/base_date.txt", "w") as f:
        f.write(status["date"])


if __name__ == "__main__":
    main()
