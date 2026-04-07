#!/usr/bin/env python3
"""从Issue body中提取图片（base64或URL）"""
import re, os, sys, base64, urllib.request


def extract_images(issue_body_file, output_dir):
    with open(issue_body_file, "r", encoding="utf-8", errors="ignore") as f:
        body = f.read()

    os.makedirs(output_dir, exist_ok=True)
    count = 0

    # 1. 查找 base64 图片
    pattern = r'data:image/(\w+);base64,([A-Za-z0-9+/=]+)'
    matches = re.findall(pattern, body)
    if matches:
        print(f"找到 {len(matches)} 张 base64 图片")
        for i, (fmt, b64data) in enumerate(matches):
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

    # 2. 查找 GitHub 图片 URL
    if count == 0:
        img_urls = re.findall(r'!\[.*?\]\((https://github\.com/[^)]+)\)', body)
        if not img_urls:
            img_urls = re.findall(r'!\[.*?\]\((https://user-images\.githubusercontent\.com/[^)]+)\)', body)
        if img_urls:
            print(f"找到 {len(img_urls)} 张 URL 图片")
            for i, url in enumerate(img_urls):
                ext = url.split('.')[-1].split('?')[0]
                if ext not in ('png', 'jpg', 'jpeg', 'gif', 'webp'):
                    ext = 'jpg'
                filepath = os.path.join(output_dir, f"screenshot_{count+1:02d}.{ext}")
                try:
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = resp.read()
                    with open(filepath, "wb") as f:
                        f.write(data)
                    print(f"  OK screenshot_{count+1:02d}.{ext} ({len(data):,} bytes)")
                    count += 1
                except Exception as e:
                    print(f"  FAIL screenshot_{count+1:02d}.{ext}: {e}")

    if count == 0:
        print("未找到任何图片")

    return count


if __name__ == "__main__":
    issue_body_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/issue_body.txt"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/screenshots"
    extract_images(issue_body_file, output_dir)
