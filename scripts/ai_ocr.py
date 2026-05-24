#!/usr/bin/env python3
"""
巅峰资本 - AI 智能截图识别
使用 DeepSeek Vision API 理解持仓截图内容，替代传统 Tesseract OCR。
输出结构化 JSON 供 update_holdings.py 直接消费，避免文本解析误差。
"""
import os, sys, json, base64, urllib.request, glob

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"

PROMPT = """你是一个基金持仓截图分析专家。上面这些是用户手机截图（可能多张，是同一页面滚动截取的不同部分）。

请仔细识别每张截图中的基金持仓表格数据，输出严格的 JSON。

## 表格结构

截图来自基金交易APP，表格包含以下列：
- 基金代码：6位数字
- 基金名称：中文
- 总金额/持有金额：如 ¥12,345.67
- 日收益/昨日收益：如 +123.45 或 -67.89
- 持有收益：如 +1,234.56
- 持有收益率：如 +12.34% 或 -5.67%

## 规则

1. 逐行识别，不要遗漏任何基金
2. 金额中逗号是千分位分隔符，数字要完整保留
3. 正收益带 +，负收益带 -
4. 如果截图标题或内容出现"个人养老金"/"养老金账户"/"账户二"，该区域基金归类为 pension
5. 普通基金账户的基金归类为 normal
6. 如果截图顶部显示"总资产"数值，提取它
7. 多张截图展示的是同一页面的不同滚动位置，可能存在重叠，对相同基金代码去重，保留第一次出现的完整数据
8. 基金名称要完整，包括括号内的A/C/人民币等后缀

## 输出 JSON 格式

```json
{
  "funds": [
    {
      "code": "012920",
      "name": "易方达全球成长精选混合(QDII)A(人民币)",
      "total_amount": "50,423.81",
      "daily_return": "+659.16",
      "holding_return": "+19,537.55",
      "holding_return_pct": "+52.97%",
      "account": "normal"
    }
  ]
}
```

只输出 JSON，不要任何解释文字。"""


def analyze_screenshots(screenshot_dir):
    """用 DeepSeek Vision 分析所有截图，返回结构化基金数据"""
    screenshots = sorted(glob.glob(os.path.join(screenshot_dir, "*")))
    if not screenshots:
        print("没有截图文件")
        return None

    print(f"AI 识别 {len(screenshots)} 张截图...")

    # 构建 DeepSeek Vision API 请求（OpenAI 兼容格式）
    content = []
    for img_path in screenshots:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(img_path)[1].lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
        data_url = f"data:{mime};base64,{img_b64}"
        content.append({
            "type": "image_url",
            "image_url": {"url": data_url}
        })
        print(f"  [{len(content)}/{len(screenshots)}] {os.path.basename(img_path)} ({len(img_b64):,} chars base64)")

    content.append({"type": "text", "text": PROMPT})

    body = {
        "model": MODEL,
        "max_tokens": 8192,
        "messages": [{"role": "user", "content": content}]
    }

    print(f"调用 {MODEL}...")
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode() if e.fp else ""
        print(f"API 错误 {e.code}: {err_body[:500]}")
        return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None

    # DeepSeek 响应格式: choices[0].message.content
    text = ""
    choices = result.get("choices", [])
    if choices:
        text = choices[0].get("message", {}).get("content", "")

    if not text:
        print("API 返回空内容")
        return None

    # 解析 JSON（可能包裹在 ```json ... ``` 中）
    json_match = None
    for pattern in [r'```json\s*([\s\S]*?)\s*```', r'```\s*([\s\S]*?)\s*```', r'(\{[\s\S]*\})']:
        m = __import__('re').search(pattern, text)
        if m:
            json_match = m.group(1).strip()
            break
    if not json_match:
        json_match = text.strip()

    try:
        data = json.loads(json_match)
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        print(f"AI 原始响应（前2000字符）:\n{text[:2000]}")
        with open("/tmp/ai_raw_response.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print("原始响应已保存到 /tmp/ai_raw_response.txt")
        return None

    funds = data.get("funds", [])
    print(f"AI 识别到 {len(funds)} 支基金")

    normal_count = sum(1 for f in funds if f.get("account") != "pension")
    pension_count = sum(1 for f in funds if f.get("account") == "pension")
    print(f"  普通账户: {normal_count} 支")
    print(f"  养老金账户: {pension_count} 支")

    return data


def save_results(data, screenshot_dir, output_dir, combined_file):
    """保存 AI 识别结果"""
    os.makedirs(output_dir, exist_ok=True)

    funds = data.get("funds", [])

    # 1. 保存结构化 JSON（供 update_holdings.py 直接消费）
    json_path = "/tmp/ai_funds.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"结构化数据已保存: {json_path}")

    # 2. 生成 OCR 兼容格式文本（供 Issue 评论展示）
    text_parts = []
    text_parts.append("=== AI 智能识别结果 ===\n")
    for f in funds:
        account_tag = "[养老金]" if f.get("account") == "pension" else "[普通]"
        text_parts.append(
            f"基金代码: {f.get('code', '?')}\n"
            f"基金名称: {f.get('name', '?')}\n"
            f"总金额: {f.get('total_amount', '?')}\n"
            f"日收益: {f.get('daily_return', '?')}\n"
            f"持有收益: {f.get('holding_return', '?')}\n"
            f"持有收益率: {f.get('holding_return_pct', '?')}\n"
            f"账户: {account_tag}\n"
        )
    combined = "\n".join(text_parts)
    with open(combined_file, "w", encoding="utf-8") as f:
        f.write(combined)
    print(f"兼容文本已保存: {combined_file}")

    # 3. 保存各截图单独的结果
    for i in range(len(glob.glob(os.path.join(screenshot_dir, "*")))):
        out_txt = os.path.join(output_dir, f"result_{i+1:02d}.txt")
        with open(out_txt, "w", encoding="utf-8") as f:
            f.write(combined)
        break  # AI 合并了所有截图，只写一份汇总

    return json_path


def main():
    screenshot_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/screenshots"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ocr_results"
    combined_file = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ocr_combined.txt"

    if not API_KEY:
        print("DEEPSEEK_API_KEY 未设置，无法使用 AI OCR")
        sys.exit(2)

    data = analyze_screenshots(screenshot_dir)
    if not data:
        sys.exit(3)

    save_results(data, screenshot_dir, output_dir, combined_file)
    print("AI OCR 完成")


if __name__ == "__main__":
    main()
