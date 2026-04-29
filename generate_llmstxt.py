"""
Generates llms.txt and llms-full.txt from a completed crawl DB.

Usage:
    python generate_llmstxt.py --db crawl.db --out ./output
    python generate_llmstxt.py --db crawl.db --validate-only
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from processor.llmstxt_builder import build, validate


def main():
    parser = argparse.ArgumentParser(description="Generate llms.txt from crawl DB")
    parser.add_argument("--db", default="crawl.db", help="SQLite DB path")
    parser.add_argument("--out", default=".", help="Output directory")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing llms.txt")
    args = parser.parse_args()

    if args.validate_only:
        llms_path = Path(args.out) / "llms.txt"
        if not llms_path.exists():
            print(f"Not found: {llms_path}")
            sys.exit(1)
        errors = validate(llms_path.read_text())
        if errors:
            print("Validation errors:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        print("llms.txt is valid.")
        return

    Path(args.out).mkdir(parents=True, exist_ok=True)
    llms_txt, llms_full = build(args.db, args.out)

    if not llms_txt:
        print("No pages found. Run the crawler first.")
        sys.exit(1)

    print(f"Generated: {args.out}/llms.txt ({len(llms_txt.splitlines())} lines)")
    print(f"Generated: {args.out}/llms-full.txt ({len(llms_full.splitlines())} lines)")
    print("\nllms.txt preview (first 20 lines):")
    print("-" * 60)
    print("\n".join(llms_txt.splitlines()[:20]))


if __name__ == "__main__":
    main()
