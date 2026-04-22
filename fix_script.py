#!/usr/bin/env python3
"""
修复脚本：
1. 将实验结果页和消融实验页的表格改为图片（page_008.png 和 page_009.png）。
2. 修复 Z-index 问题（装饰线/背景块放在最前面，防止遮挡文字）。
3. 调整布局，防止文字和表格重叠。
"""

import re
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
TARGET_FILE = SCRIPT_DIR / "src" / "intermediate_to_pptist.py"

def fix_file():
    if not TARGET_FILE.exists():
        print(f"❌ 文件不存在: {TARGET_FILE}")
        return

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. 修改 make_experiment_slide
    # 匹配函数定义到 return 语句
    pattern_exp = r'def make_experiment_slide\(experiments, table_image_path=None\):.*?return make_slide\("slide_experiments", "content", elements\)'
    
    new_func_exp = '''def make_experiment_slide(experiments, table_image_path=None):
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
    
    # 3. 优先展示表格截图
    if table_image_path and Path(table_image_path).exists():
        elements.append(make_image_element(
            nanoid(6), table_image_path, 20, y, 960, 380
        ))
        # 截图很高，文字放到下面
        y += 390
    else:
        # 备用：生成表格
        if main_results:
            result = main_results[0]
            table_data = result.get("table")
            if table_data:
                table_el = make_table_element(nanoid(6), 60, y, 880, 300, table_data, theme_color="#5b9bd5")
                if table_el: elements.append(table_el)

    # 4. 数据集和基线说明（放在最下方）
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

    if re.search(pattern_exp, content, re.DOTALL):
        content = re.sub(pattern_exp, new_func_exp, content, flags=re.DOTALL)
        print("✅ 已修复 make_experiment_slide")
    else:
        print("⚠️ 未找到 make_experiment_slide，可能已经修改过")

    # 2. 修改 make_ablation_slide
    pattern_abl = r'def make_ablation_slide\(experiments, table_image_path=None\):.*?return make_slide\("slide_ablation", "content", elements\)'
    
    new_func_abl = '''def make_ablation_slide(experiments, table_image_path=None):
    """生成消融实验页。"""
    ablation = experiments.get("ablation_study")
    
    elements = []
    
    # 1. 背景/装饰元素
    elements.append(make_line_element(nanoid(6), 60, 95, 120, "#5b9bd5"))
    
    # 2. 标题
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
        # 备用：生成表格
        if ablation:
            table_data = ablation.get("table")
            if table_data:
                table_el = make_table_element(nanoid(6), 60, y, 880, 300, table_data, theme_color="#5b9bd5")
                if table_el: elements.append(table_el)
    
    return make_slide("slide_ablation", "content", elements)'''

    if re.search(pattern_abl, content, re.DOTALL):
        content = re.sub(pattern_abl, new_func_abl, content, flags=re.DOTALL)
        print("✅ 已修复 make_ablation_slide")
    else:
        print("⚠️ 未找到 make_ablation_slide")

    # 3. 修改主函数中的调用
    # 查找并替换调用处
    old_call_exp = r'slides.append\(make_experiment_slide\(experiments\)\)'
    new_call_exp = r'slides.append(make_experiment_slide(experiments, extracted_images.get("table_main")))'
    
    if re.search(old_call_exp, content):
        content = re.sub(old_call_exp, new_call_exp, content)
        print("✅ 已更新实验结果页调用")
    
    old_call_abl = r'ablation_slide = make_ablation_slide\(experiments\)'
    new_call_abl = r'ablation_slide = make_ablation_slide(experiments, extracted_images.get("table_ablation"))'
    
    if re.search(old_call_abl, content):
        content = re.sub(old_call_abl, new_call_abl, content)
        print("✅ 已更新消融实验页调用")

    # 4. 添加图片路径映射
    # 在 extracted_images = {} 之后添加
    # 注意：这里假设代码结构，可能需要微调
    # 查找 extracted_images = {} 并在其后插入逻辑
    mapping_insert = '''extracted_images = {}
    # 映射表格截图
    if Path("output_images/page_008.png").exists():
        extracted_images["table_main"] = "output_images/page_008.png"
    if Path("output_images/page_009.png").exists():
        extracted_images["table_ablation"] = "output_images/page_009.png"
'''
    # 替换简单的 extracted_images = {}
    if 'extracted_images = {}' in content:
        content = content.replace('extracted_images = {}', mapping_insert, 1)
        print("✅ 已添加表格图片路径映射")

    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("\n🎉 修复完成！")

if __name__ == "__main__":
    fix_file()
