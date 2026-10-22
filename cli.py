"""命令行测试：python cli.py samples/invoice_01.pdf [--mock]

有 key 时走真实抽取；LLM_MODE=mock 时只验证链路。
"""

import os
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from app.extract import guess_kind, pdf_to_text  # noqa: E402
from app.llm import extract_fields_from_image, extract_fields_from_text  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("用法: python cli.py <文件路径> [hint]")
        sys.exit(1)
    path = pathlib.Path(sys.argv[1])
    hint = sys.argv[2] if len(sys.argv) > 2 else ""
    data = path.read_bytes()
    kind = guess_kind(path.suffix, path.name)

    if kind == "pdf":
        text = pdf_to_text(data)
        print(f"[PDF 文字层 {len(text)} 字符]")
        print(text[:300])
        print("---")
        result = extract_fields_from_text(text, hint)
    elif kind == "image":
        result = extract_fields_from_image(data, "image/png", hint)
    else:
        print("demo 阶段只支持 pdf / 图片")
        sys.exit(1)

    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
