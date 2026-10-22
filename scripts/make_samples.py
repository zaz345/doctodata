"""生成 10 份假样例：5 份假发票 PDF + 5 份假房源截图 PNG。

全部为随机虚构数据，不含任何真实公司/个人/小区。
用法：python scripts/make_samples.py
"""

import io
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).parent.parent
SAMPLES = ROOT / "samples"
SAMPLES.mkdir(exist_ok=True)

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

random.seed(2026)  # 可复现

FAKE_SELLERS = ["星辰云图科技有限公司", "青梧信息技术有限公司", "北斗七折网络公司", "临江数联软件有限公司", "南枝智能科技公司"]
FAKE_BUYERS = ["远山贸易有限公司", "汇文咨询工作室", "皓月电子商务公司", "白泽传媒有限公司", "澄川物流有限公司"]
ITEM_POOL = ["API调用服务费", "数据清洗服务", "软件定制开发", "云主机租赁费", "技术咨询服务"]
CITIES = ["北京", "杭州", "成都", "武汉", "西安"]
DISTRICTS = {"北京": "海淀区", "杭州": "西湖区", "成都": "高新区", "武汉": "洪山区", "西安": "雁塔区"}
COMMUNITIES = ["云栖竹径小区", "梧桐苑", "兰亭水岸", "枫桥雅居", "南山叠翠"]
LAYOUTS = ["1室1厅", "2室1厅", "2室2厅", "3室2厅", "4室2厅"]
ORIENTS = ["南北", "朝南", "东南", "东西"]


def fake_invoice(idx: int) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    c.setFont("STSong-Light", 22)
    c.drawCentredString(w / 2, h - 40 * mm, "增 值 税 电 子 普 通 发 票")
    c.setFont("STSong-Light", 11)
    c.drawString(20 * mm, h - 52 * mm, f"发票号码：{random.randint(10**10, 10**11 - 1)}")
    c.drawString(120 * mm, h - 52 * mm, f"开票日期：2026年{random.randint(1,9):02d}月{random.randint(1,28):02d}日")

    seller = random.choice(FAKE_SELLERS)
    buyer = random.choice(FAKE_BUYERS)

    c.drawString(20 * mm, h - 66 * mm, "销售方")
    c.drawString(40 * mm, h - 66 * mm, f"名称：{seller}")
    c.drawString(40 * mm, h - 74 * mm, f"纳税人识别号：{random.randint(10**14, 10**15 - 1)}")

    c.drawString(20 * mm, h - 88 * mm, "购买方")
    c.drawString(40 * mm, h - 88 * mm, f"名称：{buyer}")
    c.drawString(40 * mm, h - 96 * mm, f"纳税人识别号：{random.randint(10**14, 10**15 - 1)}")

    y = h - 115 * mm
    c.drawString(20 * mm, y, "项目名称")
    c.drawString(90 * mm, y, "金额（元）")
    c.drawString(130 * mm, y, "税率")
    c.line(20 * mm, y - 2 * mm, w - 20 * mm, y - 2 * mm)

    total = 0.0
    n_items = random.randint(1, 3)
    for i in range(n_items):
        amount = round(random.uniform(500, 20000), 2)
        total += amount
        yy = y - (10 + i * 10) * mm
        c.drawString(20 * mm, yy, random.choice(ITEM_POOL))
        c.drawString(90 * mm, yy, f"{amount:,.2f}")
        c.drawString(130 * mm, yy, "6%")

    tax = round(total * 0.06, 2)
    yy = y - (12 + n_items * 10) * mm
    c.drawString(20 * mm, yy, f"合计：￥{total:,.2f}")
    c.drawString(90 * mm, yy, f"税额：￥{tax:,.2f}")
    c.setFont("STSong-Light", 13)
    c.drawString(20 * mm, yy - 12 * mm, f"价税合计（大写）：（小写）￥{total + tax:,.2f}")

    c.showPage()
    c.save()
    return buf.getvalue()


def fake_listing(idx: int) -> bytes:
    city = random.choice(CITIES)
    district = DISTRICTS[city]
    community = random.choice(COMMUNITIES)
    layout = random.choice(LAYOUTS)
    area = round(random.uniform(55, 160), 1)
    price = round(area * random.uniform(3.5, 7.0) / 10, 1)  # 万
    unit = round(price * 10000 / area)
    floor = f"{random.randint(3, 25)}/{random.randint(26, 33)}层"

    img = Image.new("RGB", (900, 600), "#f7f8fa")
    d = ImageDraw.Draw(img)
    font_big = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 36)
    font_mid = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 26)
    font_sml = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 22)

    d.rectangle([0, 0, 900, 90], fill="#2f6fed")
    d.text((30, 25), f"{city}二手房", fill="white", font=font_mid)

    d.text((40, 120), f"{community} {layout}", fill="#1a1a1a", font=font_big)
    d.text((40, 190), f"{price} 万", fill="#e64a19", font=font_big)
    d.text((260, 205), f"单价 {unit} 元/平米", fill="#666666", font=font_mid)

    rows = [
        f"位置：{city}市{district}{community}",
        f"户型：{layout}",
        f"面积：{area} 平米",
        f"楼层：{floor}",
        f"朝向：{random.choice(ORIENTS)}",
        f"挂牌时间：2026年{random.randint(1,9):02d}月",
    ]
    for i, row in enumerate(rows):
        d.text((40, 290 + i * 44), row, fill="#333333", font=font_sml)

    d.text((40, 560), "示例截图，数据纯属虚构", fill="#999999", font=font_sml)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


for i in range(1, 6):
    (SAMPLES / f"invoice_{i:02d}.pdf").write_bytes(fake_invoice(i))
    (SAMPLES / f"listing_{i:02d}.png").write_bytes(fake_listing(i))

print("生成完毕：", sorted(p.name for p in SAMPLES.iterdir()))
