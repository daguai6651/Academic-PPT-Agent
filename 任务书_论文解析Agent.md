# 任务书：论文解析 Agent（Phase 1）

> **任务编号：** P1
> **创建日期：** 2026-04-22
> **负责人：** 时晶晶（执行）/ 张工（审核）
> **预计周期：** 2-3 周

---

## 一、任务目标

开发一个 **论文解析 Agent**，能够将计算机专业学术论文（PDF）自动解析为结构化的 **中间格式 JSON**，为后续的演示文稿绘制 Agent 提供标准化的数据输入。

### 核心要求

1. 输入：计算机论文的 PDF 文件
2. 输出：结构化的中间格式 JSON（纯内容，无视觉信息）
3. 准确率：核心字段提取准确率 ≥ 80%
4. 覆盖范围：至少覆盖 CV/NLP 领域的计算机论文

---

## 二、输入/输出定义

### 2.1 输入

| 输入类型 | 格式 | 优先级 | 说明 |
|----------|------|--------|------|
| **PDF 文件** | .pdf | P0（Phase 1） | 学术论文标准格式，通用性强 |
| **LaTeX 源码** | .tex 文件 | P2（后续） | 如果 PDF 解析不理想再考虑 |

### 2.2 输出（中间格式 JSON）

```json
{
  "paper_info": {
    "title": "论文标题",
    "title_en": "论文英文标题",
    "authors": ["作者1", "作者2"],
    "affiliations": ["机构1", "机构2"],
    "venue": "会议/期刊名称",
    "year": 2026,
    "abstract": "摘要内容（200-500 字）",
    "keywords": ["关键词1", "关键词2"]
  },
  "problem": {
    "description": "本文要解决的核心问题（3-5 句话）",
    "motivation": "研究动机（为什么这个问题重要，2-3 句话）",
    "limitations_of_existing": [
      "现有方法1的不足（1-2句话）",
      "现有方法2的不足（1-2句话）",
      "现有方法3的不足（1-2句话）"
    ]
  },
  "method": {
    "name": "方法名称（如 'Multi-Scale Attention Network'）",
    "overview": "方法整体概述（5-8 句话，涵盖核心思想）",
    "key_contributions": [
      "贡献点1（1-2句话）",
      "贡献点2（1-2句话）",
      "贡献点3（1-2句话）"
    ],
    "modules": [
      {
        "name": "模块名称",
        "description": "模块功能说明（3-5 句话）",
        "formulas": [
          {
            "id": "eq1",
            "latex": "LaTeX 公式代码",
            "description": "公式含义说明",
            "variables": {
              "Q": "Query 向量",
              "K": "Key 向量",
              "V": "Value 向量",
              "d_k": "Key 向量维度"
            }
          }
        ],
        "figure_reference": "Figure X: 对应的架构图编号和描述"
      }
    ],
    "architecture_description": "整体架构的文字描述（用于生成 Mermaid 流程图）"
  },
  "experiments": {
    "datasets": [
      {
        "name": "数据集名称",
        "description": "数据集说明（规模、领域等）",
        "size": "数据量描述"
      }
    ],
    "baselines": [
      "基线方法1",
      "基线方法2",
      "基线方法3"
    ],
    "metrics": [
      { "name": "指标名称", "description": "指标说明" }
    ],
    "main_results": [
      {
        "name": "实验名称（如 '主实验：英德翻译'）",
        "description": "实验说明（1-2 句话）",
        "table": {
          "caption": "表格标题",
          "headers": ["模型", "BLEU", "参数量"],
          "rows": [
            ["Ours (big)", "28.4", "213M"],
            ["Baseline", "24.6", "225M"]
          ],
          "highlight_row": 0,
          "highlight_col": 1
        }
      }
    ],
    "ablation_study": {
      "description": "消融实验说明",
      "table": {
        "caption": "消融实验结果",
        "headers": ["变体", "BLEU", "说明"],
        "rows": [
          ["Full Model", "28.4", "完整模型"],
          ["w/o Attention", "25.1", "移除注意力模块"],
          ["w/o Pretrain", "27.0", "移除预训练"]
        ],
        "highlight_row": 0
      }
    }
  },
  "conclusion": {
    "summary": "论文结论（3-5 句话）",
    "future_work": "未来工作方向（2-3 句话）"
  }
}
```

---

## 三、技术方案

### 3.1 整体流程

```
输入（PDF 文件）
    │
    ▼
┌──────────────────────┐
│  Step 1: PDF → 图片  │  逐页渲染为高清图片
│  （pdf2image）        │  300 DPI，保留公式和表格清晰度
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Step 2: 逐页内容提取 │  Qwen3-VL 视觉模型识别每页内容
│  （Qwen3-VL）         │  输出每页的结构化信息
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Step 3: 章节分类     │  将逐页信息按章节归类
│  （LLM 辅助）         │  识别 Intro/Method/Experiment/Conclusion
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Step 4: 结构化提取   │  按章节送入 LLM，提取中间格式字段
│  （4 个 Prompt）      │  输出 problem/method/experiments/conclusion
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Step 5: 后处理 & 校验│  JSON Schema 校验、字段补全
│  （规则）             │  缺失字段标记
└──────────┬───────────┘
           │
           ▼
输出（中间格式 JSON）
```

### 3.2 Step 1：PDF → 图片

**工具：** `pdf2image`（基于 Poppler）

```bash
# Mac 安装 Poppler
brew install poppler
pip install pdf2image
```

**渲染参数：**
- DPI：300（保证公式和表格清晰）
- 格式：PNG
- 输出：`page_001.png`, `page_002.png`, ...

### 3.3 Step 2：逐页内容提取（Qwen3-VL）

**模型：** `qwen3-vl-plus`（DashScope API）

**Prompt 模板：**

```
你是一个学术论文解析专家。请仔细分析这张论文页面的内容，提取以下信息：

1. 页面类型：标题页 / 摘要页 / 正文章节 / 参考文献页
2. 章节标题（如果有）
3. 正文内容（按段落提取，保留公式的 LaTeX 格式）
4. 表格信息（如果有，提取为 Markdown 表格）
5. 图表信息（如果有，提取图注和描述）
6. 公式（如果有，提取为 LaTeX 格式）

请以 JSON 格式输出。
```

**输出示例：**

```json
{
  "page_number": 1,
  "page_type": "正文",
  "section_title": "2 Method",
  "content": ["本文提出了一种新的...", "该方法包含三个模块..."],
  "tables": [],
  "figures": [{"caption": "Figure 1: 模型架构图", "description": "..."}],
  "formulas": [{"latex": "Attention(Q, K, V) = softmax(QK^T / \\sqrt{d_k})V", "description": "自注意力公式"}]
}
```

### 3.4 Step 3：章节分类

将逐页提取的信息按语义归类为以下章节：

| 分类标签 | 对应论文部分 | 用途 |
|---------|-------------|------|
| `problem` | Introduction + Related Work | 研究问题、动机、现有方法不足 |
| `method` | Method / Approach / Model | 方法概述、模块、公式 |
| `experiments` | Experiment / Evaluation | 实验设置、结果表格 |
| `conclusion` | Conclusion | 结论和未来工作 |

**分类方式：** 用 Qwen3-VL 一次性分析所有页面的 `section_title`，自动判断每页属于哪个章节。

### 3.5 Step 4：结构化提取（4 个 Prompt）

按章节分步提取，减少 LLM 上下文压力：

| Prompt | 输入 | 输出 |
|--------|------|------|
| **Prompt 1** | Introduction + Related Work 的页面内容 | `problem` 字段 |
| **Prompt 2** | Method 章节的页面内容 + 公式 | `method` 字段 |
| **Prompt 3** | Experiment 章节的页面内容 + 表格 | `experiments` 字段 |
| **Prompt 4** | Conclusion 章节的页面内容 | `conclusion` 字段 |

### 3.6 Step 5：后处理与校验

1. **JSON Schema 校验** — 用 `pydantic` 校验输出格式
2. **缺失字段检测** — 标记哪些字段没有提取到
3. **字段合并** — 将 4 个 Prompt 的输出合并为完整的中间格式 JSON

---

## 四、Prompt 设计草案

### Prompt 1：问题与动机提取

```
你是计算机领域的学术专家。请阅读以下论文的 Introduction 和 Related Work 部分，
提取以下结构化信息：

## 任务
1. 提取本文要解决的核心问题（3-5 句话）
2. 提取研究动机（为什么这个问题重要，2-3 句话）
3. 提取现有方法的不足（至少 2 条，每条 1-2 句话）

## 输入文本
{introduction_and_related_work}

## 输出格式（严格遵循此 JSON 结构，不要输出其他内容）
{
  "problem": {
    "description": "...",
    "motivation": "...",
    "limitations_of_existing": ["...", "..."]
  }
}
```

### Prompt 2：方法提取

```
你是计算机领域的学术专家。请阅读以下论文的 Method 部分，
提取以下结构化信息：

## 任务
1. 提取方法的名称
2. 提取方法的整体概述（5-8 句话）
3. 提取论文的主要贡献点（通常 3 条，每条 1-2 句话）
4. 提取各个模块的说明（名称 + 描述）
5. 提取所有公式及其含义说明

## 输入文本
{method_section}

## 输出格式
{
  "method": {
    "name": "...",
    "overview": "...",
    "key_contributions": ["...", "..."],
    "modules": [
      {
        "name": "...",
        "description": "...",
        "formulas": [
          {
            "id": "eq1",
            "latex": "...",
            "description": "...",
            "variables": {"符号": "含义"}
          }
        ]
      }
    ],
    "architecture_description": "..."
  }
}
```

（Prompt 3 和 Prompt 4 类似设计，此处略）

---

## 五、测试集设计

### 5.1 测试论文选择

| 编号 | 论文 | 领域 | 来源 | 说明 |
|------|------|------|------|------|
| T01 | Attention Is All You Need | NLP/Transformer | arXiv:1706.03762 | 经典论文，结构清晰 |
| T02 | BERT: Pre-training of Deep Bidirectional Transformers | NLP | arXiv:1810.04805 | 方法复杂，公式多 |
| T03 | ViT: An Image is Worth 16x16 Words | CV | arXiv:2010.11929 | CV 领域，跨模态 |
| T04 | DETR: End-to-End Object Detection | CV | arXiv:2005.12872 | 检测任务，实验多 |
| T05 | LoRA: Low-Rank Adaptation | 大模型微调 | arXiv:2106.09685 | 方法简单，适合初测 |

### 5.2 标注标准

每篇论文由张工手动标注标准答案（中间格式 JSON），作为 ground truth。

### 5.3 评估方法

| 评估维度 | 计算方式 | 目标 |
|---------|---------|------|
| **字段完整率** | Agent 输出的非空字段数 / 总字段数 | ≥ 90% |
| **内容准确率** | 手动逐条对比，正确字段数 / 总字段数 | ≥ 80% |
| **公式提取率** | 正确提取的公式数 / 论文总公式数 | ≥ 85% |
| **表格提取率** | 正确提取的实验表格数 / 论文总表格数 | ≥ 80% |

---

## 六、执行步骤

### Step 1：PDF 渲染与 Qwen3-VL 调通（3 天）

- [ ] 安装 `pdf2image` + Poppler（`brew install poppler`）
- [ ] 开发 `pdf_to_images.py` 脚本：PDF 逐页转 300 DPI PNG
- [ ] 调通 Qwen3-VL API：单页图片 → 结构化 JSON 提取
- [ ] 测试 1-2 篇论文的逐页提取效果
- [ ] 验证公式和表格的识别准确率

### Step 2：Prompt 设计与迭代（5 天）

- [ ] 设计 4 个核心 Prompt
- [ ] 用 T01（Attention Is All You Need）做初始测试
- [ ] 对比 LLM 输出与手动标注的 ground truth
- [ ] 迭代 Prompt 直到核心字段准确率 ≥ 70%
- [ ] 扩展到 T02-T03，验证泛化能力

### Step 3：测试集标注（张工负责，3 天）

- [ ] 张工手动标注 T01-T05 的 ground truth JSON
- [ ] 标注标准：每个字段的内容必须与论文原文一致

### Step 4：全面评估与优化（4 天）

- [ ] 在 5 篇测试论文上跑 Agent
- [ ] 计算各维度评估指标
- [ ] 针对低分字段优化 Prompt
- [ ] 最终目标准确率 ≥ 80%

### Step 5：集成接口（2 天）

- [ ] 封装为 Python 模块或 API
- [ ] 输入：.tex 文件路径
- [ ] 输出：中间格式 JSON 文件
- [ ] 编写使用说明

---

## 七、技术选型

| 模块 | 技术选型 | 说明 |
|------|---------|------|
| **PDF 渲染** | pdf2image + Poppler | PDF 逐页转高清图片 |
| **视觉模型** | qwen3-vl-plus（DashScope API） | 文档解析能力最强，表格/公式识别准 |
| **文本 LLM** | qwen-plus（DashScope API） | 结构化信息提取，性价比高 |
| **JSON 校验** | pydantic | 定义 Schema，自动校验 |
| **测试脚本** | Python | 评估脚本 |

---

## 八、风险点与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| **PDF 双栏解析困难** | 双栏论文的阅读顺序可能混乱 | Qwen3-VL 有文档解析能力，可自动识别版面 |
| **公式提取不完整** | 复杂公式（矩阵、多行）识别失败 | 标记为占位，后续人工补充 |
| **Qwen3-VL 输出格式不稳定** | JSON 解析失败 | 加重试机制 + JSON Schema 校验 |
| **长论文页数多** | 逐页调用 API 成本高、耗时长 | 按章节分组批量处理，减少调用次数 |
| **表格跨页** | 实验表格可能被分页截断 | 后处理时合并跨页表格 |
| **API 额度用完** | 张工以后没有 API 可用 | 当前阶段集中使用，优先保证核心功能验证 |

---

## 九、交付物

1. `pdf_to_images.py` — PDF 逐页转图片脚本
2. `paper_parser_agent.py` — 论文解析 Agent 主程序（Qwen3-VL + LLM）
3. `prompts/` — Prompt 文件目录（含逐页提取 + 4 个结构化提取 Prompt）
4. `test_data/` — 测试集（5 篇论文 PDF + ground truth JSON）
5. `eval_results/` — 评估报告（各维度指标）
6. `README.md` — 使用说明

---

## 十、验收标准

- [ ] 5 篇测试论文的平均字段完整率 ≥ 90%
- [ ] 5 篇测试论文的平均内容准确率 ≥ 80%
- [ ] 公式提取率 ≥ 85%
- [ ] 表格提取率 ≥ 80%
- [ ] 单篇论文解析耗时 ≤ 30 秒（含 LLM 调用时间）
- [ ] 输出 JSON 通过 Schema 校验，无格式错误

---

_张工审核通过后，时晶晶开始执行。_
