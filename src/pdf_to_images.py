#!/usr/bin/env python3
"""
PDF → 逐页图片
使用 PyMuPDF (fitz) 将 PDF 每页渲染为高清 PNG 图片。
"""

import os
import sys
from pathlib import Path
import fitz  # PyMuPDF


def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 200) -> list[str]:
    """
    将 PDF 逐页渲染为 PNG 图片。
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        dpi: 渲染分辨率（默认 200，兼顾清晰度和速度）
    
    Returns:
        生成的图片路径列表
    """
    doc = fitz.open(pdf_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    image_paths = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # zoom = dpi / 72 (72 是 PDF 默认 DPI)
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        
        # 渲染为 pixmap
        pix = page.get_pixmap(matrix=matrix)
        
        # 保存为 PNG
        img_path = output_path / f"page_{page_num + 1:03d}.png"
        pix.save(str(img_path))
        image_paths.append(str(img_path))
        print(f"  ✅ Page {page_num + 1} → {img_path.name}")
    
    doc.close()
    print(f"\n📄 共 {len(image_paths)} 页，输出到: {output_dir}")
    return image_paths


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python pdf_to_images.py <pdf_path> [output_dir] [dpi]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output_images"
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    
    print(f"📖 正在处理: {pdf_path}")
    print(f"📐 DPI: {dpi}")
    
    pdf_to_images(pdf_path, output_dir, dpi)
