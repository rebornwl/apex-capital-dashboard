#!/usr/bin/env python3
"""OCR识别截图"""
import subprocess, os, sys, glob


def ocr_screenshots(screenshot_dir, output_dir, combined_file):
    os.makedirs(output_dir, exist_ok=True)
    screenshots = sorted(glob.glob(os.path.join(screenshot_dir, "*")))
    if not screenshots:
        print("没有截图文件")
        return

    print(f"开始 OCR 识别 {len(screenshots)} 张截图...")
    all_text_parts = []

    for i, img_path in enumerate(screenshots):
        fname = os.path.basename(img_path)
        print(f"[{i+1}/{len(screenshots)}] {fname}")

        try:
            result = subprocess.run(
                ["tesseract", img_path, "stdout", "-l", "chi_sim+eng", "--psm", "6"],
                capture_output=True, text=True, timeout=120
            )
            text = result.stdout.strip()
            print(f"  识别到 {len(text)} 字符")

            out_txt = os.path.join(output_dir, f"result_{i+1:02d}.txt")
            with open(out_txt, "w", encoding="utf-8") as f:
                f.write(text)

            all_text_parts.append(f"=== 截图 {i+1}: {fname} ===\n{text}")
            preview = text[:300].replace("\n", " | ")
            print(f"  预览: {preview}...")

        except subprocess.TimeoutExpired:
            print(f"  OCR 超时")
        except Exception as e:
            print(f"  OCR 失败: {e}")
        print()

    combined = "\n\n".join(all_text_parts)
    with open(combined_file, "w", encoding="utf-8") as f:
        f.write(combined)

    print(f"OCR 完成，共识别 {len(screenshots)} 张截图，合并文本 {len(combined)} 字符")


if __name__ == "__main__":
    screenshot_dir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/screenshots"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ocr_results"
    combined_file = sys.argv[3] if len(sys.argv) > 3 else "/tmp/ocr_combined.txt"
    ocr_screenshots(screenshot_dir, output_dir, combined_file)
