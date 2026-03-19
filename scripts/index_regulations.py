from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.regulations.scraper import scraper


def main() -> None:
    result: dict[str, Any] = scraper.initialize_vector_index()
    indexed = int(result.get("indexed_docs") or 0)
    print(f"Indexed {indexed} regulations")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)

