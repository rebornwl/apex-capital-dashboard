#!/usr/bin/env python3
"""
巅峰资本 - GitHub Actions 云端版数据更新脚本
从 portfolio/holdings.md 读取持仓数据，拉取天天基金实时估值，
生成 data.json 供前端加载。专为 GitHub Actions 环境设计。
"""

import json
import re
import os
import urllib.request
from datetime import datetime

# 路径配置（GitHub Actions 工作目录为仓库根目录）
HOLDINGS_MD = os.path.join(os.getenv("GITHUB_WORKSPACE", "."), "portfolio", "holdings.md")
OUTPUT_DIR = os.getenv("GITHUB_WORKSPACE", ".")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "data.json")

# 天天基金 API
ESTIMATE_URL = "http://fundgz.1234567.com.cn/js/{code}.js"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'http://fund.eastmoney.com/'
}

# 基金类型标签映射
TAG_MAP = {
    "QDII混合": "qdii", "QDII指数": "qdii", "QDII股票": "qdii",
    "主动混合": "mix", "混合偏债": "bond",
    "指数型": "index", "指数增强Y": "fof", "指数型Y": "fof",
    "股票型": "stock", "养老FOF": "fof",
}

def get_tag(type_str):
    for key, val in TAG_MAP.items():
        if key in type_str:
            return val
    return "mix"

def is_trading_day():
    """判断是否为交易日（排除周末）"""
    date = datetime.now()
    return date.weekday() < 5

def fetch_estimate(code):
    """获取单只基金实时估值"""
    url = ESTIMATE_URL.format(code=code)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode('utf-8', errors='ignore')
        match = re.search(r'\((.+)\)', raw, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            return {
                "status": "success",
                "code": data.get("fundcode", code),
                "name": data.get("name", ""),
                "gsz": float(data.get("gsz", 0)),
                "gszzl": float(data.get("gszzl", 0)),
                "gztime": data.get("gztime", ""),
                "dwjz": float(data.get("dwjz", 0)),
                "jzrq": data.get("jzrq", ""),
            }
        return {"status": "error", "code": code, "message": "parse_failed"}
    except Exception as e:
        return {"status": "error", "code": code, "message": str(e)}

def parse_holdings_md(filepath):
    """从 holdings.md 解析持仓数据"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    result = {"normal": [], "pension": [], "summary": {}}

    # 解析普通账户
    normal_section = re.search(r'## 账户一：普通基金账户\s*\n\s*\n(.+?)(?=\*\*账户一小计)', content, re.DOTALL)
    if normal_section:
        rows = re.findall(
            r'\|\s*(\d+)\s*\|\s*(\d{6})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|'
            r'\s*([\d,]+\.?\d*)\s*\|\s*([+-]?[\d,]+\.?\d*)\s*\|'
            r'\s*([+-]?[\d,]+\.?\d*)\s*\|\s*([+-]?[\d.]+%)\s*\|',
            normal_section.group(1)
        )
        for row in rows:
            seq, code, name, ftype, mv_str, daily_str, hold_str, hold_pct_str = row
            mv = float(mv_str.replace(',', ''))
            today_pnl = float(daily_str.replace(',', ''))
            hold_pnl = float(hold_str.replace(',', ''))
            hold_pnl_pct = float(hold_pct_str.replace('%', '').replace('+', ''))
            cost = round(mv - hold_pnl, 2)
            result["normal"].append({
                "code": code, "name": name.strip(), "type": ftype.strip(),
                "tag": get_tag(ftype), "market_value": mv, "cost": cost,
                "today_pnl_base": today_pnl, "hold_pnl_base": hold_pnl,
                "hold_pnl_pct_base": hold_pnl_pct,
            })

    # 解析养老金账户
    pension_section = re.search(r'## 账户二：个人养老金账户\s*\n\s*\n(.+?)(?=\*\*账户二小计)', content, re.DOTALL)
    if pension_section:
        rows = re.findall(
            r'\|\s*(\d+)\s*\|\s*(\d{6})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|'
            r'\s*([\d,]+\.?\d*)\s*\|\s*([+-]?[\d,]+\.?\d*)\s*\|'
            r'\s*([+-]?[\d,]+\.?\d*)\s*\|\s*([+-]?[\d.]+%)\s*\|',
            pension_section.group(1)
        )
        for row in rows:
            seq, code, name, ftype, mv_str, daily_str, hold_str, hold_pct_str = row
            mv = float(mv_str.replace(',', ''))
            today_pnl = float(daily_str.replace(',', ''))
            hold_pnl = float(hold_str.replace(',', ''))
            hold_pnl_pct = float(hold_pct_str.replace('%', '').replace('+', ''))
            cost = round(mv - hold_pnl, 2)
            result["pension"].append({
                "code": code, "name": name.strip(), "type": ftype.strip(),
                "tag": get_tag(ftype), "market_value": mv, "cost": cost,
                "today_pnl_base": today_pnl, "hold_pnl_base": hold_pnl,
                "hold_pnl_pct_base": hold_pnl_pct, "is_pension": True,
            })

    # 汇总
    sm = re.search(r'\*\*账户一小计[：:]\s*¥([\d,]+\.?\d*)\*\*', content)
    if sm: result["summary"]["normal_total"] = float(sm.group(1).replace(',', ''))
    sp = re.search(r'\*\*账户二小计[：:]\s*¥([\d,]+\.?\d*)\*\*', content)
    if sp: result["summary"]["pension_total"] = float(sp.group(1).replace(',', ''))
    st = re.search(r'\*\*总资产\*\*\s*\|\s*\*\*¥([\d,]+\.?\d*)\*\*', content)
    if st: result["summary"]["grand_total"] = float(st.group(1).replace(',', ''))

    return result

def run_update():
    """主函数：读取持仓 + 拉取估值，生成JSON"""
    now = datetime.now()
    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 开始云端更新...")
    print(f"  GitHub Actions 运行环境")
    print(f"  交易日判断: {'是' if is_trading_day() else '否（周末）'}")

    if not os.path.exists(HOLDINGS_MD):
        print(f"ERROR: 找不到持仓文件 {HOLDINGS_MD}")
        return None

    base = parse_holdings_md(HOLDINGS_MD)
    normal_list = base["normal"]
    pension_list = base["pension"]
    print(f"  读取持仓: 普通 {len(normal_list)} 支 + 养老金 {len(pension_list)} 支")

    all_funds = []
    total_today_pnl = 0
    total_normal_value = 0
    total_pension_value = 0
    total_cost = 0

    # 拉取所有基金估值
    for h in normal_list + pension_list:
        is_pension = h.get("is_pension", False)
        est = fetch_estimate(h["code"])

        if est.get("status") == "success":
            today_change_pct = est["gszzl"]
            nav = est["gsz"]
            nav_date = est["gztime"].split(" ")[0] if est["gztime"] else ""
            name = est["name"] or h["name"]
        else:
            today_change_pct = 0
            nav = 0
            nav_date = ""
            name = h["name"]

        base_mv = h["market_value"]
        today_pnl = base_mv * today_change_pct / 100
        live_mv = base_mv + today_pnl
        cost = h["cost"]
        hold_pnl = h["hold_pnl_base"] + today_pnl
        hold_pnl_pct = ((live_mv - cost) / cost) * 100 if cost > 0 else 0

        warn = []
        if not is_pension:
            if hold_pnl_pct < -10:
                warn.append(f"CRO预警:亏损{hold_pnl_pct:.1f}%")
            if live_mv / (base["summary"].get("grand_total", 280000)) < 0.01:
                warn.append("仓位<1%,建议清仓整合")

        fund_data = {
            "code": h["code"], "name": name, "type": h["type"], "tag": h["tag"],
            "nav": round(nav, 4), "nav_date": nav_date,
            "today_pct": round(today_change_pct, 2),
            "market_value": round(live_mv, 2),
            "today_pnl": round(today_pnl, 2),
            "hold_pnl": round(hold_pnl, 2),
            "hold_pnl_pct": round(hold_pnl_pct, 2),
            "profit": "up" if hold_pnl >= 0 else "down",
            "warnings": warn,
        }
        if is_pension:
            fund_data["is_pension"] = True

        all_funds.append(fund_data)
        if is_pension:
            total_pension_value += live_mv
        else:
            total_normal_value += live_mv
        total_cost += cost
        total_today_pnl += today_pnl

        status = "✓" if est.get("status") == "success" else "✗"
        print(f"  {status} {h['code']} {name[:16]:16s} 涨跌{today_change_pct:+6.2f}% 市值¥{live_mv:>10,.0f}")

    # 汇总
    total_value = total_normal_value + total_pension_value
    total_hold_pnl = total_value - total_cost

    type_stats = {}
    for f in all_funds:
        t = f["tag"]
        if t not in type_stats:
            type_stats[t] = {"value": 0, "count": 0}
        type_stats[t]["value"] += f["market_value"]
        type_stats[t]["count"] += 1

    trading_status = "交易中" if is_trading_day() and 9 <= now.hour < 15 else "已收盘" if is_trading_day() else "休市"

    output = {
        "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "update_time_short": now.strftime("%m-%d %H:%M"),
        "is_trading_day": is_trading_day(),
        "trading_status": trading_status,
        "source": "github-actions",
        "run_id": os.getenv("GITHUB_RUN_ID", "local"),
        "summary": {
            "total_value": round(total_value, 2),
            "normal_value": round(total_normal_value, 2),
            "pension_value": round(total_pension_value, 2),
            "total_cost": round(total_cost, 2),
            "total_hold_pnl": round(total_hold_pnl, 2),
            "total_hold_pnl_pct": round((total_hold_pnl / total_cost) * 100, 2) if total_cost > 0 else 0,
            "today_pnl": round(total_today_pnl, 2),
            "normal_today_pnl": round(total_today_pnl - sum(f["today_pnl"] for f in all_funds if f.get("is_pension")), 2),
            "pension_today_pnl": round(sum(f["today_pnl"] for f in all_funds if f.get("is_pension")), 2),
            "fund_count": len(all_funds),
            "normal_count": len(normal_list),
            "pension_count": len(pension_list),
        },
        "type_distribution": {
            k: {
                "value": round(v["value"], 2), "count": v["count"],
                "pct": round((v["value"] / total_value) * 100, 1) if total_value > 0 else 0
            }
            for k, v in sorted(type_stats.items(), key=lambda x: -x[1]["value"])
        },
        "funds": all_funds,
        "rankings": {
            "top_profit": sorted(
                [{"code": f["code"], "name": f["name"], "pct": f["hold_pnl_pct"], "pnl": f["hold_pnl"]}
                 for f in all_funds if not f.get("is_pension")],
                key=lambda x: -x["pct"]
            )[:5],
            "top_loss": sorted(
                [{"code": f["code"], "name": f["name"], "pct": f["hold_pnl_pct"], "pnl": f["hold_pnl"]}
                 for f in all_funds if not f.get("is_pension")],
                key=lambda x: x["pct"]
            )[:5],
        }
    }

    # 生成日报
    report = []
    report.append(f"📊 巅峰资本 · 基金持仓日报（云端自动生成）")
    report.append(f"⏰ {output['update_time']} | {trading_status}")
    report.append(f"")
    report.append(f"💰 总资产：¥{total_value:,.2f}")
    report.append(f"   普通账户：¥{total_normal_value:,.2f}  |  养老金：¥{total_pension_value:,.2f}")
    report.append(f"📈 今日盈亏：{'+' if total_today_pnl >= 0 else ''}¥{total_today_pnl:,.2f}")
    report.append(f"📊 持有收益：{'+' if total_hold_pnl >= 0 else ''}¥{total_hold_pnl:,.2f} ({output['summary']['total_hold_pnl_pct']:+.2f}%)")

    if output["rankings"]["top_profit"]:
        top = output["rankings"]["top_profit"][0]
        report.append(f"🏆 今日最强：{top['name']} ({top['pct']:+.2f}%)")
    if output["rankings"]["top_loss"]:
        worst = output["rankings"]["top_loss"][0]
        report.append(f"⚠ 今日最弱：{worst['name']} ({worst['pct']:+.2f}%)")

    loss_funds = [f for f in all_funds if f["hold_pnl_pct"] < -5 and not f.get("is_pension")]
    if loss_funds:
        report.append(f"")
        report.append(f"🚨 需关注亏损仓位：")
        for f in sorted(loss_funds, key=lambda x: x["hold_pnl_pct"]):
            report.append(f"   • {f['name']}({f['code']}) {f['hold_pnl_pct']:+.2f}% ¥{f['market_value']:,.0f}")

    output["report_text"] = "\n".join(report)

    # 保存
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ data.json 已生成")
    print(f"📊 总资产：¥{total_value:,.2f}")
    print(f"📈 今日盈亏：{'+' if total_today_pnl >= 0 else ''}¥{total_today_pnl:,.2f}")

    return output

if __name__ == "__main__":
    data = run_update()
    if data:
        print(f"\n{'='*50}")
        print(data["report_text"])
        print(f"\n✅ 云端更新完成")
    else:
        print("❌ 更新失败")
        exit(1)
