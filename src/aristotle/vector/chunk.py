import re
from typing import List


def split_markdown(
    md_text: str, codebase_name: str, reference: str, max_chars: int = 2800
) -> List[str]:
    parts = []
    buf = []
    size = 0
    in_code = False
    for line in md_text.splitlines(keepends=True):
        if line.strip().startswith("```"):
            in_code = not in_code
        if not in_code and size > max_chars and re.match(r"^#{1,6} ", line):
            parts.append("".join(buf))
            buf, size = [], 0
        buf.append(line)
        size += len(line)
        if size > max_chars * 1.2 and not in_code:
            parts.append("".join(buf))
            buf, size = [], 0
    if buf:
        parts.append("".join(buf))
    return [
        codebase_name + "\n" + reference + "\n" + p.strip() for p in parts if p.strip()
    ]
