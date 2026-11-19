#!/usr/bin/env python3
import re
import sys
from pathlib import Path

HUNG_RE = re.compile(r"INFO: task .*blocked for more than", re.MULTILINE)
F2FS_RE = re.compile(r"f2fs_write_data_pages")
DIREAD_RE = re.compile(r"WARNING in diRead")


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def first_matching_line(block, pattern):
    match = pattern.search(block)
    if not match:
        return ""
    return block[match.start() : block.find("\n", match.start())]


def verify(path: Path) -> bool:
    with path.open(errors="replace", newline="") as handle:
        text = handle.read()
    hung_matches = list(HUNG_RE.finditer(text))
    target_blocks = []

    for index, match in enumerate(hung_matches):
        end = (
            hung_matches[index + 1].start()
            if index + 1 < len(hung_matches)
            else len(text)
        )
        block = text[match.start() : end]
        if F2FS_RE.search(block):
            target_blocks.append((match.start(), block))

    diread_count = len(DIREAD_RE.findall(text))

    if not target_blocks:
        print(f"{path}: FAIL: no hung-task report contains f2fs_write_data_pages")
        return False

    offset, block = target_blocks[0]
    hung_line = first_matching_line(block, HUNG_RE)
    f2fs_line = first_matching_line(block, F2FS_RE)
    print(f"{path}: PASS")
    print(f"  hung-task report: line {line_number(text, offset)}: {hung_line}")
    print(f"  target function:  {f2fs_line}")
    print(f"  f2fs target reports: {len(target_blocks)}")
    print(f"  WARNING in diRead occurrences: {diread_count}")
    return True


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} serial-log [serial-log ...]", file=sys.stderr)
        return 2

    results = [verify(Path(arg)) for arg in sys.argv[1:]]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
