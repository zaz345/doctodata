"""从上传的文件/URL 里抽出「可喂给 LLM 的内容」。

支持：
- PDF（有文字层的）：pdfplumber 抽文本
- 图片：返回字节，走视觉模型
- URL：抓网页、去 HTML 标签留正文
"""

import io
import re

import httpx
import pdfplumber

IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}


def guess_kind(content_type: str, filename: str) -> str:
    """返回 'pdf' | 'image' | 'html' | 'unknown'。"""
    ct = (content_type or "").split(";")[0].strip().lower()
    name = (filename or "").lower()
    if ct == "application/pdf" or name.endswith(".pdf"):
        return "pdf"
    if ct in IMAGE_MIMES or any(name.endswith(e) for e in (".png", ".jpg", ".jpeg", ".webp")):
        return "image"
    if ct.startswith("text/html") or name.endswith((".html", ".htm")):
        return "html"
    return "unknown"


def pdf_to_text(data: bytes) -> str:
    parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            parts.append(t)
    text = "\n".join(parts).strip()
    # pdfplumber 会把字距大的中文拆成「增 值 税」，去掉汉字之间的空白更可读
    text = re.sub(r"(?<=[\u4e00-\u9fff])[ \t]+(?=[\u4e00-\u9fff])", "", text)
    return text


def html_to_text(html: str) -> str:
    # demo 级别的去标签：够用就行
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;?", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()


def fetch_url_text(url: str) -> str:
    resp = httpx.get(url, timeout=20, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    ct = resp.headers.get("content-type", "")
    kind = guess_kind(ct, url)
    if kind == "pdf":
        return pdf_to_text(resp.content)
    return html_to_text(resp.text)
