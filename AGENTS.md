# AGENTS.md — drawio-skill

## 核心概念

这是一个 **skill 包**（不是应用项目），用于通过自然语言生成 `.drawio` 图表并导出为 PNG/SVG/PDF。

关键触发点：当用户描述涉及 3+ 组件、复杂数据流或关系时，**主动建议**生成图表（SKILL.md 会自动识别）。

**入口文件：** `skills/drawio-skill/SKILL.md` — 所有指令都在里面，不要偏离。

## 目录结构

```
skills/drawio-skill/
  SKILL.md              # 主指令文件（唯一必需）
  references/
    diagram-types.md    # 特定图表类型（ERD/UML/序列/ML等）的预设
    style-presets.md    # 样式预设的提取、应用、管理
    style-extraction.md # 从.drawio文件或图片提取样式的流程
    troubleshooting.md  # 常见错误 → 修复对照表
  scripts/
    repair_png.py       # -e PNG 导出后修复 IEND 截断问题（issue #8）
    encode_drawio_url.py # CLI 不可用时生成 diagrams.net 浏览器链接
  styles/built-in/      # 内置样式（default/corporate/handdrawn）
assets/                  # 示例图片（可安全删除以节省空间）
evals/                   # 触发评估数据
```

## 平台差异（必知）

| 平台 | 命令 | 额外步骤 |
|------|------|---------|
| macOS | `draw.io` 或完整路径 | Homebrew 安装后直接用 |
| Windows | 需用完整路径如 `"D:\opt\tool\draw.io\draw.io.exe"` | CLI 不在 PATH 时手动指定 |
| Linux | `draw.io` + `xvfb-run -a` | **不要用 snap 安装**（AppArmor 沙盒会崩溃）；root 运行时 `--no-sandbox` 放命令**最末尾**；导出失败先试 `--disable-gpu` 和 `export HOME=/tmp` |

## 导出步骤（关键）

导出分两个阶段，**不要混用**：

1. **预览阶段（Step 4）**：不用 `-e`，输出 `diagram.png`
   - 用途：用于 self-check（视觉检查）
   - `-e` PNG 会导致 vision API 返回 400（IEND 截断问题）

2. **最终交付（Step 7）**：用 `-e`，输出 `diagram.drawio.png`
   - 嵌入 XML，文件可在 draw.io 中继续编辑
   - **PNG 必须立即运行** `python3 scripts/repair_png.py diagram.drawio.png`
   - 不修会导致图片查看器和 vision API 报错

```bash
# 预览（Step 4）— 默认输出到 docs/drawio/
mkdir -p docs/drawio
draw.io -x -f png -s 2 -o docs/drawio/diagram.png input.drawio

# 最终交付（Step 7）
# 默认输出到 docs/drawio/；用户指定路径时使用用户路径
mkdir -p docs/drawio
draw.io -x -f png -e -s 2 -o docs/drawio/diagram.drawio.png input.drawio --disable-gpu
python3 skills/drawio-skill/scripts/repair_png.py docs/drawio/diagram.drawio.png
```

## 自检与迭代循环

- **自检（Step 5）**：用 vision 读 PNG，检查重叠/裁剪/缺失连接/出屏/边穿过形状。最多 2 轮自动修复。
- **用户反馈循环（Step 6）**：精准 XML 编辑，每次覆盖同一文件（不创建 v1/v2/v3）。5 轮后建议用户打开 draw.io 手动调整。
- **vision 模型不可用时**：跳过 Step 5，直接进入 Step 6 向用户展示。

## 样式预设规则

- 预设名称**始终转小写**后再用于文件路径
- 查找顺序：`~/.drawio-skill/styles/<name>.json` → `skills/drawio-skill/styles/built-in/<name>.json`
- 内置预设：`default`、`corporate`、`handdrawn`
- 预设激活时**完全替代**内置颜色/形状/边样式（不要混用）
- 管理操作（list/default/delete/rename）见 `references/style-presets.md`

## XML 陷阱（troubleshooting.md 核心）

| 错误 | 修复 |
|------|------|
| 边不渲染 | 展开形式：`<mxCell ...><mxGeometry relative="1" as="geometry" /></mxCell>`（禁止自闭合） |
| XML 注释含 `--` | 违法，换成单个连字符 |
| 标签换行用 `\n` | 用 `&#xa;` |
| 特殊字符未转义 | `&amp;` `&lt;` `&gt;` `&quot;` |
| shape 坐标非 10 的倍数 | 全部对齐到 10px |
| 箭头覆盖弯曲处 | 最后一段边 ≥20px 或加 waypoint |
| Linux 无显示 | `xvfb-run -a`，失败再加 `--disable-gpu` / `export HOME=/tmp` |

## 已知限制

- **vision 不可用的模型**：跳过自检，但导出流程不变
- **云图标**：仅支持基础 AWS；GCP/Azure/K8s 未收录
- **Linux snap 版本**：已知崩溃，不要用

## 更新检查

首次使用会检查上游新版本（24h 节流）。通知用户但不自动拉取。用户同意后运行 `git -C <skill-dir> pull --ff-only`。