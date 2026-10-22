# D4 交付：录屏分镜 + Portfolio 文案

> 线上地址：`https://doctodata.onrender.com`
> 录制日期：______ 
> 这份文件的目标：**明天照着做，不再做任何决策。**

---

## 0. 开录前必做（漏一条就废）

| # | 事项 | 为什么 |
|---|---|---|
| 1 | **先把本地改动推上线**，确认 Render 显示 `Live` | 预览高度 + 加载计时器两处改动还在本地，没推上去 |
| 2 | **预热 Render**：打开 URL 让它跑完一次冷启动（约 30–50s），再等它自己跑完一次抽取 | 免费层 15 分钟无访问就休眠。冷启动直接出现在视频开头 = 视频废掉 |
| 3 | 浏览器：桌面窗口 **1440×900 左右，缩放 100%**，全屏或最大化 | 客户在电脑上看 Portfolio |
| 4 | 关掉侧边栏书签栏（`Ctrl+Shift+B` 切无痕式干净界面）、关掉下载管理器弹窗 | 减少视觉噪音 |
| 5 | 清空浏览器下载栏 | 导出的 xlsx 要能被看到下载完成 |
| 6 | 手机充满电、连同一 WiFi——第 5 张截图要在真机上拍 | — |

**录屏工具**（选一个，别折腾）：Windows 自带 `Win + G` → 捕获 → 开始录制。零安装。

---

## 1. 30 秒录屏分镜（推荐版：手动点 2 份）

### 为什么不用 `?autodemo=report`

自动模式会跑 **3 份**（含一张 PNG），图片要走视觉模型，实测 **12 秒以上**，三份串下来 **28s+**，加上导出和片尾直奔 **40 秒**。超出 30 秒验收线。

推荐版本只用**两份文本 PDF**（各约 7 秒），卡在 25 秒左右，还留 5 秒容错。两份文档足够让报告页的柱状图有 2 根柱、趋势图有 2 个点——**1 份的话图是空的，很难看**。

### 分镜表

| 时间 | 画面 | 操作 | 旁白 / 字幕 |
|---|---|---|---|
| 0:00–0:03 | 首页（空的上传区 + 右侧 3 个样本） | 鼠标移到右侧 **Try a sample** 区，停在第一项 `invoice_01.pdf` | *Turn documents into spreadsheets. Let's try one.* |
| 0:03–0:10 | 加载页（转圈 + 实时计时器在跳） | **点击** `invoice_01.pdf`，手离开鼠标，让它跑 | *AI reads the file — no template to configure.* |
| 0:10–0:15 | 结果页（左：原 PDF；右：可编辑字段表；上：3 个统计数字） | 鼠标**沿着右侧字段表从上往下慢慢划一遍**，不要点 | *Fields come back structured. Anything wrong, you can edit it right here.* |
| 0:15–0:17 | 回到首页 | 点左上角 **← Upload another** | *Add a second one.* |
| 0:17–0:24 | 加载 → 第二份结果页 | 点 `invoice_02.pdf`，等待 | —（保持安静，让计时器自己走） |
| 0:24–0:26 | 结果页 | 点右上 **View report →** | *Batch view.* |
| 0:26–0:29 | 报告页（两张图：金额柱状图 + 金额趋势线） | 鼠标从左图画到右图 | *Charts across all documents.* |
| 0:29–0:32 | 报告页 → 浏览器下载栏出现 xlsx | 点 **Export to Excel**（绿色按钮） | *One click to Excel.* |

**收尾**：停在下载栏明显位置约 1 秒，停录。

### 三条纪律

1. **等待时不要动鼠标**。7 秒的加载是全片最有说服力的部分，乱晃会显得卡顿焦虑。
2. **不要解说中间那次等待**（0:17–0:24）。留白比废话强。
3. **一条过**。只要 helium 没错、导出成功，就不要重录。第二条永远不如第一条。

### 备选：想省事就用自动版

URL 换成 `https://doctodata.onrender.com/ui/?autodemo=report`，打开后**完全不用操作**，它自己跑完三份并直接进报告页，你只需要在最后点一下 Export。代价是**约 38–40 秒**。

> 判断：如果要严格卡 30 秒验收 → 用手动版。如果更怕手抖点错 → 用自动版，40 秒也能放进 Portfolio（Upwork 不校验时长）。**我推荐手动版**，因为它还顺带演示了"上传第二份"这个真实操作，客户更信。

---

## 2. Portfolio 文案（英文）

### 主版本（推荐，正文约 155 词）

**Title**
```
DocToData — Turn Invoices & Listings into Clean Spreadsheets
```

**Overview**
```
Most teams still retype numbers out of PDFs by hand. DocToData removes that step.

Drop in a PDF, an image, or a link to a page, and it returns structured fields you
can review, correct, and export — no templates to set up, and no per-document
configuration.

What it does
• Accepts PDFs, images (PNG/JPG), and page URLs
• Reads each document with an LLM and returns JSON — totals, dates, counterparties,
  and line items
• Side-by-side review: the original file on the left, editable fields on the right,
  so a human stays in the loop before anything reaches a spreadsheet
• Batch report with charts once more than one document is processed
• One-click Excel export: a summary sheet plus an item-level breakdown, both formatted

Built as a single deployable service: Python + FastAPI backend, OpenAI-compatible
LLM layer (swap the provider with one environment variable), openpyxl for Excel
export, and a lightweight HTML front end. No database, no login, no user data stored.

Live demo: https://doctodata.onrender.com
```

**Skills / tags**
```
Python · FastAPI · LLM integration · OpenAI API · REST API design ·
Document parsing (PDF) · OCR-free extraction via vision models ·
openpyxl / Excel automation · HTML + Tailwind + Chart.js · REST → JSON schema
design · Third-party API integration · Web scraping
```

**Role**
```
Solo build — architecture, backend, UI, and deployment.
```

---

### 短版本（字数受限时用，约 60 词）

```
DocToData turns invoices and property listings into clean spreadsheets. Upload a
PDF, an image, or a link; an LLM extracts the fields — totals, dates, parties,
line items — and you review them side by side against the original file before
exporting to Excel with one click. Built on Python + FastAPI with an
OpenAI-compatible LLM layer, so the model is swappable by config. No templates,
no database, no login.

Live demo: https://doctodata.onrender.com
```

---

### 三条用词纪律（别在最后一刻改坏）

1. **不写准确率数字**。"99% accurate" 这种你我都没测过，一旦客户追问就穿帮。文案里全程用"extracts fields"，不用"accurately extracts"。
2. **不写 OCR**。技术上走的是**视觉大模型**（vision model），不是传统 OCR。写成 OCR 会被懂行的客户看出外行。
3. **不写 batch size / 吞吐量**。后台是串行抽取、内存存储，没有队列。文案里"batch report"指的是**界面上的多文档汇总视图**，不是"批量处理几千份"。这个边界别踩。

### Portfolio 配图要求

5 张，顺序建议： **首页 → 结果页 → 报告页 → 导出的 Excel → 手机端**。

第 4 张（Excel）要**打开两个 sheet 的其中之一并截到图**——空的文件预览截图没有说服力。第 5 张用真手机打开 `https://doctodata.onrender.com/ui/` 后截屏。

---

## 3. 明天收工判定

| 交付物 | 完成标准 |
|---|---|
| 部署 URL | 公网可开、冷启动后能抽出字段 |
| 录屏 | 约 30 秒、能看完"上传→字段→报告→导出"四步 |
| 5 张截图 | 首页、结果页、报告页、Excel、手机端 |
| Portfolio 文案 | 上面英文版已粘进 Upwork Portfolio 条目 |

**四样齐了就停。** 不要再改 UI、不要再加功能、不要再优化。
