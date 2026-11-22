---
name: design-check
description: 改完这个项目的 UI（web/ 或 _redesign/ 下的样式、结构、文案）之后跑一遍固定流水线：补丁链生成 JS → 拼单文件 → 自检 → 25 条功能回归 → 确定性设计检测器。Use when editing web/index.html, _redesign/parts, _redesign/shell.html, or _redesign/patches, or when the user asks 改界面 / 调样式 / 修设计问题.
---

# 设计改动流水线（DSH 版 impeccable 补位）

这个项目同时在用 Impeccable，但 DSH 没有 per-edit 自动 hook，所以"改完 UI 自己扫一遍"必须由这条流水线顶上。

## 铁律

- **不要直接改 `web/index.html`**（它是产物）。改 `_redesign/parts/*.css`、`_redesign/shell.html`，
  或新增 `_redesign/patches/NNNN-*.json`（JS 改动只能走补丁）。详见 `DESIGN.md` §10。
- **不要直接改 `_redesign/src/app.js`**：每次都由 `patch_js.py` 从 `ref/old-app.js` + 补丁链重建。
- 补丁 `old` 必须恰好出现一次；链断则整链不写（fail-closed），报错后查锚点而不是手改产物。

## 顺序

```powershell
cd D:\opencode\course-terminal
python _redesign\tools\patch_js.py      # 只在动了 JS 补丁时需要
python _redesign\tools\apply.py         # 自检 + 写 web/index.html（自检红先修）
```

跑起来验证（用隔离实例，别碰日常数据）：

```powershell
$env:LOCALAPPDATA = "$env:TEMP\qa-harness-data"
python app\main.py --no-window --port 8811

powershell -ExecutionPolicy Bypass -File _redesign\tools\cap.ps1 -Port 8811 -Smoke      # 25 条断言，必须 25/25
powershell -ExecutionPolicy Bypass -File _redesign\tools\cap.ps1 -Port 8811 -Out _redesign\shots\after
```

确定性检测器（对比度 / 结构 / AI 味规则；不需要 LLM）：

```powershell
& "C:\Users\LENOVO\.dsh\skills\impeccable\scripts\impeccable.cmd" detect "http://127.0.0.1:8811/" --viewport 1440x900
& "C:\Users\LENOVO\.dsh\skills\impeccable\scripts\impeccable.cmd" detect "http://127.0.0.1:8811/" --viewport 390x844
```

## 验收线（当前基线）

| 项 | 基线 |
|---|---|
| `cap.ps1 -Smoke` | **25/25 通过，0 未捕获异常，0 console.error** |
| `cap.ps1`（全 surface） | 24 个剧本 / 36 张，全绿 |
| `impeccable detect` 1440 | **0 条 `low-contrast`**；只剩 `side-tab`（目录引导线 + 卡片顶部发丝线，规则误报）与 `dark-glow`（品牌方块，有意为之） |
| 文字对比度 | 任何承载文字的配对 ≥ 4.5:1（大字 ≥ 3:1），见 `DESIGN.md` 的 Colors 段 |

出现新的 `low-contrast` = 这次改动引入了回归，先修再收工。
