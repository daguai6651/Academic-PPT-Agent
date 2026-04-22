#!/usr/bin/env python3
"""
辅助脚本：利用 Qwen3-VL 定位表格坐标，并使用 PyMuPDF 精确裁切表格图片。
"""

import os
import sys
import json
import base64
import fitz
from openai import OpenAI

# 配置
API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen3-vl-plus"
PDF_PATH = "test_data/pdfs/attention_is_all_you_need.pdf"
OUTPUT_DIR = "output_images"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def get_bbox_for_page(page_num: int, table_desc: str):
    """
    询问 Qwen3-VL 表格的坐标。
    """
    # 1. 获取页面图片
    doc = fitz.open(PDF_PATH)
    page = doc[page_num - 1]  # 0-indexed
    pix = page.get_pixmap(dpi=150)  # 150 DPI 足够定位了
    img_bytes = pix.tobytes("png")
    img_b64 = base64.b64encode(img_bytes).decode()
    
    # 2. 构造 Prompt
    prompt = f"""
    Look at this page from a research paper.
    Find the bounding box of the main experiment table: {table_desc}.
    
    Return ONLY a JSON object with the bounding box coordinates (0.0 to 1.0 relative to the image size):
    {{"top": 0.0, "bottom": 1.0, "left": 0.0, "right": 1.0}}
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        content = response.choices[0].message.content
        # 提取 JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        return json.loads(content)
    except Exception as e:
        print(f"❌ Page {page_num} API error: {e}")
        return None

def crop_table(page_num: int, bbox: dict, output_filename: str):
    """
    根据坐标裁切表格。
    """
    doc = fitz.open(PDF_PATH)
    page = doc[page_num - 1]
    
    # 获取页面尺寸
    page_rect = page.rect
    w = page_rect.width
    h = page_rect.height
    
    # 计算绝对坐标 (加一点 padding 防止裁切掉边框)
    padding = 20  # 像素
    x0 = max(0, bbox["left"] * w - padding)
    y0 = max(0, bbox["top"] * h - padding)
    x1 = min(w, bbox["right"] * w + padding)
    y1 = min(h, bbox["bottom"] * h + padding)
    
    clip_rect = fitz.Rect(x0, y0, x1, y1)
    
    # 高 DPI 渲染以获清晰表格
    mat = fitz.Matrix(3, 3)  # 300% 缩放 -> ~200-300 DPI 级别的清晰度
    pix = page.get_pixmap(matrix=mat, clip=clip_rect)
    
    out_path = os.path.join(OUTPUT_DIR, output_filename)
    pix.save(out_path)
    print(f"✅ Saved {output_filename} ({pix.width}x{pix.height})")

def main():
    # 定义需要裁切的表格信息
    tasks = [
        {
            "page": 8,
            "desc": "Table 2: The Transformer achieves better BLEU scores...",
            "out_file": "table_main_clean.png"
        },
        {
            "page": 9,
            "desc": "Table 3: Variations on the Transformer architecture...",
            "out_file": "table_ablation_clean.png"
        }
    ]
    
    for task in tasks:
        print(f"\n--- Processing Page {task['page']} ---")
        bbox = get_bbox_for_page(task["page"], task["desc"])
        
        if bbox:
            print(f"  🎯 Detected BBox: {bbox}")
            # 简单的有效性检查
            if all(k in bbox for k in ["top", "bottom", "left", "right"]):
                crop_table(task["page"], bbox, task["out_file"])
            else:
                print(f"  ⚠️ Invalid bbox format: {bbox}")
        else:
            print(f"  ❌ Failed to get bbox for Page {task['page']}")

if __name__ == "__main__":
    if not API_KEY:
        print("❌ Missing DASHSCOPE_API_KEY")
        sys.exit(1)
    main()
