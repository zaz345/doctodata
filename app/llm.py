"""LLM 调用层：OpenAI 兼容接口，通过环境变量切换供应商。

环境变量：
  LLM_API_KEY   — API key（必填才能用真实抽取）
  LLM_BASE_URL  — OpenAI 兼容 base url，默认智谱 https://open.bigmodel.cn/api/paas/v4
  LLM_MODEL     — 文本模型，默认 glm-4-flash（免费）
  LLM_VISION_MODEL — 视觉模型，默认 glm-4v-flash（免费）
  LLM_MODE      — "mock" 时返回固定假数据，只用于验证链路，不算真抽取
"""

import base64
import json
import os
import re

from openai import OpenAI

BASE_URL = os.getenv("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
MODEL = os.getenv("LLM_MODEL", "glm-4-flash")
VISION_MODEL = os.getenv("LLM_VISION_MODEL", "glm-4v-flash")

SYSTEM_PROMPT = (
    "You are a document field extraction engine. "
    "Given the text of a document, extract its key fields and reply with a "
    "single JSON object and nothing else. "
    "Use null for fields that are not present. Do not invent values."
)

INVOICE_FIELDS = {
    "doc_type": "invoice",
    "invoice_number": "发票号码",
    "issue_date": "开票日期 YYYY-MM-DD",
    "seller_name": "销售方名称",
    "buyer_name": "购买方名称",
    "currency": "币种",
    "total_amount": "价税合计（数字）",
    "tax_amount": "税额（数字）",
    "items": [{"name": "品名", "amount": "金额（数字）"}],
}

LISTING_FIELDS = {
    "doc_type": "listing",
    "title": "房源标题",
    "city": "城市",
    "district": "区县",
    "community": "小区名",
    "price": "总价（数字，单位：万）",
    "unit_price": "单价（数字，元/平米）",
    "area_sqm": "面积（数字，平米）",
    "layout": "户型，如 2室1厅",
    "floor": "楼层描述",
    "orientation": "朝向",
}


def _mock_result(kind: str) -> dict:
    if kind == "invoice":
        return {
            "doc_type": "invoice",
            "invoice_number": "MOCK-0001",
            "issue_date": "2026-10-01",
            "seller_name": "Mock Seller Co.",
            "buyer_name": "Mock Buyer Co.",
            "currency": "CNY",
            "total_amount": 11300.0,
            "tax_amount": 1300.0,
            "items": [{"name": "Mock item", "amount": 10000.0}],
        }
    return {
        "doc_type": "listing",
        "title": "Mock Listing",
        "city": "北京",
        "district": "海淀区",
        "community": "Mock 小区",
        "price": 500.0,
        "unit_price": 50000.0,
        "area_sqm": 100.0,
        "layout": "2室1厅",
        "floor": "中层/6层",
        "orientation": "南北",
    }


def _parse_json(text: str) -> dict:
    """从模型输出里抠出 JSON（容忍 markdown 代码块包裹）。"""
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"LLM did not return JSON: {text[:200]}")
    return json.loads(m.group(0))


def _client() -> OpenAI:
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key:
        raise RuntimeError("LLM_API_KEY 未设置。请设置智谱免费 key（见 README）。")
    return OpenAI(api_key=api_key, base_url=BASE_URL)


def extract_fields_from_text(text: str, hint: str = "") -> dict:
    """文本（PDF 抽出的 / 网页扒的）→ 字段 JSON。hint 为空则自动判类型。"""
    if os.getenv("LLM_MODE", "") == "mock":
        return _mock_result(hint or "invoice")

    client = _client()
    if hint in ("invoice", "listing"):
        field_spec = INVOICE_FIELDS if hint == "invoice" else LISTING_FIELDS
        schema_line = f"Target schema (JSON keys and meaning): {json.dumps(field_spec, ensure_ascii=False)}"
    else:
        schema_line = (
            "The document is an invoice, a real-estate listing, or something else.\n"
            "- If it is an invoice: set doc_type to 'invoice' and use the invoice schema.\n"
            "- If it is a real-estate listing: set doc_type to 'listing' and use the listing schema.\n"
            "- Otherwise: set doc_type to 'generic' and pick 5-8 key fields that best "
            "represent this document's structure (short snake_case English keys), "
            "extracting their values from the text. Keep the original wording in the "
            "values; use null only for a field you chose that is truly absent.\n"
            "Reply ONLY with a JSON object (doc_type plus the fields).\n"
            f"Invoice schema: {json.dumps(INVOICE_FIELDS, ensure_ascii=False)}\n"
            f"Listing schema: {json.dumps(LISTING_FIELDS, ensure_ascii=False)}"
        )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"{schema_line}\n\n"
                    f"Document text:\n\"\"\"\n{text[:12000]}\n\"\"\"\n\nReply with JSON only."
                ),
            },
        ],
        temperature=0.1,
    )
    return _parse_json(resp.choices[0].message.content)


def extract_fields_from_image(image_bytes: bytes, mime: str, hint: str = "") -> dict:
    """图片（发票/房源截图）→ 视觉模型 → 字段 JSON。"""
    if os.getenv("LLM_MODE", "") == "mock":
        return _mock_result(hint or "listing")

    field_spec = INVOICE_FIELDS if hint == "invoice" else LISTING_FIELDS
    b64 = base64.b64encode(image_bytes).decode()
    client = _client()
    resp = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Extract fields from this document image. "
                            f"Target schema: {json.dumps(field_spec, ensure_ascii=False)}. "
                            "Reply with JSON only."
                        ),
                    },
                ],
            },
        ],
        temperature=0.1,
    )
    return _parse_json(resp.choices[0].message.content)
