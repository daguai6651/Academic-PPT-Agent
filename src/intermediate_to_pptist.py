#!/usr/bin/env python3
"""
Step 3：中间格式 JSON → PPTist JSON
将论文中间格式转换为 PPTist 可识别的页面结构 JSON。
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime


# ============================================================
# PPTist 配置
# ============================================================
CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 562.5  # 16:9
THEME = {
    "backgroundColor": "#ffffff",
    "themeColors": ["#5b9bd5", "#ed7d31", "#a5a5a5", "#ffc000", "#4472c4", "#70ad47"],
    "fontColor": "#333333",
    "fontName": "",
    "outline": {"width": 2, "color": "#525252", "style": "solid"},
    "shadow": {"h": 3, "v": 3, "blur": 2, "color": "#808080"}
}


# ============================================================
# 辅助函数
# ============================================================

def nanoid(length=6):
    """简易 ID 生成。"""
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def image_to_base64(image_path: str) -> str:
    """将图片文件转为 Base64 data URL。"""
    import base64
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = image_path.rsplit(".", 1)[-1].lower()
    mime = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "gif", "webp", "svg") else "image/png"
    return f"data:{mime};base64,{b64}"


def latex_to_html(latex: str, font_size: int = 20, color: str = "#333333") -> str:
    """
    将 LaTeX 公式转为 HTML 富文本格式。
    处理常见的 LaTeX 结构：分式、上下标、根号、文本、运算符等。
    """
    import re
    
    html = latex
    
    # 1. 处理 \frac{num}{den} → 分式
    def replace_frac(m):
        num = m.group(1)
        den = m.group(2)
        return f'<span style="display: inline-flex; flex-direction: column; align-items: center; vertical-align: middle; margin: 0 3px;"><span style="border-bottom: 1px solid {color}; padding: 0 4px; font-size: {font_size}px;">{num}</span><span style="padding: 0 4px; font-size: {font_size}px;">{den}</span></span>'
    
    frac_pattern = r'\\frac\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
    html = re.sub(frac_pattern, replace_frac, html)
    
    # 2. 处理 \sqrt{...} → 根号
    def replace_sqrt(m):
        content = m.group(1)
        return f'<span style="vertical-align: middle;">√<span style="border-top: 1px solid {color}; padding: 0 2px;">{content}</span></span>'
    
    html = re.sub(r'\\sqrt\{([^{}]*)\}', replace_sqrt, html)
    
    # 3. 处理 ^{...} 上标
    html = re.sub(r'\^\{([^{}]*)\}', r'<sup style="font-size: 0.75em;">\1</sup>', html)
    
    # 4. 处理 _{...} 下标
    html = re.sub(r'_\{([^{}]*)\}', r'<sub style="font-size: 0.75em;">\1</sub>', html)
    
    # 5. 处理 ^x 和 _x（单字符）
    html = re.sub(r'\^([a-zA-Z0-9])', r'<sup style="font-size: 0.75em;">\1</sup>', html)
    html = re.sub(r'_([a-zA-Z0-9])', r'<sub style="font-size: 0.75em;">\1</sub>', html)
    
    # 6. 处理 \text{...}
    html = re.sub(r'\\text\{([^{}]*)\}', r'\1', html)
    
    # 7. 处理数学符号
    symbols = {
        r'\\cdot': '·',
        r'\\times': '×',
        r'\\div': '÷',
        r'\\pm': '±',
        r'\\mp': '∓',
        r'\\leq': '≤',
        r'\\geq': '≥',
        r'\\neq': '≠',
        r'\\approx': '≈',
        r'\\equiv': '≡',
        r'\\infty': '∞',
        r'\\sum': '∑',
        r'\\prod': '∏',
        r'\\int': '∫',
        r'\\partial': '∂',
        r'\\nabla': '∇',
        r'\\rightarrow': '→',
        r'\\leftarrow': '←',
        r'\\Rightarrow': '⇒',
        r'\\Leftarrow': '⇐',
        r'\\alpha': 'α',
        r'\\beta': 'β',
        r'\\gamma': 'γ',
        r'\\delta': 'δ',
        r'\\epsilon': 'ε',
        r'\\theta': 'θ',
        r'\\lambda': 'λ',
        r'\\mu': 'μ',
        r'\\pi': 'π',
        r'\\sigma': 'σ',
        r'\\omega': 'ω',
        r'\\Delta': 'Δ',
        r'\\Theta': 'Θ',
        r'\\Lambda': 'Λ',
        r'\\Sigma': 'Σ',
        r'\\Omega': 'Ω',
        r'\\left\(': '(',
        r'\\right\)': ')',
        r'\\left\[': '[',
        r'\\right\]': ']',
        r'\\mathrm\{([^{}]*)\}': r'\1',
        r'\\mathbf\{([^{}]*)\}': r'<b>\1</b>',
        r'\\mathit\{([^{}]*)\}': r'<i>\1</i>',
        r'\\log': 'log',
        r'\\sin': 'sin',
        r'\\cos': 'cos',
        r'\\tan': 'tan',
        r'\\exp': 'exp',
        r'\\max': 'max',
        r'\\min': 'min',
    }
    
    for latex_sym, html_sym in symbols.items():
        if '{}' in latex_sym:
            html = re.sub(latex_sym, html_sym, html)
        else:
            html = html.replace(latex_sym, html_sym)
    
    # 8. 清理剩余的 LaTeX 命令
    html = re.sub(r'\\[a-zA-Z]+\s*', '', html)
    html = re.sub(r'[{}]', '', html)
    
    # 9. 包装为公式样式
    return f'<p style="font-size: {font_size}px; color: {color}; line-height: 1.5; text-align: center; padding: 8px 0;">{html}</p>'


def text_to_html(text: str, font_size: int = 18, color: str = "#333333", line_height: float = 1.8) -> str:
    """将纯文本转为 PPTist 需要的 HTML 格式。"""
    if not text:
        return ""
    # 按换行符分段
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    parts = []
    for p in paragraphs:
        parts.append(f'<p style="font-size: {font_size}px; color: {color}; line-height: {line_height};">{p}</p>')
    return ''.join(parts)


def bullets_to_html(items: list, font_size: int = 18, color: str = "#333333") -> str:
    """将列表转为带项目符号的 HTML。"""
    parts = []
    for item in items:
        parts.append(f'<p style="font-size: {font_size}px; color: {color}; line-height: 1.8;">• {item}</p>')
    return ''.join(parts)


def make_text_element(el_id, left, top, width, height, content_html, font_size=18, color="#333333", text_type=None):
    """创建一个 PPTist text 元素。"""
    el = {
        "type": "text",
        "id": el_id,
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "rotate": 0,
        "content": content_html,
        "defaultFontName": "",
        "defaultColor": color,
        "lineHeight": 1.5,
        "paragraphSpace": 5
    }
    if text_type:
        el["textType"] = text_type
    return el


def make_shape_element(el_id, left, top, width, height, fill, path=None):
    """创建一个 PPTist shape 元素（用作装饰线或背景框）。"""
    if path is None:
        path = "M 0 0 L 200 0 L 200 200 L 0 200 Z"
    return {
        "type": "shape",
        "id": el_id,
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "viewBox": [200, 200],
        "path": path,
        "fill": fill,
        "fixedRatio": False,
        "rotate": 0
    }


def make_image_element(el_id, image_path, left, top, width, height, fixed_ratio=True):
    """创建一个 PPTist image 元素（Base64 内嵌）。"""
    src = image_to_base64(image_path)
    return {
        "type": "image",
        "id": el_id,
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "fixedRatio": fixed_ratio,
        "src": src,
        "rotate": 0
    }


def make_line_element(el_id, left, top, width, color="#5b9bd5"):
    """创建一条装饰线。"""
    return {
        "type": "line",
        "id": el_id,
        "left": left,
        "top": top,
        "width": width,
        "start": [0, 0],
        "end": [width, 0],
        "points": ["", ""],
        "color": color,
        "style": "solid",
        "rotate": 0
    }


def make_table_element(el_id, left, top, width, height, table_data, col_widths=None, theme_color="#5b9bd5"):
    """创建 PPTist table 元素。"""
    if not table_data or not table_data.get("headers"):
        return None
    
    headers = table_data["headers"]
    rows = table_data.get("rows", [])
    all_rows = [headers] + rows
    highlight_row = table_data.get("highlight_row")
    
    cells = []
    for r_idx, row_data in enumerate(all_rows):
        row_cells = []
        for c_idx, cell_text in enumerate(row_data):
            is_header = (r_idx == 0)
            is_highlight = (highlight_row is not None and r_idx == highlight_row + 1)
            
            style = {
                "fontsize": "14px",
                "align": "center" if is_header else "left",
                "bold": is_header or is_highlight
            }
            
            if is_header:
                style["backcolor"] = theme_color
                style["color"] = "#ffffff"
            elif is_highlight:
                style["backcolor"] = "#e8f4fd"
            
            row_cells.append({
                "id": nanoid(6),
                "colspan": 1,
                "rowspan": 1,
                "text": str(cell_text),
                "style": style
            })
        cells.append(row_cells)
    
    n_cols = len(headers)
    col_widths = col_widths or [1.0 / n_cols] * n_cols
    
    return {
        "type": "table",
        "id": el_id,
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "rotate": 0,
        "outline": {"style": "solid", "width": 1, "color": "#cccccc"},
        "colWidths": col_widths,
        "cellMinHeight": 35,
        "data": cells
    }


def make_slide(slide_id, slide_type, elements, background=None):
    """创建一个 PPTist slide。"""
    slide = {
        "id": slide_id,
        "type": slide_type,
        "elements": elements,
        "background": background or {"type": "solid", "color": "#ffffff"}
    }
    return slide


# ============================================================
# 页面生成器
# ============================================================

def make_cover_slide(paper_info):
    """生成封面页。"""
    title = paper_info.get("title", "论文标题")
    authors = ", ".join(paper_info.get("authors", []))
    abstract = paper_info.get("abstract", "")[:100] + "..." if paper_info.get("abstract") else ""
    year = paper_info.get("year") or ""
    venue = paper_info.get("venue") or ""
    
    # 截取标题（如果太长分两行）
    display_title = title
    if len(title) > 40:
        # 尝试在空格处断开
        mid = title.rfind(" ", 0, 40)
        if mid > 0:
            display_title = title[:mid] + "\n" + title[mid+1:]
    
    elements = [
        # 标题
        make_text_element(
            nanoid(6), 100, 150, 800, 120,
            text_to_html(display_title, font_size=36, color="#333333"),
            text_type="title"
        ),
        # 装饰线
        make_line_element(nanoid(6), 350, 290, 300, "#5b9bd5"),
        # 作者
        make_text_element(
            nanoid(6), 200, 320, 600, 50,
            text_to_html(authors if authors else "作者信息", font_size=20, color="#666666")
        ),
    ]
    
    # 副信息（年份 + venue）
    subtitle_parts = []
    if year:
        subtitle_parts.append(str(year))
    if venue:
        subtitle_parts.append(venue)
    subtitle = " | ".join(subtitle_parts) if subtitle_parts else "学术汇报"
    
    elements.append(make_text_element(
        nanoid(6), 200, 390, 600, 40,
        text_to_html(subtitle, font_size=16, color="#999999")
    ))
    
    return make_slide("slide_cover", "cover", elements)


def make_problem_slide(problem):
    """生成研究背景与问题页。"""
    desc = problem.get("description", "")
    motivation = problem.get("motivation", "")
    limitations = problem.get("limitations_of_existing", [])
    
    elements = [
        # 标题
        make_text_element(
            nanoid(6), 60, 30, 880, 60,
            text_to_html("研究背景与动机", font_size=32, color="#333333"),
            text_type="title"
        ),
        make_line_element(nanoid(6), 60, 95, 120, "#5b9bd5"),
    ]
    
    y = 130
    
    # 问题描述
    if desc:
        elements.append(make_text_element(
            nanoid(6), 60, y, 880, 150,
            text_to_html(desc, font_size=18, color="#333333", line_height=1.7)
        ))
        y += 160
    
    # 现有不足（要点列表）
    if limitations:
        elements.append(make_text_element(
            nanoid(6), 60, y, 880, 40,
            text_to_html("现有方法的不足", font_size=22, color="#5b9bd5", line_height=1.5)
        ))
        y += 50
        
        elements.append(make_text_element(
            nanoid(6), 60, y, 880, 250,
            bullets_to_html(limitations, font_size=17, color="#444444")
        ))
    
    return make_slide("slide_problem", "content", elements)


def make_method_overview_slide(method, image_path=None):
    """生成方法概述页。"""
    name = method.get("name", "本文方法")
    overview = method.get("overview", "")
    contributions = method.get("key_contributions", [])
    
    elements = [
        make_text_element(
            nanoid(6), 60, 30, 880, 60,
            text_to_html(f"方法概述：{name}", font_size=32, color="#333333"),
            text_type="title"
        ),
        make_line_element(nanoid(6), 60, 95, 200, "#5b9bd5"),
    ]
    
    # 如果有架构图，放在右侧，文字在左侧
    if image_path and Path(image_path).exists():
        # 文字区域缩小，放在左侧
        y = 130
        if overview:
            elements.append(make_text_element(
                nanoid(6), 60, y, 500, 200,
                text_to_html(overview, font_size=15, color="#333333", line_height=1.6)
            ))
            y += 210
        
        if contributions:
            elements.append(make_text_element(
                nanoid(6), 60, y, 500, 35,
                text_to_html("主要贡献", font_size=18, color="#5b9bd5", line_height=1.5)
            ))
            y += 40
            
            contribution_bullets = []
            for i, c in enumerate(contributions, 1):
                contribution_bullets.append(f"{i}. {c}")
            
            elements.append(make_text_element(
                nanoid(6), 60, y, 500, 200,
                bullets_to_html(contribution_bullets, font_size=14, color="#444444")
            ))
        
        # 架构图放在右侧
        elements.append(make_image_element(
            nanoid(6), image_path, 560, 120, 400, 400
        ))
    else:
        # 无图片时的原始布局
        y = 130
        if overview:
            elements.append(make_text_element(
                nanoid(6), 60, y, 880, 150,
                text_to_html(overview, font_size=17, color="#333333", line_height=1.7)
            ))
            y += 160
        
        if contributions:
            elements.append(make_text_element(
                nanoid(6), 60, y, 880, 40,
                text_to_html("主要贡献", font_size=22, color="#5b9bd5", line_height=1.5)
            ))
            y += 50
            
            contribution_bullets = []
            for i, c in enumerate(contributions, 1):
                contribution_bullets.append(f"{i}. {c}")
            
            elements.append(make_text_element(
                nanoid(6), 60, y, 880, 250,
                bullets_to_html(contribution_bullets, font_size=17, color="#444444")
            ))
    
    return make_slide("slide_method_overview", "content", elements)


def make_module_slide(modules, page_index=1, image_path=None):
    """生成模块详情页（每页展示 2 个模块）。"""
    start_idx = (page_index - 1) * 2
    page_modules = modules[start_idx:start_idx + 2]
    
    if not page_modules:
        return None
    
    elements = [
        make_text_element(
            nanoid(6), 60, 30, 880, 60,
            text_to_html(f"核心模块（{page_index}）", font_size=32, color="#333333"),
            text_type="title"
        ),
        make_line_element(nanoid(6), 60, 95, 200, "#5b9bd5"),
    ]
    
    # 如果有模块图，放在右侧
    has_image = image_path and Path(image_path).exists()
    text_width = 500 if has_image else 880
    image_left = 560 if has_image else None
    
    y = 130
    
    for mod in page_modules:
        mod_name = mod.get("name", "")
        mod_desc = mod.get("description", "")
        formulas = mod.get("formulas", [])
        
        # 模块名称
        elements.append(make_text_element(
            nanoid(6), 60, y, text_width, 35,
            text_to_html(f"▎{mod_name}", font_size=20, color="#5b9bd5", line_height=1.5)
        ))
        y += 38
        
        # 模块描述
        if mod_desc:
            elements.append(make_text_element(
                nanoid(6), 60, y, text_width, 70,
                text_to_html(mod_desc, font_size=14, color="#444444", line_height=1.6)
            ))
            y += 75
        
        # 公式（用 HTML 富文本展示，支持分式、上下标等）
        for formula in formulas:
            latex = formula.get("latex", "")
            desc = formula.get("description", "")
            if latex:
                # 用带背景色的文本框展示公式
                elements.append(make_shape_element(
                    nanoid(6), 60, y, text_width, 55, "#f5f8ff"
                ))
                # 公式转为 HTML 富文本
                formula_html = latex_to_html(latex, font_size=18, color="#333333")
                if desc:
                    formula_html += f'<p style="font-size: 12px; color: #666666; text-align: center; padding: 2px 0; margin-top: -5px;">{desc}</p>'
                elements.append(make_text_element(
                    nanoid(6), 70, y + 5, text_width - 20, 50,
                    formula_html
                ))
                y += 65
        
        y += 10  # 模块间距
    
    # 图片放在右侧
    if has_image:
        elements.append(make_image_element(
            nanoid(6), image_path, image_left, 120, 400, 400
        ))
    
    return make_slide(f"slide_module_{page_index}", "content", elements)


def make_experiment_slide(experiments, table_image_path=None):
    """生成实验结果页。"""
    datasets = experiments.get("datasets", [])
    baselines = experiments.get("baselines", [])
    main_results = experiments.get("main_results", [])
    
    elements = []
    
    # 1. 背景/装饰元素（底层，防止遮挡文字）
    elements.append(make_line_element(nanoid(6), 60, 95, 120, "#5b9bd5"))
    
    # 2. 标题（上层）
    elements.append(make_text_element(
        nanoid(6), 60, 30, 880, 60,
        text_to_html("实验结果", font_size=32, color="#333333"),
        text_type="title"
    ))
    
    y = 130
    
    # 3. 优先展示表格截图（整页截图）
    if table_image_path and Path(table_image_path).exists():
        elements.append(make_image_element(
            nanoid(6), table_image_path, 20, y, 960, 380
        ))
        # 截图很高，文字放到下面
        y += 390
    else:
        # 备用：如果没有截图，尝试生成表格
        if main_results:
            result = main_results[0]
            table_data = result.get("table")
            if table_data:
                table_el = make_table_element(nanoid(6), 60, y, 880, 300, table_data, theme_color="#5b9bd5")
                if table_el:
                    elements.append(table_el)
                y += 310

    # 4. 数据集和基线说明（放在最下方，避免与表格重叠）
    if datasets:
        dataset_names = [d.get("name", "") for d in datasets if d.get("name")]
        elements.append(make_text_element(
            nanoid(6), 60, y, 880, 35,
            text_to_html(f"数据集：{', '.join(dataset_names)}", font_size=17, color="#444444")
        ))
        y += 40
    
    if baselines:
        elements.append(make_text_element(
            nanoid(6), 60, y, 880, 30,
            text_to_html(f"对比基线：{', '.join(baselines)}", font_size=16, color="#666666")
        ))
    
    return make_slide("slide_experiments", "content", elements)


def make_ablation_slide(experiments, table_image_path=None):
    """生成消融实验页。"""
    elements = []
    
    # 1. 背景/装饰元素（底层）
    elements.append(make_line_element(nanoid(6), 60, 95, 120, "#5b9bd5"))
    
    # 2. 标题（上层）
    elements.append(make_text_element(
        nanoid(6), 60, 30, 880, 60,
        text_to_html("消融实验", font_size=32, color="#333333"),
        text_type="title"
    ))
    
    y = 130
    
    # 3. 优先展示表格截图
    if table_image_path and Path(table_image_path).exists():
        elements.append(make_image_element(
            nanoid(6), table_image_path, 20, y, 960, 380
        ))
        y += 390
    else:
        # 备用
        ablation = experiments.get("ablation_study")
        if ablation:
            table_data = ablation.get("table")
            if table_data:
                table_el = make_table_element(nanoid(6), 60, y, 880, 300, table_data, theme_color="#5b9bd5")
                if table_el: elements.append(table_el)

    return make_slide("slide_ablation", "content", elements)

    # 备用：如果没有图片，尝试生成文字表格
    ablation = experiments.get("ablation_study")
    if ablation:
        table_data = ablation.get("table")
        if table_data:
            table_el = make_table_element(nanoid(6), 60, 130, 880, 350, table_data, theme_color="#5b9bd5")
            if table_el:
                elements.append(table_el)
    
    return make_slide("slide_ablation", "content", elements)


def make_conclusion_slide(conclusion):
    """生成结论页。"""
    summary = conclusion.get("summary", "")
    future_work = conclusion.get("future_work", "")
    
    elements = [
        make_text_element(
            nanoid(6), 60, 30, 880, 60,
            text_to_html("结论与展望", font_size=32, color="#333333"),
            text_type="title"
        ),
        make_line_element(nanoid(6), 60, 95, 120, "#5b9bd5"),
    ]
    
    y = 130
    
    if summary:
        elements.append(make_text_element(
            nanoid(6), 60, y, 880, 40,
            text_to_html("结论", font_size=22, color="#5b9bd5")
        ))
        y += 50
        
        elements.append(make_text_element(
            nanoid(6), 60, y, 880, 200,
            text_to_html(summary, font_size=17, color="#444444", line_height=1.7)
        ))
        y += 210
    
    if future_work:
        elements.append(make_text_element(
            nanoid(6), 60, y, 880, 35,
            text_to_html("未来工作", font_size=22, color="#5b9bd5")
        ))
        y += 45
        
        elements.append(make_text_element(
            nanoid(6), 60, y, 880, 120,
            text_to_html(future_work, font_size=17, color="#444444", line_height=1.7)
        ))
    
    return make_slide("slide_conclusion", "content", elements)


def make_end_slide():
    """生成结束页。"""
    elements = [
        make_text_element(
            nanoid(6), 200, 200, 600, 100,
            text_to_html("感谢观看", font_size=48, color="#5b9bd5"),
            text_type="title"
        ),
        make_text_element(
            nanoid(6), 200, 330, 600, 50,
            text_to_html("Q & A", font_size=24, color="#999999")
        )
    ]
    return make_slide("slide_end", "end", elements)


# ============================================================
# 主函数
# ============================================================

def intermediate_to_pptist(intermediate_data, output_path=None, images_dir=None):
    """将中间格式 JSON 转换为 PPTist JSON。
    
    Args:
        intermediate_data: 中间格式 JSON 数据
        output_path: 输出路径
        images_dir: 论文原图目录（用于嵌入图片到 PPT）
    """
    
    paper_info = intermediate_data.get("paper_info", {})
    problem = intermediate_data.get("problem", {})
    method = intermediate_data.get("method", {})
    experiments = intermediate_data.get("experiments", {})
    conclusion = intermediate_data.get("conclusion", {})
    modules = method.get("modules", [])
    
    # 图片路径手动映射（Phase 1 手动指定，后续改为自动定位）
    extracted_images = {}
    # 映射表格截图（精准裁剪版）
    if Path("output_images/table_main_clean.png").exists():
        extracted_images["table_main"] = "output_images/table_main_clean.png"
    if Path("output_images/table_ablation_clean.png").exists():
        extracted_images["table_ablation"] = "output_images/table_ablation_clean.png"

    if images_dir and Path(images_dir).exists():
        img_path = Path(images_dir)
        # 根据文件名手动指定用途
        for img_file in img_path.glob("*.png"):
            name = img_file.stem
            if "page3" in name:
                extracted_images["architecture"] = str(img_file)  # Transformer 架构图
            elif "page4_img1" in name:
                extracted_images["scaled_attention"] = str(img_file)  # Scaled Dot-Product Attention
            elif "page4_img2" in name:
                extracted_images["multi_head"] = str(img_file)  # Multi-Head Attention
    
    slides = []
    
    # 1. 封面
    slides.append(make_cover_slide(paper_info))
    
    # 2. 研究背景与问题
    slides.append(make_problem_slide(problem))
    
    # 3. 方法概述（加入架构图）
    arch_img = extracted_images.get("architecture")
    slides.append(make_method_overview_slide(method, image_path=arch_img))
    
    # 4-5. 核心模块（每页 2 个模块，加入模块图）
    module_pages_needed = (len(modules) + 1) // 2
    for i in range(1, min(module_pages_needed + 1, 3)):  # 最多 3 页模块
        # 手动指定每页的图片
        page_images = {}
        if i == 1:
            # 第 1 页模块：Encoder + Decoder + Attention → 放 Scaled Attention 图
            page_images["module"] = extracted_images.get("scaled_attention")
        elif i == 2:
            # 第 2 页模块：Multi-Head + FFN + PE → 放 Multi-Head 图
            page_images["module"] = extracted_images.get("multi_head")
        
        module_slide = make_module_slide(modules, page_index=i, image_path=page_images.get("module"))
        if module_slide:
            slides.append(module_slide)
    
    # 6. 实验结果
    slides.append(make_experiment_slide(experiments, extracted_images.get("table_main")))
    
    # 7. 消融实验（如果有）
    ablation_slide = make_ablation_slide(experiments, extracted_images.get("table_ablation"))
    if ablation_slide:
        slides.append(ablation_slide)
    
    # 8. 结论与展望
    slides.append(make_conclusion_slide(conclusion))
    
    # 9. 结束页
    slides.append(make_end_slide())
    
    # 构建完整 PPTist JSON
    pptist_json = {
        "title": paper_info.get("title", "学术汇报"),
        "width": CANVAS_WIDTH,
        "height": CANVAS_HEIGHT,
        "theme": THEME,
        "slides": slides
    }
    
    # 保存
    if output_path is None:
        output_path = "output_images/pptist_output.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pptist_json, f, ensure_ascii=False, indent=2)
    
    print(f"✅ PPTist JSON 已生成: {output_path}")
    print(f"📊 共 {len(slides)} 页")
    
    for i, slide in enumerate(slides):
        slide_type = slide.get("type", "content")
        title = ""
        # Find first text element (since decorative lines are now at index 0)
        for el in slide["elements"]:
            if el.get("type") == "text":
                content = el.get("content", "")
                import re
                text_match = re.search(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
                if text_match:
                    title = re.sub(r'<[^>]+>', '', text_match.group(1))[:30]
                break
        print(f"   Page {i+1} [{slide_type}]: {title}")
    
    return pptist_json


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "output_images/intermediate_format.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    images_dir = sys.argv[3] if len(sys.argv) > 3 else "output_images/extracted_images"
    
    print(f"📖 读取中间格式: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        intermediate_data = json.load(f)
    
    print(f"🖼️  图片目录: {images_dir}")
    
    intermediate_to_pptist(intermediate_data, output_path, images_dir)
