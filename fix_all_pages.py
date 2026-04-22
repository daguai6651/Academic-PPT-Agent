#!/usr/bin/env python3
"""
全面修复脚本：
1. 表格替换为截图 (Page 8, 9)。
2. 修复所有页面的 Z-index 问题（确保装饰线在文字下方）。
3. 调整实验页和消融页的布局（文字下沉）。
"""

import re
from pathlib import Path

TARGET = Path("src/intermediate_to_pptist.py")
content = TARGET.read_text(encoding="utf-8")

# ==========================================
# 1. 修复 make_experiment_slide
# ==========================================
new_exp = '''def make_experiment_slide(experiments, table_image_path=None):
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
    
    return make_slide("slide_experiments", "content", elements)'''

# 替换实验页函数
pattern = r'def make_experiment_slide\(.*?return make_slide\("slide_experiments", "content", elements\)'
if re.search(pattern, content, re.DOTALL):
    content = re.sub(pattern, new_exp, content, flags=re.DOTALL)
    print("✅ 已修复 make_experiment_slide")

# ==========================================
# 2. 修复 make_ablation_slide
# ==========================================
new_abl = '''def make_ablation_slide(experiments, table_image_path=None):
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

    return make_slide("slide_ablation", "content", elements)'''

# 替换消融页函数
pattern = r'def make_ablation_slide\(.*?return make_slide\("slide_ablation", "content", elements\)'
if re.search(pattern, content, re.DOTALL):
    content = re.sub(pattern, new_abl, content, flags=re.DOTALL)
    print("✅ 已修复 make_ablation_slide")

# ==========================================
# 3. 修复主函数中的调用逻辑
# ==========================================
# 确保传入了图片路径
old_call_exp = r'make_experiment_slide\(experiments\)'
if re.search(old_call_exp, content):
    content = re.sub(old_call_exp, 'make_experiment_slide(experiments, extracted_images.get("table_main"))', content)
    print("✅ 已更新实验页调用")

old_call_abl = r'make_ablation_slide\(experiments\)'
if re.search(old_call_abl, content):
    content = re.sub(old_call_abl, 'make_ablation_slide(experiments, extracted_images.get("table_ablation"))', content)
    print("✅ 已更新消融页调用")

# 添加图片路径映射
if 'extracted_images["table_main"]' not in content:
    mapping = '''    if Path("output_images/page_008.png").exists():
        extracted_images["table_main"] = "output_images/page_008.png"
    if Path("output_images/page_009.png").exists():
        extracted_images["table_ablation"] = "output_images/page_009.png"
'''
    # 插入到 extracted_images = {} 之后
    content = content.replace('extracted_images = {}', 'extracted_images = {}\n' + mapping)
    print("✅ 已添加图片路径映射")

TARGET.write_text(content, encoding="utf-8")
print("\n🎉 全部修复完成！")
