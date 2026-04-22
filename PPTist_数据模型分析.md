# PPTist 数据模型与改造分析

> **分析日期：** 2026-04-22
> **PPTist 版本：** master 分支
> **项目路径：** `/Users/opple/Desktop/zx/Academic_PPT_Agent/PPTist-master`

---

## 一、项目概览

| 项目 | 说明 |
|------|------|
| **技术栈** | Vue 3.x + TypeScript + Vite + Pinia |
| **核心功能** | 在线 PPT 编辑器，支持文字、图片、形状、线条、图表、表格、公式、视频、音频 |
| **导出格式** | JSON、PPTX、PDF、图片（PNG/JPG）、.pptist（专属加密格式） |
| **导入格式** | JSON、PPTX、.pptist |
| **已有 AI 功能** | AIPPT — 基于模板 + LLM 生成 PPT |
| **许可证** | AGPL-3.0 |

---

## 二、核心数据模型

### 2.1 顶层 JSON 结构（导出/导入格式）

```json
{
  "title": "演示文稿标题",
  "width": 1000,
  "height": 562.5,
  "theme": { ... },
  "slides": [ ... ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 演示文稿标题 |
| `width` | number | 画布宽度基数（默认 1000） |
| `height` | number | 画布高度 = width × viewportRatio（默认 0.5625，即 16:9） |
| `theme` | SlideTheme | 主题配置 |
| `slides` | Slide[] | 幻灯片页面数组 |

### 2.2 主题配置（SlideTheme）

```typescript
interface SlideTheme {
  backgroundColor: string       // 页面背景颜色，如 '#fff'
  themeColors: string[]         // 主题色数组，默认6色
  fontColor: string             // 字体颜色，如 '#333'
  fontName: string              // 默认字体
  outline: PPTElementOutline    // 默认边框
  shadow: PPTElementShadow      // 默认阴影
}
```

### 2.3 幻灯片页面（Slide）

```typescript
interface Slide {
  id: string                    // 页面唯一ID
  elements: PPTElement[]        // 页面内所有元素
  notes?: Note[]                // 批注
  remark?: string               // 备注（HTML）
  background?: SlideBackground  // 页面背景
  animations?: PPTAnimation[]   // 元素动画
  turningMode?: TurningMode     // 翻页方式
  sectionTag?: SectionTag       // 章节标记
  type?: SlideType              // 页面类型（cover/contents/transition/content/end）
}
```

**页面类型说明：**
- `cover` — 封面页
- `contents` — 目录页
- `transition` — 章节过渡页
- `content` — 内容页
- `end` — 结束页

> **对我们项目的意义：** 学术论文汇报可以直接用 `cover` + `content` + `end` 这三种类型就够。

### 2.4 元素类型（PPTElement）

**9 种元素类型，我们只需要其中 5 种：**

| 元素类型 | type 值 | 是否必需 | 说明 |
|----------|---------|---------|------|
| 文本 | `text` | ✅ 必需 | 标题、正文、列表等，content 为 HTML 字符串 |
| 图片 | `image` | ✅ 必需 | 架构图、实验结果图等，src 为 URL/base64 |
| 公式 | `latex` | ✅ 必需 | LaTeX 公式，存储为 SVG path |
| 表格 | `table` | ✅ 必需 | 实验结果对比表 |
| 形状 | `shape` | ⚠️ 可选 | 装饰性图形、背景色块等 |
| 线条 | `line` | ❌ 不需要 | 箭头、连接线等 |
| 图表 | `chart` | ⚠️ 可选 | 柱状图、折线图、饼图等（用 ECharts 渲染） |
| 视频 | `video` | ❌ 不需要 | 视频播放 |
| 音频 | `audio` | ❌ 不需要 | 音频播放 |

### 2.5 文本元素（PPTTextElement）— 最常用

```typescript
interface PPTTextElement {
  type: 'text'
  id: string
  left: number          // 距离画布左侧
  top: number           // 距离画布顶部
  width: number
  height: number
  rotate: number        // 旋转角度
  content: string       // ⚠️ HTML 字符串（不是纯文本！）
  defaultFontName: string
  defaultColor: string
  lineHeight?: number   // 行高（倍），默认 1.5
  wordSpace?: number    // 字间距
  fill?: string         // 背景填充色
  outline?: PPTElementOutline  // 边框
  shadow?: PPTElementShadow    // 阴影
  opacity?: number      // 不透明度
  paragraphSpace?: number  // 段间距，默认 5px
  vertical?: boolean    // 竖向文本
  textType?: TextType   // 文本类型：title/subtitle/content/item/itemTitle/notes/header/footer/partNumber/itemNumber
}
```

**content 字段示例（HTML 字符串）：**
```html
<p style="font-size: 32px; font-weight: bold; color: #333;">研究背景</p>
<p style="font-size: 16px; color: #666;">现有方法存在以下问题：</p>
<p style="font-size: 16px; color: #666;">1. 检索精度不足</p>
<p style="font-size: 16px; color: #666;">2. 缺乏上下文理解</p>
```

> **对我们项目的意义：** AI 生成的内容需要包装成 HTML 格式，而不是纯文本。这是关键。

### 2.6 公式元素（PPTLatexElement）

```typescript
interface PPTLatexElement {
  type: 'latex'
  id: string
  left: number
  top: number
  width: number
  height: number
  rotate: number
  latex: string       // LaTeX 代码，如 '\frac{a}{b}'
  path: string        // SVG path（渲染后）
  color: string
  strokeWidth: number
  viewBox: [number, number]
  fixedRatio: boolean
}
```

> **注意：** PPTist 的 LaTeX 元素渲染方式是把 LaTeX 转为 SVG path 存储。如果我们的 AI 生成 JSON 时只填 `latex` 字段，`path` 为空，可能需要前端渲染时自动生成。

### 2.7 表格元素（PPTTableElement）

```typescript
interface PPTTableElement {
  type: 'table'
  id: string
  left: number
  top: number
  width: number
  height: number
  rotate: number
  outline: PPTElementOutline
  theme?: TableTheme
  colWidths: number[]         // 列宽比例，如 [0.3, 0.4, 0.3]
  cellMinHeight: number       // 单元格最小高度
  data: TableCell[][]         // 二维数组
}

interface TableCell {
  id: string
  colspan: number
  rowspan: number
  text: string                // 纯文本（不是 HTML）
  style?: TableCellStyle
}

interface TableCellStyle {
  bold?: boolean
  em?: boolean                // 斜体
  underline?: boolean
  strikethrough?: boolean
  color?: string              // 字体颜色
  backcolor?: string          // 单元格背景色
  fontsize?: string           // 如 '14px'
  fontname?: string
  align?: 'left' | 'center' | 'right'
  vAlign?: 'top' | 'middle' | 'bottom'
}
```

### 2.8 图片元素（PPTImageElement）

```typescript
interface PPTImageElement {
  type: 'image'
  id: string
  left: number
  top: number
  width: number
  height: number
  rotate: number
  fixedRatio: boolean     // 固定宽高比
  src: string             // 图片 URL 或 base64
  outline?: PPTElementOutline
  filters?: ImageElementFilters
  clip?: ImageElementClip
  flipH?: boolean
  flipV?: boolean
  shadow?: PPTElementShadow
  radius?: number         // 圆角
  colorMask?: string
  imageType?: 'pageFigure' | 'itemFigure' | 'background'
}
```

---

## 三、Store 状态管理

**核心 Store：** `src/store/slides.ts`

```typescript
interface SlidesState {
  title: string           // 标题
  theme: SlideTheme       // 主题
  slides: Slide[]         // 所有页面
  slideIndex: number      // 当前页索引
  viewportSize: number    // 画布宽度基数（默认 1000）
  viewportRatio: number   // 画布比例（默认 0.5625）
  templates: SlideTemplate[]  // 模板列表
}
```

**关键 Actions（我们需要的）：**

| Action | 说明 |
|--------|------|
| `setSlides(slides, themeProps)` | 替换所有幻灯片（导入 JSON 时用） |
| `addSlide(slide)` | 添加页面 |
| `updateSlide(props, slideId)` | 更新页面属性 |
| `addElement(element)` | 添加元素到当前页 |
| `updateElement({ id, props, slideId })` | 更新元素属性（**局部修改的核心！**） |
| `deleteElement(elementId)` | 删除元素 |
| `setTitle(title)` | 设置标题 |
| `setTheme(themeProps)` | 设置主题 |

> **对我们项目的意义：** `updateElement` 就是局部修改的基础。我们只需要生成修改后的元素 JSON，调用这个 action 就能应用到页面。

---

## 四、导入/导出机制

### 4.1 导出 JSON

```typescript
// src/hooks/useExport.ts
const exportJSON = () => {
  const json = {
    title: title.value,
    width: viewportSize.value,
    height: viewportSize.value * viewportRatio.value,
    theme: theme.value,
    slides: slides.value,
  }
  const blob = new Blob([JSON.stringify(json)], { type: '' })
  saveAs(blob, `${title.value}.json`)
}
```

### 4.2 导入 JSON

```typescript
// src/hooks/useImport.ts
const importJSON = (files, cover = false) => {
  const file = files[0]
  const reader = new FileReader()
  reader.addEventListener('load', () => {
    const { slides, theme, width, height } = JSON.parse(reader.result)
    slidesStore.setSlides(slides, theme)
    // 自动适配 viewport
    slidesStore.setViewportRatio(getAspectRatio(width, height))
    slidesStore.setViewportSize(width)
  })
  reader.readAsText(file)
}
```

> **对我们项目的意义：** 我们的 AI 生成的 JSON 格式必须和导出 JSON 完全一致，才能被 `importJSON` 正确导入。

### 4.3 导出 PPTX

使用 `pptxgenjs` 库，将每个元素转换为 PPTX 格式。公式（latex）元素会被转为 SVG 图片嵌入。

### 4.4 导入 PPTX

使用 `pptxtojson` 库，将 PPTX 解析为 JSON 格式。但官方标注"仅供测试"，说明解析不完全可靠。

---

## 五、现有 AI 功能分析（AIPPT）

PPTist 已经内置了 AI 生成 PPT 的功能（`src/hooks/useAIPPT.ts`）。

### 5.1 工作原理

1. **输入：** 用户输入一个主题
2. **LLM 生成：** 调用后端 API，返回 Markdown 格式的 PPT 大纲
3. **模板填充：** 使用预设的模板幻灯片，将 LLM 生成的文本内容填入模板元素中
4. **渲染：** 将填充后的幻灯片添加到编辑器中

### 5.2 输入格式（AIPPTSlide）

```typescript
interface AIPPTSlide {
  type: 'cover' | 'contents' | 'transition' | 'content' | 'end'
  data: {
    title?: string
    text?: string
    items?: Array<{
      title?: string
      text?: string
    }>
  }
  offset?: number  // 用于分页
}
```

### 5.3 核心逻辑

- 根据 `type` 选择对应的模板幻灯片（封面/目录/过渡/内容/结束）
- 根据 `textType`（title/subtitle/content/item/itemNumber）匹配模板中的文本元素
- 用 LLM 返回的内容替换模板文本
- 图片从图片池中随机匹配

### 5.4 对我们项目的启示

**可以直接复用的部分：**
- `getAdaptedFontsize()` — 自适应字体大小（根据文本长度和容器尺寸计算）
- `getNewTextElement()` — 根据文本内容更新文本元素
- 模板匹配逻辑（根据页面类型和内容数量选择合适的模板）

**需要改造的部分：**
- 现有的 AIPPT 只支持文本替换，不支持公式、表格、架构图
- 模板是预设的，我们需要动态生成布局
- 没有局部修改功能

---

## 六、改造方案

### 6.1 最小改造清单

| 改造项 | 说明 | 难度 |
|--------|------|------|
| **新增 API 接口** | 接收外部 JSON 数据，直接调用 `setSlides()` 渲染 | ⭐ 低 |
| **局部修改交互** | 侧边栏显示修改方案，accept/reject 后调用 `updateElement()` | ⭐⭐ 中 |
| **LaTeX 渲染增强** | 确保 AI 生成的 `latex` 元素能正确渲染 | ⭐⭐ 中 |
| **Mermaid 图表支持** | 新增图表元素类型，支持 Mermaid 语法渲染 | ⭐⭐⭐ 较高 |
| **学术模板** | 新增学术汇报专用模板（8-10 页） | ⭐⭐ 中 |

### 6.2 JSON 生成规范

我们的 AI Agent 生成的 JSON 必须严格遵循以下格式：

```json
{
  "title": "论文标题",
  "width": 1000,
  "height": 562.5,
  "theme": {
    "backgroundColor": "#ffffff",
    "themeColors": ["#5b9bd5", "#ed7d31", "#a5a5a5", "#ffc000", "#4472c4", "#70ad47"],
    "fontColor": "#333333",
    "fontName": "",
    "outline": { "width": 2, "color": "#525252", "style": "solid" },
    "shadow": { "h": 3, "v": 3, "blur": 2, "color": "#808080" }
  },
  "slides": [
    {
      "id": "slide_001",
      "type": "cover",
      "elements": [
        {
          "type": "text",
          "id": "el_001",
          "left": 100,
          "top": 200,
          "width": 800,
          "height": 100,
          "rotate": 0,
          "content": "<p style=\"font-size: 32px; font-weight: bold; text-align: center;\">论文标题</p>",
          "defaultFontName": "",
          "defaultColor": "#333333",
          "textType": "title",
          "lineHeight": 1.5,
          "paragraphSpace": 5
        }
      ],
      "background": { "type": "solid", "color": "#ffffff" }
    }
  ]
}
```

### 6.3 局部修改流程

```
1. 用户点击选中元素 → 获取元素 ID 和当前 JSON
2. 用户输入修改指令 → 发送给 AI Agent
3. AI Agent 返回修改后的元素 JSON（diff）
4. 前端显示预览（当前 vs 修改后）
5. 用户点击"接受" → 调用 updateElement({ id, props, slideId })
6. 用户点击"拒绝" → 不做任何操作
```

---

## 七、下一步行动

### Phase 0 具体任务

1. **运行 PPTist 开发服务器**
   ```bash
   cd /Users/opple/Desktop/zx/Academic_PPT_Agent/PPTist-master
   npm install
   npm run dev
   ```

2. **导出一个示例 JSON**
   - 在 PPTist 在线编辑器中创建一个简单的 3 页 PPT
   - 导出 JSON 文件
   - 分析实际生成的 JSON 结构

3. **手写一个学术 PPT 的 JSON**
   - 根据上面的数据模型，手动写一个 5 页的学术汇报 JSON
   - 包含：封面、研究背景、方法概述、实验结果、结论
   - 至少包含 text 和 table 两种元素类型

4. **导入验证**
   - 在 PPTist 中导入手写的 JSON
   - 检查是否能正确渲染
   - 截图记录

5. **输出文档**
   - 记录成功的 JSON 模板
   - 记录遇到的问题和解决方案

---

## 八、关键发现总结

1. **PPTist 的数据模型很清晰** — 每个元素都有明确的 TypeScript 类型定义，JSON 格式规范
2. **导入/导出 JSON 已经完善** — 我们只需要生成符合格式的 JSON 就能直接使用
3. **局部修改有现成的 API** — `updateElement()` action 可以更新任意元素的任意属性
4. **已有 AI 生成框架** — `useAIPPT.ts` 展示了模板填充的思路，可以在此基础上扩展
5. **LaTeX 公式需要特别注意** — PPTist 的 latex 元素需要 `path` 字段（SVG path），AI 生成时可能需要前端渲染后回填
6. **表格元素用纯文本** — 表格的 cell.text 是纯文本，不是 HTML，比文本元素简单
7. **文本元素用 HTML** — 文本的 content 是 HTML 字符串，AI 生成时需要包装成 HTML 格式

---

_分析完成。下一步：运行 PPTist，导出示例 JSON，手写学术 PPT JSON 并验证渲染。_
