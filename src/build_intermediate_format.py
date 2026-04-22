#!/usr/bin/env python3
"""
论文解析 Agent — Step 2：逐页结果 → 中间格式 JSON
按章节分组后，调用 5 个 LLM Prompt 提取结构化信息，合并为最终中间格式 JSON。
"""

import os
import sys
import json
from pathlib import Path
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Optional


# ============================================================
# 配置
# ============================================================
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
QWEN_MODEL = "qwen-plus"  # 纯文本提取用 qwen-plus 性价比更高
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


# ============================================================
# Pydantic Schema（中间格式）
# ============================================================

class FormulaInfo(BaseModel):
    id: str = Field(..., description="公式编号，如 eq1, eq2")
    latex: str = Field(..., description="LaTeX 公式代码")
    description: str = Field(..., description="公式含义说明")
    variables: dict = Field(default_factory=dict, description="变量含义，如 {'Q': 'Query 向量'}")


class ModuleInfo(BaseModel):
    name: str = Field(..., description="模块名称")
    description: str = Field(..., description="模块功能说明（3-5句话）")
    formulas: list[FormulaInfo] = Field(default_factory=list, description="该模块涉及的公式")


class TableInfo(BaseModel):
    caption: str = Field(..., description="表格标题")
    headers: list[str] = Field(default_factory=list, description="表头")
    rows: list[list[str]] = Field(default_factory=list, description="数据行")
    highlight_row: Optional[int] = Field(None, description="需要高亮的行索引（0-based），通常是本文方法）")


class ExperimentResult(BaseModel):
    name: str = Field(..., description="实验名称")
    description: str = Field(default="", description="实验说明")
    table: Optional[TableInfo] = Field(None, description="实验结果表格")


class IntermediateFormat(BaseModel):
    """论文中间格式 JSON"""
    paper_info: dict = Field(default_factory=dict, description="论文基本信息")
    problem: dict = Field(default_factory=dict, description="研究问题")
    method: dict = Field(default_factory=dict, description="方法")
    experiments: dict = Field(default_factory=dict, description="实验")
    conclusion: dict = Field(default_factory=dict, description="结论")


# ============================================================
# 数据聚合
# ============================================================

def group_by_section(per_page_results: list[dict]) -> dict[str, list[dict]]:
    """按 page_type 分组。"""
    grouped = {}
    for page in per_page_results:
        page_type = page.get("page_type", "other")
        if page_type not in grouped:
            grouped[page_type] = []
        grouped[page_type].append(page)
    return grouped


def merge_group(pages: list[dict]) -> str:
    """将一个章节组内的页面内容拼接为文本。"""
    parts = []
    for page in pages:
        section = page.get("section_title", "")
        paragraphs = page.get("content_paragraphs", [])
        formulas = page.get("formulas", [])
        tables = page.get("tables", [])
        key_terms = page.get("key_terms", [])
        
        if section:
            parts.append(f"## {section}")
        
        for p in paragraphs:
            parts.append(p)
        
        if formulas:
            parts.append("### 公式")
            for f in formulas:
                parts.append(f"  - {f.get('latex', '')}  ({f.get('description', '')})")
        
        if tables:
            parts.append("### 表格")
            for t in tables:
                parts.append(f"  - {t.get('caption', '')}")
                if t.get("markdown"):
                    parts.append(f"    {t['markdown'][:200]}")
        
        if key_terms:
            parts.append(f"### 关键术语: {', '.join(key_terms)}")
        
        parts.append("---")
    
    return "\n\n".join(parts)


# ============================================================
# 5 个结构化 Prompt
# ============================================================

PROMPT_PAPER_INFO = """你是一个学术论文解析助手。请从以下论文的标题页和摘要页信息中，提取论文基本信息。

## 输入内容
{text}

## 提取要求
1. title: 论文标题（中英文都要，如果有）
2. authors: 作者列表
3. affiliations: 作者机构（如果有）
4. venue: 发表的会议或期刊名称（如果有提到）
5. year: 发表年份（从上下文推断，不确定则为 null）
6. abstract: 摘要内容（完整保留，不要缩写）
7. keywords: 关键词（如果有）

## 输出格式（严格 JSON）
{
  "title": "...",
  "title_en": "..." or null,
  "authors": ["...", "..."],
  "affiliations": ["..."] or [],
  "venue": "..." or null,
  "year": 2026 or null,
  "abstract": "...",
  "keywords": ["..."] or []
}
"""

PROMPT_PROBLEM = """你是一个计算机领域的学术专家。请阅读以下论文的 Introduction 部分，提取研究问题和动机。

## 输入内容
{text}

## 提取要求
1. description: 本文要解决的核心问题（3-5 句话，用自己的话总结）
2. motivation: 研究动机（为什么这个问题重要，2-3 句话）
3. limitations_of_existing: 现有方法的不足（至少 2 条，每条 1-2 句话）

## 输出格式（严格 JSON）
{
  "description": "...",
  "motivation": "...",
  "limitations_of_existing": ["...", "..."]
}
"""

PROMPT_METHOD = """你是一个计算机领域的学术专家。请阅读以下论文的 Method 部分，提取方法的结构化信息。

## 输入内容
{text}

## 提取要求
1. name: 方法名称（如果有的话，如 "Transformer"）
2. overview: 方法整体概述（5-8 句话，用自己的话总结核心思想）
3. key_contributions: 论文的主要贡献点（通常 2-4 条，每条 1-2 句话）
4. modules: 各个模块/组件的说明（名称 + 描述 + 相关公式）
   - 注意：请将公式归类到对应的模块中
   - 每个公式需要包含变量含义说明
5. architecture_description: 整体架构的文字描述（用于后续生成架构图，3-5 句话）

## 输出格式（严格 JSON）
{
  "name": "...",
  "overview": "...",
  "key_contributions": ["...", "..."],
  "modules": [
    {
      "name": "模块名",
      "description": "模块功能说明",
      "formulas": [
        {
          "id": "eq1",
          "latex": "LaTeX 公式",
          "description": "公式含义",
          "variables": {"符号": "含义"}
        }
      ]
    }
  ],
  "architecture_description": "..."
}
"""

PROMPT_EXPERIMENTS = """你是一个计算机领域的学术专家。请阅读以下论文的 Experiment 部分，提取实验的结构化信息。

## 输入内容
{text}

## 提取要求
1. datasets: 使用的数据集（名称 + 简要说明）
2. baselines: 对比的基线方法（列表）
3. metrics: 评估指标（名称 + 说明，如 BLEU、Accuracy）
4. main_results: 主要实验结果
   - 包含实验名称、说明、结果表格
   - 表格要正确提取 headers 和 rows
   - highlight_row 标记本文方法的行索引（0-based），用于后续 PPT 高亮
5. ablation_study: 消融实验（如果有）
   - 包含消融实验说明和结果表格

## 输出格式（严格 JSON）
{
  "datasets": [
    {"name": "...", "description": "...", "size": "..." or null}
  ],
  "baselines": ["...", "..."],
  "metrics": [
    {"name": "...", "description": "..."}
  ],
  "main_results": [
    {
      "name": "实验名称",
      "description": "实验说明",
      "table": {
        "caption": "表格标题",
        "headers": ["列1", "列2"],
        "rows": [["值1", "值2"]],
        "highlight_row": 0
      }
    }
  ],
  "ablation_study": {
    "description": "消融实验说明",
    "table": {
      "caption": "消融实验标题",
      "headers": ["变体", "BLEU", "说明"],
      "rows": [["Full Model", "28.4", "完整模型"]],
      "highlight_row": 0
    }
  } or null
}
"""

PROMPT_CONCLUSION = """你是一个计算机领域的学术专家。请阅读以下论文的 Conclusion 部分，提取结论和未来工作方向。

## 输入内容
{text}

## 提取要求
1. summary: 论文结论（3-5 句话，总结主要贡献和发现）
2. future_work: 未来工作方向（2-3 句话）

## 输出格式（严格 JSON）
{
  "summary": "...",
  "future_work": "..."
}
"""


# ============================================================
# LLM 调用
# ============================================================

def call_llm(client: OpenAI, prompt: str, text: str, max_retries: int = 2) -> dict:
    """调用 LLM 提取结构化信息，带重试。"""
    messages = [
        {
            "role": "system",
            "content": "你是一个学术论文解析专家。请严格按要求的 JSON 格式输出，不要输出其他内容。"
        },
        {
            "role": "user",
            "content": prompt.replace("{text}", text)
        }
    ]
    
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=QWEN_MODEL,
                messages=messages,
                temperature=0.1,
                max_tokens=4000,
            )
            
            content = response.choices[0].message.content
            
            # 解析 JSON
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].strip()
            else:
                json_str = content.strip()
            
            result = json.loads(json_str)
            return result
            
        except json.JSONDecodeError as e:
            if attempt < max_retries:
                print(f"    ⚠️ JSON 解析失败，重试 ({attempt + 1}/{max_retries}): {e}")
                messages.append({
                    "role": "assistant",
                    "content": content
                })
                messages.append({
                    "role": "user",
                    "content": "JSON 格式不正确，请重新输出合法的 JSON。"
                })
            else:
                print(f"    ❌ JSON 解析失败，已达最大重试次数: {e}")
                return {"_raw": content}
        
        except Exception as e:
            if attempt < max_retries:
                print(f"    ⚠️ 调用失败，重试 ({attempt + 1}/{max_retries}): {e}")
            else:
                print(f"    ❌ 调用失败，已达最大重试次数: {e}")
                return {"_error": str(e)}


# ============================================================
# 主函数
# ============================================================

def build_intermediate_format(per_page_results: list[dict], output_path: str = None):
    """从逐页结果构建中间格式 JSON。"""
    
    if not DASHSCOPE_API_KEY:
        print("❌ 未设置 DASHSCOPE_API_KEY 环境变量")
        sys.exit(1)
    
    client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=BASE_URL)
    
    # 1. 按章节分组
    print("📂 Step 1: 按章节分组...")
    grouped = group_by_section(per_page_results)
    for section, pages in grouped.items():
        print(f"   {section}: {len(pages)} 页")
    
    # 2. 拼接各章节文本
    print("\n📝 Step 2: 拼接章节文本...")
    title_pages = grouped.get("title_page", []) + grouped.get("abstract", [])
    intro_pages = grouped.get("introduction", [])
    method_pages = grouped.get("method", [])
    experiment_pages = grouped.get("experiment", [])
    conclusion_pages = grouped.get("conclusion", [])
    
    title_text = merge_group(title_pages)
    intro_text = merge_group(intro_pages)
    method_text = merge_group(method_pages)
    experiment_text = merge_group(experiment_pages)
    conclusion_text = merge_group(conclusion_pages)
    
    # 3. 调用 5 个 Prompt 提取
    print("\n🤖 Step 3: 调用 LLM 提取结构化信息...")
    
    print("  (1/5) 提取 paper_info...")
    paper_info = call_llm(client, PROMPT_PAPER_INFO, title_text)
    
    print("  (2/5) 提取 problem...")
    problem = call_llm(client, PROMPT_PROBLEM, intro_text)
    
    print("  (3/5) 提取 method...")
    method = call_llm(client, PROMPT_METHOD, method_text)
    
    print("  (4/5) 提取 experiments...")
    experiments = call_llm(client, PROMPT_EXPERIMENTS, experiment_text)
    
    print("  (5/5) 提取 conclusion...")
    conclusion = call_llm(client, PROMPT_CONCLUSION, conclusion_text)
    
    # 4. 合并为完整中间格式
    print("\n🔗 Step 4: 合并为中间格式 JSON...")
    result = {
        "paper_info": paper_info,
        "problem": problem,
        "method": method,
        "experiments": experiments,
        "conclusion": conclusion,
    }
    
    # 5. 保存
    if output_path is None:
        output_path = "output_images/intermediate_format.json"
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 中间格式 JSON 已保存: {output_path}")
    return result


def print_summary(result: dict):
    """打印中间格式 JSON 摘要。"""
    print(f"\n{'='*60}")
    print(f"📊 中间格式 JSON 摘要")
    print(f"{'='*60}")
    
    # paper_info
    pi = result.get("paper_info", {})
    print(f"\n📄 paper_info:")
    print(f"   标题: {pi.get('title', 'N/A')}")
    print(f"   作者: {', '.join(pi.get('authors', []))}")
    print(f"   摘要长度: {len(pi.get('abstract', ''))} 字")
    
    # problem
    pb = result.get("problem", {})
    print(f"\n🔍 problem:")
    print(f"   问题描述: {pb.get('description', 'N/A')[:80]}...")
    print(f"   现有不足: {len(pb.get('limitations_of_existing', []))} 条")
    
    # method
    mt = result.get("method", {})
    print(f"\n⚙️ method:")
    print(f"   方法名: {mt.get('name', 'N/A')}")
    print(f"   贡献点: {len(mt.get('key_contributions', []))} 条")
    print(f"   模块数: {len(mt.get('modules', []))} 个")
    total_formulas = sum(len(m.get("formulas", [])) for m in mt.get("modules", []))
    print(f"   公式数: {total_formulas} 个")
    
    # experiments
    exp = result.get("experiments", {})
    print(f"\n🧪 experiments:")
    print(f"   数据集: {len(exp.get('datasets', []))} 个")
    print(f"   基线方法: {len(exp.get('baselines', []))} 个")
    print(f"   实验结果: {len(exp.get('main_results', []))} 组")
    if exp.get("ablation_study"):
        print(f"   消融实验: 有")
    
    # conclusion
    cl = result.get("conclusion", {})
    print(f"\n📌 conclusion:")
    print(f"   结论: {cl.get('summary', 'N/A')[:80]}...")
    if cl.get("future_work"):
        print(f"   未来工作: {cl.get('future_work')[:60]}...")


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "output_images/per_page_results.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"📖 读取逐页结果: {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        per_page_results = json.load(f)
    
    result = build_intermediate_format(per_page_results, output_path)
    print_summary(result)
