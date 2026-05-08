---
name: drawio-skill
version: 1.5.2
description: 当用户请求图表、流程图、架构图或可视化时使用。当主动解释 3+ 组件、复杂数据流或关系时也触发。使用原生 draw.io 桌面 CLI 在本地生成 .drawio XML 文件并导出为 PNG/SVG/PDF。
license: MIT
compatibility: Requires draw.io desktop app CLI on PATH (Linux/Windows). Self-check step requires a vision-enabled model (e.g., Claude Sonnet/Opus); gracefully skipped if unavailable.
platforms: [linux, windows]
metadata: {"openclaw":{"requires":{"anyBins":["draw.io","drawio"]},"emoji":"📐","os":["linux","win32"],"install":[{"id":"brew-drawio","kind":"brew","formula":"drawio","bins":["draw.io"],"label":"Install draw.io via Homebrew","os":["darwin"]}]},"hermes":{"tags":["drawio","diagram","flowchart","architecture","visualization","uml"],"category":"design","requires_tools":["draw.io"],"related_skills":["mermaid","excalidraw","plantuml"]},"author":"Agents365-ai","version":"1.5.2"}
---

# Draw.io 图表

## 概述

使用原生 draw.io 桌面应用 CLI 在本地生成 `.drawio` XML 文件并导出为 PNG/SVG/PDF/JPG。

**支持格式：** PNG、SVG、PDF、JPG — 无需浏览器自动化。

PNG、SVG 和 PDF 导出支持 `--embed-diagram`（`-e`）— 导出的文件包含完整的图表 XML，在 draw.io 中打开即可恢复可编辑的图表。使用双扩展名（如 `name.drawio.png`）表示嵌入了 XML。

## 捆绑资源

当工作流引用以下文件时，按需读取 — 无需预先加载所有内容。

| 文件 | 何时读取 |
|---|---|
| `references/diagram-types.md` | 用户指定了特定图表类型（ERD、UML 类、序列、架构、ML/DL、流程图） |
| `references/style-presets.md` | 用户请求学习/保存/列出/设默认/删除样式预设，或已解析到活动预设并需要应用规则 |
| `references/style-extraction.md` | 处于 Learn 流程中，需要提取步骤（由 `style-presets.md` 调用） |
| `references/troubleshooting.md` | 导出失败、vision 拒绝 PNG、或渲染结果异常 |
| `scripts/repair_png.py` | 每次 `-e` PNG 导出后 — 修复 draw.io 截断的 IEND 块（issue #8） |
| `scripts/encode_drawio_url.py` | CLI 不可用时，需要浏览器后备 diagrams.net URL |

## 前置条件

必须安装 draw.io 桌面应用且 CLI 可访问：

```bash
# Linux
draw.io --version

# Windows — 自动检测安装路径
if command -v draw.io &>/dev/null; then
  DRAWIO="draw.io"
elif [ -f "C:/Program Files/draw.io/draw.io.exe" ]; then
  DRAWIO="C:/Program Files/draw.io/draw.io.exe"
elif [ -f "C:/Program Files (x86)/draw.io/draw.io.exe" ]; then
  DRAWIO="C:/Program Files (x86)/draw.io/draw.io.exe"
elif [ -f "$LOCALAPPDATA/draw.io/draw.io.exe" ]; then
  DRAWIO="$LOCALAPPDATA/draw.io/draw.io.exe"
elif [ -f "D:/Program Files/draw.io/draw.io.exe" ]; then
  DRAWIO="D:/Program Files/draw.io/draw.io.exe"
elif [ -f "D:/opt/tool/draw.io/draw.io.exe" ]; then
  DRAWIO="D:/opt/tool/draw.io/draw.io.exe"
else
  echo "未检测到 draw.io 应用，请先从 https://github.com/jgraph/drawio-desktop/releases 下载安装"
fi
"$DRAWIO" --version
```

缺少 draw.io 桌面应用时的安装方式：
- Linux：从 https://github.com/jgraph/drawio-desktop/releases 下载 `.deb`/`.rpm` — **不要用 snap**（AppArmor 沙盒会拒绝 secrets/keyring，导致服务器崩溃）
- Windows：从 https://github.com/jgraph/drawio-desktop/releases 下载安装程序

## 工作流

开始工作流前，评估用户请求是否足够具体。如缺少关键细节，问 1-3 个聚焦问题：
- **图表类型** — 哪个预设？（ERD、UML、序列、架构、ML/DL、流程图，或通用）
- **输出格式** — PNG（默认）、SVG、PDF 还是 JPG？
- **输出位置** — 默认是用户工作目录；遵循用户明确指定的路径（如 "put it in `./artifacts/`"）。未提及则不追问。
- **范围/保真度** — 有多少组件？有哪些特定技术或标签？

如果请求已明确指定这些细节或明显简单（如 "draw a flowchart of X"），跳过澄清。

0. **更新检查（通知，不拉取）** — 对话中首次使用。通过 `<this-skill-dir>/.last_update` 节流至每 24 小时；未经用户明确同意绝不修改 skill 目录。

   - 如果 `.last_update` 存在且未满 24 小时，完全跳过此步骤。
   - 否则，从上游获取最新标签：
     ```bash
     git -C <this-skill-dir> ls-remote --tags origin 'v*' 2>/dev/null \
       | awk '{print $2}' | sed 's|refs/tags/||' | sort -V | tail -1
     ```
   - 与 frontmatter 中 skill 的 `metadata.version` 比较。如果上游标签更新（semver 严格更大），告诉用户一行并询问：
     > "A newer version of this skill is available: vX.Y.Z → vA.B.C. Want me to `git pull`?"

     如果用户同意，运行 `git -C <this-skill-dir> pull --ff-only`。无论是否同意都刷新 `.last_update`，使提示在 24 小时内不重复。
   - 如果上游相同或更旧，静默刷新 `.last_update` 并继续。
   - 任何失败时（离线、不是 git 仓库——如 ClawHub 安装的副本、只读路径、无权限），静默吞下错误并继续用户任务。不提及失败。

**Step 0.5 — 解析活动预设。** 确定本次生成适用哪个（如果有）用户定义的样式预设。

- 扫描用户消息中明确命名样式预设的短语："use my `<name>` style"、"with my `<name>` style"、"in `<name>` mode"、"in the style of `<name>`"。单独的 `with <name>` 不算数 — "draw a diagram with redis" 命名的是组件而非样式。如果找到明确匹配 → 活动预设 = `<name>`。
- 否则，检查 `~/.drawio-skill/styles/` 中任何有 `"default": true` 的文件。如果找到 → 活动预设 = 那个。
- 否则 → 无活动预设；沿用内置颜色/形状/连接线约定完成工作流其余部分。

从 `~/.drawio-skill/styles/<name>.json` 加载预设 JSON，回退到 `<this-skill-dir>/styles/built-in/<name>.json`。如果命名预设两处都不存在，告诉用户名称未知，列出可用预设（用户目录 + 内置），然后停止 — 不要静默回退到默认。

预设加载成功后，在回复第一行提及："*Using preset `<name>` (confidence: `<level>`).*" 有关预设如何改变颜色/形状/连接线/字体的决策，见下方 **Applying a preset** 小节。

1. **检查依赖** — 验证 `draw.io --version` 成功；记录平台以使用正确 CLI 路径
2. **规划** — 识别形状、关系、布局（LR 或 TB）、按层级分组
3. **生成** — 将 `.drawio` XML 文件写入磁盘。默认输出目录是 `docs/drawio/`（不存在则自动创建）；如果用户指定了输出路径或目录（如 `./artifacts/`、`docs/images/`），使用那个 — 先 `mkdir -p` 目标目录。在步骤 4 和 7 的 PNG/SVG/PDF 导出中应用相同的目录选择。
4. **导出草稿** — 运行 CLI 生成预览 PNG。**此步不要传 `-e`** — 它添加的嵌入 `zTXt mxGraphModel` 块会导致 vision API（包括 Claude）在步骤 5 返回 400 "Could not process image"。将清洁预览保存为 `<name>.png`（单扩展名）。嵌入仅用于最终导出（步骤 7）。
5. **自检** — 使用 agent 内置的 vision 能力读取导出的 PNG，在展示用户前捕获明显问题并自动修复（需要支持 vision 的模型如 Claude Sonnet/Opus）。如果读取 PNG 返回 400 / "Could not process image" 错误，几乎肯定是误用了 `-e` 导出 — 去掉 `-e` 重新导出并重试一次。如果仍然失败，跳过自检并继续步骤 6。
6. **审核循环** — 向用户展示图片，收集反馈，应用精准的 XML 编辑，重新导出，重复直到批准
7. **最终导出** — 将批准版本重新导出为所有请求的格式。此处使用 `-e`（PNG/SVG/PDF）使交付物在 draw.io 中保持可编辑；保存为 `<name>.drawio.png` 表示嵌入了 XML。**对于带 `-e` 的 PNG，立即运行 `python3 <this-skill-dir>/scripts/repair_png.py <name>.drawio.png`** — draw.io 的 CLI 在 `-e` PNG 输出中截断 IEND 块（缺 8 字节），产生 vision API 和严格 PNG 解码器拒绝的损坏文件（issue #8）。报告文件路径。

### 步骤 5：自检

导出草稿 PNG 后，使用 agent 的 vision 能力（如 Claude 的图像输入）读取图像，在展示用户前检查以下问题。如果 agent 不支持 vision，跳过自检直接展示 PNG。

**重要：** 此处读取的草稿 PNG 必须是不带 `-e` 导出的。Draw.io 的 `-e` 标志发出的 PNG 有截断的 IEND 块（缺 8 字节 type+CRC），Anthropic vision API 会以 400 "Could not process image" 拒绝（issue #8）。预览步骤最简单的修复是完全不加 `-e`；步骤 7 的最终导出保持 `-e` 并运行修复脚本。如果在此看到 400 错误，去掉 `-e` 重新导出并重试一次；如果因其他原因仍然失败，跳过自检继续步骤 6。

| 检查项 | 查找内容 | 自动修复动作 |
|-------|-----------------|-----------------|
| 形状重叠 | 两个或多个形状叠在一起 | 将形状移开 ≥200px |
| 标签被裁剪 | 文本在形状边界处被截断 | 增大形状宽/高以容纳标签 |
| 连接缺失 | 箭头视觉上未连接到形状 | 验证 `source`/`target` id 与现有单元格匹配 |
| 画布外形状 | 形状在负坐标或远离主群组 | 移至主群组附近的正坐标 |
| 连接线穿过形状 | 连接线/箭头视觉上穿过无关形状 | 添加路径点（`<Array as="points">`）绕开形状，或增大形状间距 |
| 连接线堆叠 | 多条连接线重叠在同一路径上 | 在形状周长上分布入口/出口点（使用不同的 exitX/entryX 值） |

- 最多 **2 轮自检** — 如果 2 次修复后仍有问题，直接展示给用户
- 每次修复后重新导出并重新读取新 PNG

### 步骤 6：审核循环

自检后，向用户展示导出的图片并收集反馈。

**精准编辑规则** — 对于每类反馈，应用最小的 XML 更改：

| 用户请求 | XML 编辑动作 |
|-------------|-----------------|
| 改变 X 的颜色 | 按 `value` 匹配找到 `mxCell`，更新 `style` 中的 `fillColor`/`strokeColor` |
| 添加新节点 | 追加新的 `mxCell` 顶点，使用下一个可用 `id`，定位在相关节点附近 |
| 删除节点 | 删除 `mxCell` 顶点及任何 `source`/`target` 匹配的连接线 |
| 移动形状 X | 更新匹配 `mxCell` 的 `mxGeometry` 中的 `x`/`y` |
| 调整形状 X 大小 | 更新匹配 `mxCell` 的 `mxGeometry` 中的 `width`/`height` |
| 添加从 A 到 B 的箭头 | 追加新的 `mxCell` 连接线，`source`/`target` 匹配 A 和 B 的 id |
| 改变标签文本 | 更新匹配 `mxCell` 的 `value` 属性 |
| 改变布局方向 | **完全重新生成** — 用新方向重建 XML |

**规则：**
- 单元素修改：原地编辑现有 XML — 保留之前迭代的布局调优
- 布局级修改（如交换 LR↔TB、"重新开始"）：重新生成完整 XML
- 每次迭代覆盖同一 `{name}.png`（不带 `-e`）— 不要创建 `v1`、`v2`、`v3` 文件。`-e` 仅用于步骤 7 的最终导出。
- 应用编辑后，重新导出并展示更新后的图片
- 循环直到用户说 approved / done / LGTM
- **安全阀：** 5 轮迭代后，建议用户打开 draw.io 桌面中的 `.drawio` 文件进行精细调整

### 步骤 7：最终导出

用户批准后：
- 导出为所有请求的格式（PNG、SVG、PDF、JPG）— 未指定则默认 PNG
- 报告 `.drawio` 源文件和导出图片的文件路径
- **自动启动：** 提议在 draw.io 桌面中打开 `.drawio` 文件进行精细调整 — `open diagram.drawio`（macOS）、`xdg-open`（Linux）、`start`（Windows）
- 确认文件已保存并可用

## 样式预设

**样式预设**是一个命名 JSON 文件，捕获用户的视觉偏好（调色板、形状、字体、连接线）。活动时，它完全替代此 skill 中的内置颜色/形状约定。

**lookup 顺序**（SKILL.md 步骤 0.5 解析预设名称时）：
1. `~/.drawio-skill/styles/<name>.json` — 用户预设（`git pull` 后保留）
2. `<this-skill-dir>/styles/built-in/<name>.json` — 附带的内置（`default`、`corporate`、`handdrawn`）

所有文件操作前始终将用户提供的名称转为小写 — schema 强制小写。

**其他一切** — Learn 流程（从文件提取预设）、管理操作（list/default/delete/rename）、应用规则（颜色查找、形状关键字、连接线、字体、extras、与图表类型预设的交互）和验证 — 阅读 `references/style-presets.md`。仅在用户调用那些流程或需要将活动预设应用于当前生成时才需要。

## Draw.io XML 结构

### 文件骨架

```xml
<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="drawio" version="26.0.0">
  <diagram name="Page-1">
    <mxGraphModel>
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- user shapes start at id="2" -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**规则：**
- `id="0"` 和 `id="1"` 是必需的根单元格 — 绝不省略
- 用户形状从 `id="2"` 开始，顺序递增
- 所有形状有 `parent="1"`（在容器内除外 — 那就用容器的 id）
- 所有文本在 style 中使用 `html=1` 以正确渲染
- **XML 注释中绝不使用 `--`** — 违反 XML 规范会导致解析错误
- 属性值中的特殊字符转义：`&amp;`、`&lt;`、`&gt;`、`&quot;`
- **标签中的多行文本：** 在 `value` 属性内使用 `&#xa;` 换行（不是字面 `\n`）。例如：`value="第1行&#xa;第2行"`

### 形状类型（顶点）

| Style 关键字 | 用于 |
|--------------|---------|
| `rounded=0` | 普通矩形（默认） |
| `rounded=1` | 圆角矩形 — 服务、模块 |
| `ellipse;` | 圆形/椭圆 — 开始/结束、数据库 |
| `rhombus;` | 菱形 — 决策点 |
| `shape=mxgraph.aws4.resourceIcon;` | AWS 图标 |
| `shape=cylinder3;` | 圆柱 — 数据库 |
| `swimlane;` | 带标题栏的组/容器 |

### 必需属性

```xml
<!-- 矩形 / 圆角框 -->
<mxCell id="2" value="Label" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="160" height="60" as="geometry" />
</mxCell>

<!-- 圆柱（数据库） -->
<mxCell id="3" value="DB" style="shape=cylinder3;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;" vertex="1" parent="1">
  <mxGeometry x="350" y="100" width="120" height="80" as="geometry" />
</mxCell>

<!-- 菱形（决策） -->
<mxCell id="4" value="Check?" style="rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;" vertex="1" parent="1">
  <mxGeometry x="100" y="220" width="160" height="80" as="geometry" />
</mxCell>
```

### 容器和组

对于带嵌套元素的架构图，使用 draw.io 的父子包容 — 不要只是把形状放在大形状上面。

| 类型 | Style | 何时使用 |
|------|-------|-------------|
| **Group**（不可见） | `group;pointerEvents=0;` | 无需视觉边框，容器无连接 |
| **Swimlane**（有标题） | `swimlane;startSize=30;` | 容器需要可见标题栏，或容器本身有连接 |
| **自定义容器** | 在任意形状上添加 `container=1;pointerEvents=0;` | 任何作为容器但自身无连接的形状 |

**关键规则：**
- 在不应捕获子级之间连接的容器样式中添加 `pointerEvents=0;`
- 子级设置 `parent="containerId"` 并使用**相对于容器**的坐标

```xml
<!-- Swimlane 容器 -->
<mxCell id="svc1" value="User Service" style="swimlane;startSize=30;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
  <mxGeometry x="100" y="100" width="300" height="200" as="geometry"/>
</mxCell>
<!-- 容器内的子级 — 坐标相对于父级 -->
<mxCell id="api1" value="REST API" style="rounded=1;whiteSpace=wrap;html=1;" vertex="1" parent="svc1">
  <mxGeometry x="20" y="40" width="120" height="60" as="geometry"/>
</mxCell>
<mxCell id="db1" value="Database" style="shape=cylinder3;whiteSpace=wrap;html=1;" vertex="1" parent="svc1">
  <mxGeometry x="160" y="40" width="120" height="60" as="geometry"/>
</mxCell>
```

### 连接线（edge）

**关键：** 每个 edge `mxCell` 必须包含 `<mxGeometry relative="1" as="geometry" />` 子元素。自闭合 edge 单元格（`<mxCell ... edge="1" ... />`）**无效**且不会渲染。始终使用展开形式。

```xml
<!-- 方向箭头 — 始终包含 rounded、orthogonalLoop、jettySize 以获得清洁路由 -->
<mxCell id="10" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;" edge="1" parent="1" source="2" target="3">
  <mxGeometry relative="1" as="geometry" />
</mxCell>

<!-- 带标签的箭头 + 显式入口/出口点以控制方向 -->
<mxCell id="11" value="HTTP/REST" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;" edge="1" parent="1" source="2" target="4">
  <mxGeometry relative="1" as="geometry" />
</mxCell>

<!-- 带路径点的箭头 — 当连接线必须绕开其他形状时使用 -->
<mxCell id="12" value="" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;" edge="1" parent="1" source="3" target="5">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="500" y="50" />
    </Array>
  </mxGeometry>
</mxCell>
```

**连接线样式规则：**
- **动画连接线：** 在任意连接线样式中添加 `flowAnimation=1;` 以显示沿箭头移动的点的动画。在 SVG 导出和 draw.io 桌面中有效 — 适合数据流和流水线图表。例如：`style="edgeStyle=orthogonalEdgeStyle;flowAnimation=1;rounded=1;..."`
- **始终**包含 `rounded=1;orthogonalLoop=1;jettySize=auto` — 这些启用避免重叠的智能路由
- 当节点有 2+ 连接时，在每条连接线上固定 `exitX/exitY/entryX/entryY` — 在线之间分配形状周长
- 当连接线必须绕开中间形状时，添加 `<Array as="points">` 路径点
- **为箭头留出空间：** 最后一弯和目标形状之间的最终直线段必须 ≥20px。如果太短，箭头会重叠弯曲看起来断裂。通过增加节点间距或添加显式路径点来修复

### 在形状上分布连接

当多条连接线连接到同一形状时，分配不同的入口/出口点以防止堆叠：

| 位置 | exitX/entryX | exitY/entryY | 用于 |
|----------|-------------|-------------|----------|
| 顶部中心 | 0.5 | 0 | 连接到上方的节点 |
| 左上 | 0.25 | 0 | 从顶部数第 2 个连接 |
| 右上 | 0.75 | 0 | 从顶部数第 3 个连接 |
| 右侧中心 | 1 | 0.5 | 连接到右侧的节点 |
| 底部中心 | 0.5 | 1 | 连接到下方的节点 |
| 左侧中心 | 0 | 0.5 | 连接到左侧的节点 |

**规则：** 如果一个形状在一侧有 N 个连接，均匀分布（例如，底部 3 个连接 → exitX = 0.25、0.5、0.75）

### 调色板（fillColor / strokeColor）

*仅在无预设活动时使用（见上方 "Applying a preset"）。*

| 颜色名 | fillColor | strokeColor | 用于 |
|-----------|-----------|-------------|---------|
| 蓝 | `#dae8fc` | `#6c8ebf` | 服务、客户端 |
| 绿 | `#d5e8d4` | `#82b366` | 成功、数据库 |
| 黄 | `#fff2cc` | `#d6b656` | 队列、决策 |
| 橙 | `#ffe6cc` | `#d79b00` | 网关、API |
| 红/粉 | `#f8cecc` | `#b85450` | 错误、告警 |
| 灰 | `#f5f5f5` | `#666666` | 外部/中性 |
| 紫 | `#e1d5e7` | `#9673a6` | 安全、认证 |

### 布局技巧

**间距 — 随复杂度缩放：**

| 图表复杂度 | 节点数 | 水平间距 | 垂直间距 |
|-------------------|-------|----------------|--------------|
| 简单 | ≤5 | 200px | 150px |
| 中等 | 6–10 | 280px | 200px |
| 复杂 | >10 | 350px | 250px |

**路由走廊：** 在形状行/列之间留出约 80px 的额外空走廊，让连接线在不走穿形状的情况下路由。永远不要把形状放在连接线需要穿过的间隙中。

**网格对齐：** 将所有 `x`、`y`、`width`、`height` 值对齐到 **10 的倍数** — 这确保形状在 draw.io 默认网格上干净对齐，也便于手动编辑。

**通用规则：**
- 分配 x/y 坐标前先规划网格 — 先在纸上/脑海中勾勒节点位置
- 将相关节点分到同一水平或垂直带
- 使用 `swimlane` 单元格进行带可见边框的逻辑分组
- 将重度连接的"中心"节点放在中央，使连接线向外辐射而非交叉
- 要强制垂直连接，在连接线上显式固定入口/出口点：
  `exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0`
- 始终将子节点与父节点居中对齐（相同的中心 x）以避免对角线路由
- **事件总线模式**：将 Kafka/总线节点放在**服务行的中心**，而不是下方 — 两侧的服务可以用短水平箭头到达它（左侧 `exitX=1`、右侧 `exitX=0`），消除所有线条交叉
- 水平连接（`exitX=1` 或 `exitX=0`）不会穿过同一行中的垂直节点；用于对等连接和发布连接

**避免连接线穿过形状：**
- 在最终确定坐标前，脑海中追踪每条连接线的路径 — 如果必须穿过无关形状，要么移动形状要么添加路径点
- 对于树/层次布局：将节点分配到层（行），仅在相邻层之间连接以最小化交叉
- 对于星形/中心布局：将中心放置在中间，卫星围绕它 — 连接线保持短且径向
- 当连接线必须跨越多行/列时，沿外侧走廊路由，而非穿过图表中间

## 导出

### 命令

**两个**导出模式：

- **预览 / 自检**（工作流步骤 4）— 不用 `-e`。输出 `diagram.png`。用于 vision 自检；此处使用 `-e` 会触发 vision API 的 400 "Could not process image" 错误（issue #8）。
- **最终 / 交付物**（步骤 7）— 传 `-e`。输出 `diagram.drawio.png`。嵌入的 XML 使文件在 draw.io 中保持可编辑。

```bash
# 预览 PNG（步骤 4 使用，在自检前）— 不用 -e
draw.io -x -f png -s 2 -o diagram.png input.drawio

# 最终 PNG（步骤 7，用户批准后）— 用 -e，双扩展名
draw.io -x -f png -e -s 2 -o diagram.drawio.png input.drawio

# Linux（无头 — 需要 xvfb-run；服务器上加 HOME 和 --disable-gpu）
export HOME=${HOME:-/tmp}
xvfb-run -a --server-args="-screen 0 1280x1024x24" \
  draw.io -x -f png -e -s 2 -o diagram.drawio.png input.drawio --disable-gpu
# 以 root 运行（CI / Docker）？在最后追加 --no-sandbox（放在前面会让 drawio 把它当作输入文件名）

# Windows（--disable-gpu 避免 Chromium 缓存权限错误）
"$DRAWIO" -x -f png -e -s 2 -o diagram.drawio.png input.drawio --disable-gpu

# SVG 导出（最终 — -e 安全；SVG 是文本）
draw.io -x -f svg -e -o diagram.svg input.drawio

# PDF 导出（最终）
draw.io -x -f pdf -e -o diagram.pdf input.drawio

# 自定义输出目录（如 CI artifacts 目录）— 先创建，导出到那里
mkdir -p ./artifacts && draw.io -x -f png -e -s 2 -o ./artifacts/diagram.drawio.png input.drawio
```

### 导出后 PNG 修复（`-e` PNG 导出后必需）

draw.io CLI 在发出 `-e` PNG 时截断 IEND 块 — 文件以 4 字节 IEND 长度字段结束，但 `IEND` 类型 + CRC（8 字节）缺失。结果：vision API 返回 400 "Could not process image"，严格 PNG 解码器报错。SVG/PDF 不受影响。

每次 `-e` PNG 导出后立即运行：

```bash
python3 <this-skill-dir>/scripts/repair_png.py diagram.drawio.png
```

脚本的 `endswith(IEND)` guard 使其在 draw.io 在上游修复 bug 后成为空操作 — 可以无条件安全运行。

**关键标志：**
- `-x` — 导出模式（必需）
- `-f` — 格式：`png`、`svg`、`pdf`、`jpg`
- `-e` — 在输出中嵌入图表 XML（PNG、SVG、PDF）— 导出的文件在 draw.io 中保持可编辑。**步骤 5 自检用的预览 PNG 跳过** — `-e` PNG 有 vision API 拒绝的截断 IEND 块（issue #8）。最终 PNG 导出保留 `-e` 并运行 `scripts/repair_png.py`（见导出后 PNG 修复）。SVG/PDF 不受影响。
- `-s` — 缩放：`1`、`2`、`3`（PNG 推荐 2）
- `-o` — 输出文件路径；接受任何目录（如 `./artifacts/diagram.drawio.png`）— 先 `mkdir -p` 目标目录。嵌入时使用 `.drawio.png` 双扩展名。
- `-b` — 图表周围边框宽度（默认：0，建议 10）
- `-t` — 透明背景（仅 PNG）
- `--page-index 0` — 导出特定页面（默认：全部）

### 浏览器后备（无需 CLI）

当 draw.io 桌面 CLI 不可用时，生成客户端查看器 URL：

```bash
python3 <this-skill-dir>/scripts/encode_drawio_url.py input.drawio
```

打印 `https://viewer.diagrams.net/...` URL，图表 XML 经 deflate 压缩并 base64 编码到 URL 片段中。片段（`#` 之后）从不发送到服务器，所以没有内容上传 — 图表在客户端打开用于查看和编辑。当用户无法安装桌面应用时有用。

### 后备链

当工具不可用时，优雅降级：

| 场景 | 行为 |
|----------|----------|
| draw.io CLI 缺失、有 Python | 使用浏览器后备（diagrams.net URL） |
| draw.io CLI 缺失、无 Python | 仅生成 `.drawio` XML；指示用户手动在 draw.io 桌面或 diagrams.net 打开 |
| Vision 不可用于自检 | 跳过自检（步骤 5）；直接向用户展示导出的 PNG |
| 导出失败（Chromium/显示问题） | 在 Linux 上重试 `xvfb-run -a`；如果仍然失败，交付 `.drawio` XML 并建议手动导出 |
| Linux 服务器导出失败（无头） | 按顺序尝试：(1) `xvfb-run -a`, (2) 如果是 root 在最后追加 `--no-sandbox`, (3) 加 `--disable-gpu`, (4) `export HOME=/tmp`, (5) 安装 apt 依赖（`libgtk-3-0 libnotify4 libnss3 libgbm1 libasound2t64` 等）, (6) 后备 [tomkludy/drawio-renderer](https://hub.docker.com/r/tomkludy/drawio-renderer) Docker（REST API 无头导出） |

### 检查 draw.io 是否在 PATH 中

```bash
# Linux — 先尝试短命令
if command -v draw.io &>/dev/null; then
  DRAWIO="draw.io"

# Windows — 自动检测常见安装路径
elif [ -f "C:/Program Files/draw.io/draw.io.exe" ]; then
  DRAWIO="C:/Program Files/draw.io/draw.io.exe"
elif [ -f "C:/Program Files (x86)/draw.io/draw.io.exe" ]; then
  DRAWIO="C:/Program Files (x86)/draw.io/draw.io.exe"
elif [ -f "$LOCALAPPDATA/draw.io/draw.io.exe" ]; then
  DRAWIO="$LOCALAPPDATA/draw.io/draw.io.exe"
elif [ -f "D:/Program Files/draw.io/draw.io.exe" ]; then
  DRAWIO="D:/Program Files/draw.io/draw.io.exe"
elif [ -f "D:/opt/tool/draw.io/draw.io.exe" ]; then
  DRAWIO="D:/opt/tool/draw.io/draw.io.exe"
else
  echo "draw.io not found — install from https://github.com/jgraph/drawio-desktop/releases"
fi
```

## 常见错误

当输出有问题（导出失败、vision 拒绝 PNG、布局损坏、连接线错误路由）时，参阅 `references/troubleshooting.md` 的逐行错误 → 修复对照表。

## 图表类型预设

当用户请求特定图表类型时，读取 `references/diagram-types.md` 获取匹配的预设（形状、连接线、布局方向）。按用户措辞选择：

| 用户说 | `references/diagram-types.md` 中的章节 |
|---|---|
| "ER diagram"、"schema diagram"、"data model" | ERD |
| "UML class diagram"、"class diagram" | UML 类 |
| "sequence diagram"、"interaction diagram"、"lifeline" | 序列 |
| "architecture"、"system diagram"、"service diagram" | 架构 |
| "neural network"、"model architecture"、"ML diagram"、"deep learning" | ML / 深度学习模型 |
| "flowchart"、"decision tree"、"process flow" | 流程图 |

图表类型预设设置**结构性** style 关键字。如果用户样式预设也活动（见 `## Style Presets`），保留结构性关键字并在其上叠加颜色/字体/连接线/extras — 阅读 `references/style-presets.md` → "Interaction with diagram-type presets" 了解合并规则。