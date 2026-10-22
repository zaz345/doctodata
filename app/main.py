"""DocToData — 上传文档 → LLM 抽字段 → 表格 / 图表 / Excel。

D1：/extract 跑通。
D2：三页面 UI（/ui）、样例下载、原文件预览、Excel 导出。
"""

import io
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from .extract import fetch_url_text, guess_kind, html_to_text, pdf_to_text
from .llm import extract_fields_from_image, extract_fields_from_text

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "samples"
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="DocToData", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 内存存储：doc_id -> 结果（含原始文件字节，供结果页预览）。重启即清空。
RESULTS: dict = {}

# 客户端给的 content-type 不可靠（浏览器对无 type 的 File 会发 octet-stream），
# 一律按扩展名推导，否则 GLM 视觉接口会报 1210 图片格式错误。
IMAGE_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def image_mime_for(filename: str, fallback: str = "") -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in IMAGE_MIME_BY_EXT:
        return IMAGE_MIME_BY_EXT[ext]
    if fallback in IMAGE_MIME_BY_EXT.values():
        return fallback
    return "image/png"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return RedirectResponse(url="/ui/")


@app.post("/extract")
async def extract(
    file: UploadFile | None = File(None),
    url: str | None = Form(None),
    hint: str = Form(""),  # "invoice" | "listing" | ""(自动)
):
    """上传文件或粘贴链接，返回抽出的字段 JSON。"""
    t0 = time.time()
    content = b""
    mime = ""
    try:
        if file is not None:
            content = await file.read()
            kind = guess_kind(file.content_type, file.filename or "")
            mime = (file.content_type or "").split(";")[0]
            if kind == "pdf":
                mime = "application/pdf"
                text = pdf_to_text(content)
                if not text:
                    raise HTTPException(400, "这份 PDF 没有文字层（可能是扫描件），当前 demo 只支持文字版 PDF 和图片。")
                result = extract_fields_from_text(text, hint)
            elif kind == "image":
                mime = image_mime_for(file.filename, mime)
                result = extract_fields_from_image(content, mime, hint)
            elif kind == "html":
                result = extract_fields_from_text(html_to_text(content.decode("utf-8", "ignore")), hint)
            else:
                raise HTTPException(400, f"不支持的文件类型: {file.content_type} / {file.filename}")
        elif url:
            text = fetch_url_text(url)
            if not text:
                raise HTTPException(400, "该网页抓不到正文。")
            result = extract_fields_from_text(text, hint)
        else:
            raise HTTPException(400, "请上传文件（file）或提供链接（url）。")
    except HTTPException:
        raise
    except RuntimeError as e:  # 缺 key 等
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(500, f"抽取失败: {e}")

    doc_id = uuid.uuid4().hex[:12]
    payload = {
        "doc_id": doc_id,
        "filename": file.filename if file else url,
        "mime": mime,
        "fields": result,
        "elapsed_sec": round(time.time() - t0, 2),
    }
    RESULTS[doc_id] = {**payload, "content": content, "mime": mime}
    return payload


@app.get("/results/{doc_id}")
def get_result(doc_id: str):
    if doc_id not in RESULTS:
        raise HTTPException(404, "结果不存在或服务已重启")
    r = RESULTS[doc_id]
    return {k: v for k, v in r.items() if k != "content"}


@app.get("/files/{doc_id}")
def get_file(doc_id: str):
    """结果页左侧预览：原样返回上传的文件。"""
    if doc_id not in RESULTS:
        raise HTTPException(404, "文件不存在或服务已重启")
    r = RESULTS[doc_id]
    if not r["content"]:
        raise HTTPException(404, "该文档来自链接，没有本地文件可预览")
    return StreamingResponse(io.BytesIO(r["content"]), media_type=r["mime"] or "application/octet-stream")


@app.get("/samples")
def list_samples():
    """示例文件清单（前端渲染成 3 张卡片）。"""
    items = []
    for p in sorted(SAMPLES_DIR.glob("*")):
        if p.suffix.lower() not in (".pdf", ".png", ".jpg", ".jpeg"):
            continue
        items.append({
            "name": p.name,
            "kind": "invoice" if p.stem.startswith("invoice") else "listing",
            "type": "pdf" if p.suffix.lower() == ".pdf" else "image",
            "url": f"/samples/{p.name}",
        })
    return items


@app.get("/samples/{name}")
def get_sample(name: str):
    p = (SAMPLES_DIR / name).resolve()
    if SAMPLES_DIR.resolve() not in p.parents or not p.exists():
        raise HTTPException(404, "示例不存在")
    media = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    return FileResponse(p, media_type=media.get(p.suffix.lower(), "application/octet-stream"))


EXPORT_HEADERS = {
    "invoice": ["doc_id", "filename", "invoice_number", "issue_date", "seller_name",
                "buyer_name", "currency", "total_amount", "tax_amount", "items_count"],
    "listing": ["doc_id", "filename", "title", "city", "district", "community",
                "price", "unit_price", "area_sqm", "layout", "floor", "orientation"],
}


@app.post("/export")
async def export_excel(request: Request):
    """前端把（可能编辑过的）字段 POST 回来，生成 xlsx。"""
    body = await request.json()
    docs = body.get("docs") or []
    if not docs:
        raise HTTPException(400, "没有可导出的数据")

    wb = Workbook()
    ws = wb.active
    ws.title = "Documents"

    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="2563EB")

    def write_row(sheet, values, bold=False):
        sheet.append(values)
        if bold:
            for cell in sheet[sheet.max_row]:
                cell.font = head_font
                cell.fill = head_fill

    # 主表：每份文档一行，列取所有文档字段的并集
    keys = []
    for d in docs:
        for k, v in (d.get("fields") or {}).items():
            if k != "items" and k not in keys:
                keys.append(k)
    cols = ["doc_id", "filename"] + [k for k in keys if k not in ("doc_id", "filename")]
    write_row(ws, cols, bold=True)
    for d in docs:
        f = d.get("fields") or {}
        row = []
        for c in cols:
            if c == "doc_id":
                row.append(d.get("doc_id", ""))
            elif c == "filename":
                row.append(d.get("filename", ""))
            elif c == "items_count":
                row.append(len(f.get("items") or []))
            else:
                row.append(f.get(c, ""))
        ws.append(row)

    for i, c in enumerate(ws[1], start=1):
        ws.column_dimensions[chr(64 + i)].width = max(12, min(28, len(str(c.value)) + 8))

    # 明细表：发票品目展开
    items_rows = []
    for d in docs:
        for it in ((d.get("fields") or {}).get("items") or []):
            items_rows.append([d.get("doc_id", ""), d.get("filename", ""), it.get("name", ""), it.get("amount", "")])
    if items_rows:
        ws2 = wb.create_sheet("Items")
        write_row(ws2, ["doc_id", "filename", "item_name", "amount"], bold=True)
        for r in items_rows:
            ws2.append(r)
        for col, w in zip("ABCD", (16, 28, 26, 14)):
            ws2.column_dimensions[col].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="doctodata_export.xlsx"'},
    )


# 前端单页：/ui/
app.mount("/ui", StaticFiles(directory=str(WEB_DIR), html=True), name="ui")
