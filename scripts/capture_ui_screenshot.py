"""Take a screenshot of the running Streamlit UI for the README.

Assumes Streamlit is already serving at http://localhost:8501. This script
exists so that the screenshot included in docs/images/ can be regenerated
deterministically -- not so that it has to run from CI.

Usage:
    streamlit run app/streamlit_app.py &
    python scripts/capture_ui_screenshot.py --out docs/images/streamlit_ui.png

Optional knobs:
    --url     where Streamlit is serving (default http://localhost:8501)
    --select  index of the sample image to select in the sidebar (default 2,
              which is scratch_surface.png after the placeholder)
    --width   viewport width in px (default 1400)
    --height  viewport height in px (default 1100)
    --click-run  also click the "검사 시작" button and wait for results
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from playwright.sync_api import sync_playwright


def capture(url: str, out: str, viewport: tuple[int, int],
            select_index: int, click_run: bool) -> str:
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": viewport[0],
                                            "height": viewport[1]})
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle")
        # Streamlit re-renders a few times after page load; let things settle.
        page.wait_for_timeout(2500)

        if select_index >= 0:
            try:
                # The sample-image dropdown is the only stSelectbox in our
                # sidebar. Open it and pick `select_index` from the list
                # (0 = "(선택 안 함)", 1.. = the actual sample files).
                sb = page.locator("[data-testid='stSelectbox']")
                if sb.count() > 0:
                    sb.first.click()
                    page.wait_for_timeout(500)
                    options = page.locator("li[role='option']")
                    if options.count() > select_index:
                        options.nth(select_index).click()
                        page.wait_for_timeout(1200)
            except Exception as e:
                print(f"[capture] sample-select skipped: {e}", file=sys.stderr)

        if click_run:
            try:
                run_btn = page.get_by_role("button", name="검사 시작")
                if run_btn.count() > 0:
                    run_btn.first.click()
                    # Wait for the verdict / metrics block to render. Streamlit
                    # updates the DOM incrementally; networkidle is unreliable
                    # so just sleep enough for a CPU-bound 50ms inspection.
                    page.wait_for_timeout(4000)
            except Exception as e:
                print(f"[capture] click-run skipped: {e}", file=sys.stderr)

        # Capture the whole page (scroll-aware) to include the results.
        page.screenshot(path=out, full_page=True)
        browser.close()
    print(f"[capture] wrote {out}")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://localhost:8501")
    p.add_argument("--out", default=os.path.join("docs", "images",
                                                 "streamlit_ui.png"))
    p.add_argument("--width", type=int, default=1400)
    p.add_argument("--height", type=int, default=1100)
    p.add_argument("--select", type=int, default=2,
                   help="index into the sample-image dropdown")
    p.add_argument("--click-run", action="store_true")
    args = p.parse_args(argv)
    capture(args.url, args.out, (args.width, args.height),
            args.select, args.click_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
