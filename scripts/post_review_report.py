#!/usr/bin/env python3
"""生成审核报告并发布到Issue评论"""
import json, os, sys, urllib.request


def post_review(issue_num, status_file, ocr_file):
    with open(status_file, "r", encoding="utf-8") as f:
        status = json.load(f)
    with open(ocr_file, "r", encoding="utf-8") as f:
        ocr_text = f.read()

    repo = os.environ.get("GITHUB_REPOSITORY", "rebornwl/apex-capital-dashboard")
    token = os.environ.get("GH_TOKEN", "")

    if status.get("updated"):
        # 构建普通账户明细表
        normal_lines = []
        for f in status.get("funds_normal", []):
            nums = f["nums"]
            total = nums[0] if len(nums) >= 1 else "?"
            daily = nums[1] if len(nums) >= 2 else "?"
            hold = nums[2] if len(nums) >= 3 else "?"
            name = f.get("name", "")[:15]
            normal_lines.append(f"| {f['code']} | {name} | {total} | {daily} | {hold} |")

        pension_lines = []
        for f in status.get("funds_pension", []):
            nums = f["nums"]
            total = nums[0] if len(nums) >= 1 else "?"
            daily = nums[1] if len(nums) >= 2 else "?"
            hold = nums[2] if len(nums) >= 3 else "?"
            name = f.get("name", "")[:15]
            pension_lines.append(f"| {f['code']} | {name} | {total} | {daily} | {hold} |")

        body_parts = []
        body_parts.append("## ✅ 持仓数据已更新\n")
        body_parts.append(f"- 数据基准日：**{status['date']}**")
        body_parts.append(f"- 普通账户：**{status['normal_count']}** 支，合计 **¥{status['normal_total']}**")
        body_parts.append(f"- 养老金账户：**{status['pension_count']}** 支，合计 **¥{status['pension_total']}**")
        body_parts.append(f"- 总资产：**¥{status['grand_total']}**")
        body_parts.append(f"- 今日盈亏：{status.get('normal_daily', '?')} + {status.get('pension_daily', '?')}")

        # 差异报告
        if status.get("missing_funds"):
            body_parts.append(f"\n### ⚠️ 未识别到的基金（{len(status['missing_funds'])}支，已保留旧数据）")
            for c in status["missing_funds"]:
                body_parts.append(f"- `{c}`")

        if status.get("extra_funds"):
            body_parts.append(f"\n### ℹ️ 新识别到的基金代码")
            for c in status["extra_funds"]:
                body_parts.append(f"- `{c}`")

        if status.get("warnings"):
            body_parts.append("\n### 备注")
            for w in status["warnings"]:
                body_parts.append(f"- {w}")

        body_parts.append("\n### 普通账户明细（前10支）")
        body_parts.append("| 代码 | 名称 | 总金额 | 日收益 | 持有收益 |")
        body_parts.append("|-----|------|--------|--------|---------|")
        for line in normal_lines[:10]:
            body_parts.append(line)
        if len(normal_lines) > 10:
            body_parts.append(f"| ... 共{len(normal_lines)}支 | ... | ... | ... | ... |")

        body_parts.append("\n### 养老金账户明细")
        body_parts.append("| 代码 | 名称 | 总金额 | 日收益 | 持有收益 |")
        body_parts.append("|-----|------|--------|--------|---------|")
        for line in pension_lines:
            body_parts.append(line)

        # OCR原文
        body_parts.append("\n<details><summary>📄 OCR原始文本</summary>\n```\n")
        body_parts.append(ocr_text[:3000])
        if len(ocr_text) > 3000:
            body_parts.append("...")
        body_parts.append("\n```\n</details>")
        body_parts.append("\n> holdings.md 已自动更新，数据刷新已触发。如有误请重新截图或在WorkBuddy中修正。")

        comment_body = "\n".join(body_parts)
    else:
        comment_body = f"""## ⚠️ OCR识别数据不足

识别到的基金数量：
- 普通账户：{status.get('funds_normal_count', 0)} 支（期望 20 支）
- 养老金账户：{status.get('funds_pension_count', 0)} 支（期望 5 支）

请重新截取更清晰的持仓页面截图。

<details><summary>📄 OCR原始文本</summary>

```
{ocr_text[:3000]}
...
```

</details>

> 建议在 WorkBuddy 对话中直接发送截图让 AI 更新"""

    # 发送评论
    url = f"https://api.github.com/repos/{repo}/issues/{issue_num}/comments"
    data = json.dumps({"body": comment_body}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"token {token}",
        "Content-Type": "application/json",
        "User-Agent": "Apex-Capital-Bot"
    })
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read().decode())
    print(f"审核报告已发布: {result.get('html_url', '')}")


if __name__ == "__main__":
    issue_num = sys.argv[1] if len(sys.argv) > 1 else "0"
    status_file = sys.argv[2] if len(sys.argv) > 2 else "/tmp/update_status.json"
    ocr_file = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ocr_combined.txt"
    post_review(issue_num, status_file, ocr_file)
