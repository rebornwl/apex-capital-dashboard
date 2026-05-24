#!/usr/bin/env python3
"""从Issue body中提取图片（base64或URL）"""
import re, os, sys, base64, urllib.request


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


def _download_url(url, timeout=30):
    """下载 URL 图片，使用 GITHUB_TOKEN 认证（私有仓库需要）"""
    req = urllib.request.Request(url)
    if GITHUB_TOKEN:
        req.add_header("Authorization", f"token {GITHUB_TOKEN}")
    req.add_header("Accept", "image/*, */*")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def extract_images(issue_body_file, output_dir):
    with open(issue_body_file, "r", encoding="utf-8", errors="ignore") as f:
        body = f.read()

    os.makedirs(output_dir, exist_ok=True)
    count = 0

    # 1. 查找 base64 图片
    pattern = r'data:image/(\w+);base64,([A-Za-z0-9+/=\s]+)'
    matches = re.findall(pattern, body)
    if matches:
        print(f"找到 {len(matches)} 张 base64 图片")
        for i, (fmt, b64data) in enumerate(matches):
            b64data = re.sub(r'\s+', '', b64data)
            ext = "jpg" if fmt in ("jpeg", "jfif") else fmt
            filepath = os.path.join(output_dir, f"screenshot_{i+1:02d}.{ext}")
            try:
                with open(filepath, "wb") as imgf:
                    imgf.write(base64.b64decode(b64data))
                size = os.path.getsize(filepath)
                print(f"  OK screenshot_{i+1:02d}.{ext} ({size:,} bytes)")
                count += 1
            except Exception as e:
                print(f"  FAIL screenshot_{i+1:02d}.{ext}: {e}")

    # 2. 查找 GitHub 图片 URL（github.com / githubusercontent.com 均覆盖）
    img_url_patterns = [
        r'!\[.*?\]\((https://github\.com/[^)\s]+)\)',
        r'!\[.*?\]\((https://user-images\.githubusercontent\.com/[^)\s]+)\)',
        r'<img[^>]+src="(https://github\.com/[^"\s]+)"',
        r'<img[^>]+src="(https://user-images\.githubusercontent\.com/[^"\s]+)"',
        r'(https://github\.com/user-attachments/assets/[a-f0-9-]+)',
    ]
    img_urls = []
    for pat in img_url_patterns:
        found = re.findall(pat, body)
        for u in found:
            if u not in img_urls:
                img_urls.append(u)

    if img_urls:
        print(f"找到 {len(img_urls)} 张 URL 图片")
        for i, url in enumerate(img_urls):
            ext = url.split('/')[-1].split('?')[0].split('.')[-1]
            if ext not in ('png', 'jpg', 'jpeg', 'gif', 'webp'):
                ext = 'png'
            filepath = os.path.join(output_dir, f"screenshot_{count+1:02d}.{ext}")
            try:
                data = _download_url(url)
                with open(filepath, "wb") as f:
                    f.write(data)
                print(f"  OK screenshot_{count+1:02d}.{ext} ({len(data):,} bytes)")
                count += 1
            except Exception as e:
                print(f"  FAIL screenshot_{count+1:02d}.{ext}: {e}")

    if count == 0:
        print("未找到任何图片 — 请确认截图已正确粘贴到 Issue 中")

    return count


if __name__ == "__main__":
    issue_body_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/issue_body.txt"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/screenshots"
    extract_images(issue_body_file, output_dir)
