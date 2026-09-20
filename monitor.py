import json
import os
import re
import time
from datetime import date, timedelta

import requests
from playwright.sync_api import sync_playwright


BOOKING_URL = "https://www.tbluelinepark.com/ticket_chn/GD2100036"
START_DATE = date(2026, 10, 12)
END_DATE = date(2026, 10, 16)
MIN_TICKETS = 1
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", "30"))


def target_dates():
    current = START_DATE
    while current <= END_DATE:
        yield current
        current += timedelta(days=1)


def parse_remaining(text: str) -> int:
    if "售罄" in text:
        return 0
    match = re.search(r"剩余\s*:\s*(\d+)", text)
    return int(match.group(1)) if match else 0


def prepare_page(page):
    page.goto(BOOKING_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_selector("#calYyyyMM", timeout=30_000)
    wanted_month = START_DATE.strftime("%Y %m")
    for _ in range(18):
        shown_month = page.locator("#calYyyyMM").inner_text().strip()
        if shown_month == wanted_month:
            return
        page.locator("#moveNextMonth").click()
        page.wait_for_timeout(500)
    raise RuntimeError(f"無法切換到 {wanted_month}")


def check_tickets(page):
    available = []
    for target in target_dates():
        selector = f'[id="{target.strftime("%Y%m%d")}"]'
        day = page.locator(selector)
        if day.count() == 0 or not day.get_attribute("onclick"):
            print(f"{target}: 尚未開放或沒有班次", flush=True)
            continue

        day.click()
        page.locator("ul.scheduleInfoSelectUl li").first.wait_for(
            state="attached", timeout=10_000
        )
        rows = page.locator("ul.scheduleInfoSelectUl li").all_inner_texts()
        for row in rows:
            remaining = parse_remaining(row)
            if remaining >= MIN_TICKETS:
                time_match = re.search(r"(\d{2}:\d{2}\s*~\s*\d{2}:\d{2})", row)
                available.append(
                    {
                        "date": target.isoformat(),
                        "time": time_match.group(1).replace(" ", "") if time_match else row,
                        "remaining": remaining,
                    }
                )
    return available


def send_line_message(items):
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token or not user_id:
        raise RuntimeError("缺少 LINE_CHANNEL_ACCESS_TOKEN 或 LINE_USER_ID")

    lines = ["【釜山膠囊列車有票了】"]
    lines.extend(
        f"{item['date']}｜{item['time']}｜剩餘 {item['remaining']} 張"
        for item in items
    )
    lines.extend(["", "立即查看：", BOOKING_URL])
    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": [{"type": "text", "text": "\n".join(lines)}]},
        timeout=30,
    )
    response.raise_for_status()


def main():
    previous_signature = ""
    print(f"監控啟動：每 {CHECK_INTERVAL_SECONDS} 秒檢查一次", flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        page = browser.new_page(locale="zh-CN")

        while True:
            started = time.monotonic()
            try:
                prepare_page(page)
                items = check_tickets(page)
                signature = json.dumps(items, ensure_ascii=False, sort_keys=True)

                if items and signature != previous_signature:
                    send_line_message(items)
                    print(f"已發送 LINE 通知，共 {len(items)} 個有票班次", flush=True)
                elif items:
                    print("仍有票，但狀態未改變，不重複通知", flush=True)
                else:
                    print("目前沒有符合條件的班次", flush=True)

                previous_signature = signature
            except Exception as error:
                print(f"本輪查詢失敗：{type(error).__name__}: {error}", flush=True)
                try:
                    page.close()
                except Exception:
                    pass
                page = browser.new_page(locale="zh-CN")

            elapsed = time.monotonic() - started
            time.sleep(max(1, CHECK_INTERVAL_SECONDS - elapsed))


if __name__ == "__main__":
    main()
