# DocToData

上传 PDF / 图片 / 链接 → LLM 抽字段 → 表格 → 图表报告 → 一键导出 Excel。

销售 demo，不是产品。代码能跑就行。

## 跑起来

**双击 `run.bat`**，浏览器打开 <http://127.0.0.1:8642> —— 这就是给客户看的 UI（上传页 → 结果页 → 报告页）。
`http://127.0.0.1:8642/docs` 是接口文档（开发者用）。

本项目用**项目内独立 venv**（`.venv/`），不依赖系统环境，已建好。

**方式一：双击 `run.bat`**（或在本目录命令行执行 `.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8642`），
然后浏览器打开 <http://127.0.0.1:8642> —— 会自动跳到 `/docs` 接口文档页，点 `POST /extract` → `Try it out` → 选文件 → `Execute`，不敲任何命令。

**方式二：命令行直接测一份文件。** 注意：服务已经占住一个窗口，命令行测试要**另开一个 cmd 窗口**（`Win + R` → `cmd`），逐行粘贴：

```cmd
cd /d E:\WorkBuddy_WorkSpace\remoteEarn\DocToData
```

```cmd
.venv\Scripts\python.exe cli.py samples\invoice_01.pdf invoice
```

- 第一个参数是文件路径，`samples\` 下可换成 `listing_01.png` 等任意样例
- 第二个参数 `invoice` / `listing` 是可选提示（告诉模型文档类型）；**不写就自动判断**
- 用 `.venv\Scripts\python.exe` 全路径而不是裸 `python`：避免撞上 Windows 商店的假 python

依赖重装（换机器 / 删了 .venv）：

```bash
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## LLM key

已写入 Windows 用户环境变量 `LLM_API_KEY`（不落任何文件，`setx` 设置过就不用再管）。
换 key：`setx LLM_API_KEY "新key"`，然后重开终端。

免费模型：`glm-4-flash`（文本）、`glm-4v-flash`（视觉），默认已配好，不花钱。

默认接入智谱。想换任何 OpenAI 兼容供应商（deepseek 等）：

```bash
set LLM_BASE_URL=https://api.deepseek.com/v1
set LLM_MODEL=deepseek-chat
set LLM_API_KEY=...
```

## 接口

- `POST /extract` — multipart：`file`（pdf/png/jpg）或 `url`，可选 `hint`（invoice/listing）。返回 `{doc_id, filename, mime, fields, elapsed_sec}`。
- `GET /results/{doc_id}` — 取回结果（内存存储，重启即失）。
- `GET /files/{doc_id}` — 原文件（结果页预览用）。
- `GET /samples` / `GET /samples/{name}` — 示例清单 / 下载。
- `POST /export` — body `{"docs":[{doc_id, filename, fields}]}`，返回 xlsx（Documents 主表 + Items 明细）。
- `GET /health`
- 前端单页：`web/index.html`，挂在 `/ui/`，根路径 `/` 自动跳过去。Tailwind 和 Chart.js 已下载到 `web/vendor/`（jsdelivr 在国内不通，别改回 CDN）。

## 样例

`samples/` 下 10 份**全部虚构**的文件：5 份假发票 PDF + 5 份假房源截图 PNG。  
由 `scripts/make_samples.py` 生成，随机种子固定。

## 环境变量

| 变量                 | 默认           | 说明                          |
| ------------------ | ------------ | --------------------------- |
| `LLM_API_KEY`      | 无（必填才能真抽取）   | 智谱 key                      |
| `LLM_BASE_URL`     | 智谱 v4        | OpenAI 兼容地址                 |
| `LLM_MODEL`        | glm-4-flash  | 文本模型                        |
| `LLM_VISION_MODEL` | glm-4v-flash | 视觉模型                        |
| `LLM_MODE`         | 正常           | 设为 `mock` 返回固定假数据，仅用于验证接口链路 |

## 改了代码怎么上线

线上地址：`https://doctodata.onrender.com`（Render Blueprint，free plan，Singapore）。  
Render 监听 GitHub 仓库的 `main` 分支，**push 上去会自动重新部署**，不用点任何按钮。

**本机 `github.com:443`（HTTPS）不通，必须走 SSH**，仓库已配好：

```cmd
cd /d E:\WorkBuddy_WorkSpace\remoteEarn\DocToData
git add -A
git commit -m "说明这次改了什么"
set GIT_SSH_COMMAND=ssh -i C:/Users/Admin1/.ssh/id_ed25519 -o IdentitiesOnly=yes
git push origin main
```

> 不要改回 HTTPS 远程地址。SSH 走 `github.com:22` 是通的，HTTPS 的 443 被拦。  
> 推完等 1–2 分钟，Render 自动重建；改前端后可用 `curl -s https://doctodata.onrender.com/ui/index.html | grep 关键词` 确认新版已生效。

## 免费层的两个注意点

- **15 分钟无人访问会自动休眠**，下次访问有 30–50 秒冷启动。演示/录屏前先打开一次预热。
- **不要删除或暂停 Render 上的服务**。免费层不计时、空转到点自动睡，**不会产生费用**；但删除会让域名失效（交付物第一项就没了），暂停会让地址变成「服务已暂停」页面。

