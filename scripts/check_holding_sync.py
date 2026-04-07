#!/usr/bin/env python3
"""
巅峰资本 - GitHub holding-sync Issue 处理脚本
检查 GitHub 上未处理的 holding-sync Issue，
下载图片并触发 OCR 识别流程。
供 WorkBuddy CEO Agent 自动化调用。
"""

import json
import os
import re
import base64
import urllib.request
import subprocess
import sys
from datetime import datetime

REPO = "rebornwl/apex-capital-dashboard"
WORKSPACE = r"C:\Users\Administrator\Documents\基金监控及推荐"
HOLDINGS_MD = os.path.join(WORKSPACE, "portfolio", "holdings.md")
OCR_SCRIPT = os.path.join(os.path.expanduser("~"), ".workbuddy", "skills", "ocr-local", "scripts", "ocr.js")
GITHUB_REPO_DIR = os.path.join(os.environ.get("TEMP", "/tmp"), "apex-capital-pages")

# GitHub API
API_BASE = f"https://api.github.com/repos/{REPO}"

def gh_api(endpoint, method="GET", data=None):
    """调用 GitHub API（使用本地 gh CLI 的认证）"""
    url = f"{API_BASE}{endpoint}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "Apex-Capital-Bot",
    }
    # 使用 gh cli 获取 token
    try:
        token = subprocess.check_output(
            ["gh", "auth", "token"], capture_output=True, text=True, shell=True
        ).strip()
        if token:
            headers["Authorization"] = f"token {token}"
    except:
        pass

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"API 错误: {e}")
        return None

def get_open_issues():
    """获取所有未处理的 holding-sync Issue"""
    result = gh_api("/issues?labels=holding-sync&state=open&per_page=10")
    if not result:
        return []
    # 过滤掉 PR
    return [i for i in result if "pull_request" not in i]

def download_issue_images(issue):
    """从 Issue body 下载 base64 图片"""
    body = issue.get("body", "") or ""
    pattern = r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)'
    matches = re.findall(pattern, body)

    screenshots_dir = os.path.join(WORKSPACE, ".holding-screenshots")
    os.makedirs(screenshots_dir, exist_ok=True)

    images = []
    for i, (fmt, b64data) in enumerate(matches):
        ext = "jpg" if fmt == "jpeg" else fmt
        filename = f"issue_{issue['number']}_{i+1}.{ext}"
        filepath = os.path.join(screenshots_dir, filename)
        try:
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64data))
            size = os.path.getsize(filepath)
            images.append(filepath)
            print(f"  ✓ {filename} ({size:,} bytes)")
        except Exception as e:
            print(f"  ✗ {filename} 保存失败: {e}")

    return images

def run_ocr(image_path):
    """运行 OCR 识别"""
    try:
        result = subprocess.run(
            ["node", OCR_SCRIPT, image_path, "--lang", "chi_sim+eng"],
            capture_output=True, text=True, timeout=60,
            cwd=os.path.dirname(OCR_SCRIPT)
        )
        # 提取实际文本内容（跳过进度条等）
        output = result.stdout
        # 找到最后一个空行之后的内容
        lines = output.split("\n")
        text_lines = []
        in_text = False
        for line in lines:
            # 跳过进度和控制信息
            if line.startswith("Progress:") or line.startswith("⏳"):
                continue
            if "Recognizing text" in line or "Languages:" in line:
                continue
            if "Error opening" in line or "TESSDATA" in line or "Failed loading" in line:
                continue
            if line.strip():
                text_lines.append(line.strip())
                in_text = True
            elif in_text and not line.strip():
                in_text = False

        return "\n".join(text_lines)
    except Exception as e:
        print(f"  OCR 失败: {e}")
        return ""

def add_issue_comment(issue_number, body):
    """给 Issue 添加评论"""
    return gh_api(f"/issues/{issue_number}/comments", method="POST", data={"body": body})

def close_issue(issue_number):
    """关闭 Issue"""
    return gh_api(f"/issues/{issue_number}", method="PATCH", data={"state": "closed"})

def add_label(issue_number, label):
    """给 Issue 添加标签"""
    return gh_api(f"/issues/{issue_number}/labels", method="POST", data={"labels": [label]})

def check_for_updates():
    """主函数：检查并处理 holding-sync Issue"""
    print(f"{'='*50}")
    print(f"  巅峰资本 · 持仓截图同步检查")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    issues = get_open_issues()
    if not issues:
        print("✅ 没有待处理的 holding-sync Issue")
        return False

    print(f"📋 发现 {len(issues)} 个待处理 Issue\n")

    for issue in issues:
        issue_num = issue["number"]
        issue_title = issue["title"]
        created_at = issue["created_at"]
        labels = [l["name"] for l in issue.get("labels", [])]

        # 跳过已标记为 processing 且不是刚创建的
        if "processing" in labels:
            print(f"⏭️ Issue #{issue_num} 已在处理中，跳过")
            continue

        print(f"📥 处理 Issue #{issue_num}: {issue_title}")
        print(f"   创建时间: {created_at}")

        # 下载图片
        print(f"   下载图片...")
        images = download_issue_images(issue)

        if not images:
            print(f"   ⚠️ Issue #{issue_num} 中无图片，跳过")
            add_issue_comment(issue_num,
                "⚠️ 未检测到截图图片。\n\n请确保截图以图片形式（非链接）上传到 Issue 中。")
            continue

        # OCR 识别
        print(f"   OCR 识别 {len(images)} 张截图...")
        ocr_results = []
        for img_path in images:
            print(f"   识别 {os.path.basename(img_path)}...")
            text = run_ocr(img_path)
            ocr_results.append(text)
            # 打印前200字符预览
            preview = text[:200].replace("\n", " ")
            print(f"   → {preview}...")

        all_text = "\n\n---\n\n".join(ocr_results)

        # 标记为 processing
        add_label(issue_num, "processing")

        # 添加 OCR 结果评论
        add_issue_comment(issue_num,
            f"## 🔍 OCR 识别结果\n\n"
            f"共识别 **{len(images)}** 张截图。\n\n"
            f"<details>\n<summary>📄 点击查看原始 OCR 文本</summary>\n\n"
            f"```\n{all_text}\n```\n\n"
            f"</details>\n\n"
            f"⏳ 等待 CEO Agent 分析数据并更新 holdings.md...")

        # 保存 OCR 结果供 CEO Agent 使用
        ocr_cache_dir = os.path.join(WORKSPACE, ".holding-screenshots", "ocr-cache")
        os.makedirs(ocr_cache_dir, exist_ok=True)
        cache_file = os.path.join(ocr_cache_dir, f"issue_{issue_num}.txt")
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(f"Issue: #{issue_num} - {issue_title}\n")
            f.write(f"Created: {created_at}\n")
            f.write(f"Images: {len(images)}\n")
            f.write(f"OCR Time: {datetime.now().isoformat()}\n")
            f.write(f"\n{'='*50}\n\n")
            for i, text in enumerate(ocr_results):
                f.write(f"--- 截图 {i+1} ---\n{text}\n\n")

        print(f"\n   ✅ Issue #{issue_num} OCR 完成，结果已缓存")
        print(f"   📁 缓存文件: {cache_file}")
        print(f"   ⏳ 等待 CEO Agent 分析并更新 holdings.md\n")

    print(f"{'='*50}")
    print("✅ 检查完毕")
    return True

if __name__ == "__main__":
    has_updates = check_for_updates()
    if has_updates:
        print("\n🔔 发现新的持仓截图，需要 CEO Agent 处理！")
        print("   请运行 OCR 识别并更新 holdings.md")
    sys.exit(0 if has_updates else 1)
