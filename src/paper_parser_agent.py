#!/usr/bin/env python3
"""
论文解析 Agent — Step 1 测试脚本
PDF → 逐页图片 → Qwen3-VL 逐页提取结构化内容
"""

import os
import sys
import json
import base64
from pathlib import Path
from openai import OpenAI


# ============================================================
# 配置
# ============================================================
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
QWEN_VL_MODEL = "qwen3-vl-plus-2025-12-19"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


# ============================================================
# PDF → 图片
# ============================================================
def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 200) -> list[str]:
    """将 PDF 逐页渲染为 PNG 图片。"""
    import fitz
    
    doc = fitz.open(pdf_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    image_paths = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)
        img_path = output_path / f"page_{page_num + 1:03d}.png"
        pix.save(str(img_path))
        image_paths.append(str(img_path))
        print(f"  ✅ Page {page_num + 1} → {img_path.name}")
    
    doc.close()
    print(f"\n📄 共 {len(image_paths)} 页，输出到: {output_dir}")
    return image_paths


# ============================================================
# Qwen3-VL 逐页提取
# ============================================================
PER_PAGE_PROMPT = """你是一个学术论文解析专家。请仔细分析这张论文页面的内容，提取以下信息并以 JSON 格式输出：

{
    "page_number": 页码,
    "page_type": "title_page" 或 "abstract" 或 "introduction" 或 "method" 或 "experiment" 或 "conclusion" 或 "references" 或 "appendix" 或 "other",
    "section_title": "该页的章节标题（如果没有则为 null）",
    "content_paragraphs": ["段落1", "段落2", ...],
    "formulas": [
        {"latex": "LaTeX 公式代码", "description": "公式含义简述"}
    ],
    "tables": [
        {"caption": "表格标题或描述", "markdown": "Markdown 表格内容"}
    ],
    "figures": [
        {"caption": "图注", "description": "图的内容描述"}
    ],
    "key_terms": ["关键术语1", "关键术语2"]
}

注意：
1. content_paragraphs 只保留核心内容，每段不超过 200 字
2. 公式请尽量以 LaTeX 格式提取
3. 表格请转换为 Markdown 表格格式
4. 如果该页没有某类内容，对应字段为空数组或 null
5. 只输出 JSON，不要输出其他内容"""


def image_to_base64(image_path: str) -> str:
    """将图片转为 base64 data URL。"""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def extract_page_content(client: OpenAI, image_path: str, page_num: int) -> dict:
    """调用 Qwen3-VL 提取单页内容。"""
    image_b64 = image_to_base64(image_path)
    
    response = client.chat.completions.create(
        model=QWEN_VL_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_b64},
                    },
                    {
                        "type": "text",
                        "text": PER_PAGE_PROMPT,
                    }
                ]
            }
        ],
        temperature=0.1,
        max_tokens=4000,
    )
    
    content = response.choices[0].message.content
    
    # 尝试解析 JSON
    try:
        # 尝试直接解析
        result = json.loads(content)
    except json.JSONDecodeError:
        # 尝试从 markdown 代码块中提取
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
            result = json.loads(json_str)
        elif "```" in content:
            json_str = content.split("```")[1].strip()
            result = json.loads(json_str)
        else:
            # 直接返回原文
            result = {"raw_output": content}
    
    return result


# ============================================================
# 主函数
# ============================================================
def main(pdf_path: str, output_dir: str = "output_images"):
    # 检查 API Key
    if not DASHSCOPE_API_KEY:
        print("❌ 未设置 DASHSCOPE_API_KEY 环境变量")
        print("   请运行: export DASHSCOPE_API_KEY='your-api-key'")
        sys.exit(1)
    
    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url=BASE_URL,
    )
    
    # Step 1: PDF → 图片
    print(f"\n{'='*60}")
    print(f"Step 1: PDF → 逐页图片")
    print(f"{'='*60}")
    image_paths = pdf_to_images(pdf_path, output_dir, dpi=200)
    
    # Step 2: 逐页提取
    print(f"\n{'='*60}")
    print(f"Step 2: Qwen3-VL 逐页提取内容")
    print(f"{'='*60}")
    
    all_pages = []
    for i, img_path in enumerate(image_paths):
        page_num = i + 1
        print(f"\n📄 正在处理第 {page_num} 页...")
        
        try:
            result = extract_page_content(client, img_path, page_num)
            all_pages.append(result)
            
            # 打印摘要
            page_type = result.get("page_type", "unknown")
            section = result.get("section_title", "N/A")
            formulas = len(result.get("formulas", []))
            tables = len(result.get("tables", []))
            print(f"   类型: {page_type}")
            print(f"   章节: {section}")
            print(f"   公式: {formulas} 个 | 表格: {tables} 个")
            
        except Exception as e:
            print(f"   ❌ 提取失败: {e}")
            all_pages.append({"page_number": page_num, "error": str(e)})
    
    # Step 3: 保存结果
    print(f"\n{'='*60}")
    print(f"Step 3: 保存结果")
    print(f"{'='*60}")
    
    output_json = Path(output_dir) / "per_page_results.json"
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 结果已保存: {output_json}")
    
    # 打印全文摘要
    print(f"\n{'='*60}")
    print(f"📊 全文摘要")
    print(f"{'='*60}")
    for page in all_pages:
        pn = page.get("page_number", "?")
        pt = page.get("page_type", "?")
        st = page.get("section_title", "N/A")
        print(f"  Page {pn}: [{pt}] {st}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python paper_parser_agent.py <pdf_path> [output_dir]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output_images"
    
    main(pdf_path, output_dir)
