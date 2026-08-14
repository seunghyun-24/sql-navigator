"""test-queries.md의 모든 ```sql 블록이 sqlglot(postgres)으로 파싱되는지 검증.

사용: python examples/validate_examples.py
"""

import re
import sys
from pathlib import Path

import sqlglot

MD_PATH = Path(__file__).parent / "test-queries.md"


def main() -> int:
    md = MD_PATH.read_text(encoding="utf-8")
    blocks = re.findall(r"```sql\n(.*?)```", md, re.DOTALL)
    failures = 0
    for i, sql in enumerate(blocks, start=1):
        try:
            statements = sqlglot.parse(sql, read="postgres")
            print(f"block {i}: OK ({len(statements)} statement(s))")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"block {i}: FAIL - {e}")
    print(f"\n{len(blocks)} blocks, {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
