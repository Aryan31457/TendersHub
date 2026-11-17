import os
import re
import time
from playwright.sync_api import sync_playwright
from captcha_solver import solve_captcha_with_ai
from config import MAX_PAGES, URL
from script import parse_tenders_from_html
from tender_search import search_tender_by_id


def scrape_tenders(limit=None, max_pages=None):
  """Scrapes active tenders from the portal with AI CAPTCHA solving.

  Args:
      limit (int, optional): Max number of tenders to extract (e.g. 10). If
        None, extracts all.
      max_pages (int, optional): Max pages to paginate. Overrides MAX_PAGES if
        given.
  """
  tenders_list = []
  target_pages = max_pages if max_pages is not None else MAX_PAGES

  with sync_playwright() as p:
    # Launch browser (set headless=False so progress can be monitored)
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print(f"[LOG] Navigating to Active Tenders URL: {URL}...")
    page.goto(URL, timeout=60000)
    print(f"[LOG] Successfully reached target page: {page.url}")

    # Optional: Select sorting by 'Published Date' if radio button exists
    try:
      page.click(
          "input#published, input[id='published'], input[value='Published Date']",
          timeout=2000,
      )
    except Exception:
      pass

    # 1. Automated AI CAPTCHA Handling with Retries
    captcha_input_selector = (
        "input#captchaText, input[name='captchaText'], input[name*='Captcha'"
        " i], input[id*='captcha' i]"
    )
    max_retries = 5
    success = False

    for attempt in range(max_retries):
      try:
        print(f"\n[LOG] --- CAPTCHA Attempt {attempt + 1}/{max_retries} ---")
        page.wait_for_selector(
            "img#captchaImage, img[id*='captcha' i], img[src*='captcha']",
            timeout=10000,
        )

        # Captures screenshot, logs sending to AI agent, and returns case-sensitive string
        solved_code = solve_captcha_with_ai(page)
        if not solved_code:
          raise ValueError("Received empty code from CAPTCHA solver.")

        # Fill the CAPTCHA field exactly as returned (case-sensitive)
        page.fill(captcha_input_selector, solved_code)
        print(
            f"[LOG] Filled CAPTCHA: '{solved_code}' (Preserving exact"
            " case-sensitivity)."
        )
        time.sleep(1)

        print("[LOG] Submitting Search form and awaiting verification...")
        page.click("input#Submit, input[value='Search'], button:has-text('Search')")

        try:
          page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
          pass
        page.wait_for_timeout(2000)

        # Verify whether the results table loaded
        html_check = page.content()
        test_tenders = parse_tenders_from_html(html_check, base_url=page.url or URL)
        if len(test_tenders) > 0 or page.locator("table#table.list_table tr, table.list_table tr").count() > 2:
          print("[LOG] CAPTCHA accepted and active tenders table loaded successfully!")
          success = True
          break
        else:
          print(f"[LOG] Attempt {attempt + 1}: CAPTCHA rejected or table not loaded. Reloading page...")
          page.goto(URL, timeout=60000)
          print(f"[LOG] Reached page: {page.url}")
          try:
            page.click(
                "input#published, input[id='published'], input[value='Published Date']",
                timeout=2000,
            )
          except Exception:
            pass
          page.wait_for_timeout(1000)
      except Exception as e:
        print(f"[LOG] Error during automated CAPTCHA execution (Attempt {attempt + 1}): {e}")
        try:
          page.goto(URL, timeout=60000)
        except Exception:
          pass

    if not success:
      print("[LOG] Failed to pass CAPTCHA automatically after maximum retries.")
      # Fallback to manual solving prompt if needed
      try:
        from captcha import handle_manual_captcha
        print("[LOG] Falling back to manual CAPTCHA solving...")
        handle_manual_captcha(page)
        html_check = page.content()
        if len(parse_tenders_from_html(html_check, base_url=page.url or URL)) > 0:
          success = True
      except Exception:
        pass

      if not success:
        browser.close()
        return []

    # 2. Extract Data & Paginate
    print("\n[LOG] Extracting active tender data from page...")
    html_content = page.content()

    # Save snapshot to tenders.html
    try:
      with open("tenders.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    except Exception as e:
      print(f"Warning: Could not save tenders.html: {e}")

    # Detect Total Records if reported on the page
    total_records = None
    match = re.search(r"Total\s*records\s*:\s*(\d+)", html_content, re.IGNORECASE)
    if match:
      total_records = int(match.group(1))
      print(f"[LOG] Total active tender records reported by portal: {total_records}")

    page_num = 1
    seen_tender_keys = set()

    try:
      while True:
        current_page_tenders = parse_tenders_from_html(
            html_content, base_url=page.url or URL
        )

        # De-duplicate entries
        new_items = []
        for t in current_page_tenders:
          key = t.get("Tender ID") or f"{t.get('S.No')}_{t.get('Title')}"
          if key not in seen_tender_keys:
            seen_tender_keys.add(key)
            new_items.append(t)

        if not new_items:
          print(f"[LOG] Page {page_num}: No new tender rows found. Ending pagination.")
          break

        tenders_list.extend(new_items)
        progress_total = f" / {limit}" if limit else (f" / {total_records}" if total_records else "")
        print(
            f"[LOG] Page {page_num}: Extracted {len(new_items)} tenders"
            f" (Total: {len(tenders_list)}{progress_total})."
        )

        # Check requested item limit
        if limit and limit > 0 and len(tenders_list) >= limit:
          tenders_list = tenders_list[:limit]
          print(f"[LOG] Successfully reached requested limit of {limit} tenders.")
          break

        # Check stopping criteria
        if total_records and len(tenders_list) >= total_records:
          print(f"[LOG] Successfully collected all {total_records} records.")
          break

        if target_pages and target_pages > 0 and page_num >= target_pages:
          print(f"[LOG] Reached configured limit of {target_pages} pages.")
          break

        # Check for Next page button
        next_btn = page.locator(
            "a#loadNext, a[title='Load Next'], a:has-text('Next >')"
        )
        if next_btn.count() == 0 or not next_btn.first.is_visible():
          print("[LOG] No next page link available ('Next >' not found). Reached final page.")
          break

        prev_first_s_no = (
            current_page_tenders[0]["S.No"] if current_page_tenders else None
        )

        # Navigate to next page
        try:
          with page.expect_navigation(
              wait_until="domcontentloaded", timeout=20000
          ):
            next_btn.first.click()
        except Exception:
          try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
          except Exception:
            pass

        time.sleep(1)

        # Ensure page content actually changed
        for _ in range(5):
          html_content = page.content()
          check_tenders = parse_tenders_from_html(
              html_content, base_url=page.url or URL
          )
          if check_tenders and check_tenders[0]["S.No"] != prev_first_s_no:
            break
          time.sleep(1)

        page_num += 1
        print(f"[LOG] Reached page {page_num}...")

    except KeyboardInterrupt:
      print(
          f"\n[LOG] Pagination interrupted by user. Returning {len(tenders_list)}"
          " tenders collected so far."
      )
    except Exception as e:
      print(f"[LOG] Pagination stopped on page {page_num} due to: {e}")
    finally:
      browser.close()

  if limit and len(tenders_list) > limit:
    tenders_list = tenders_list[:limit]

  print(f"\n[LOG] Completed scraping. Total active tenders extracted: {len(tenders_list)}")
  return tenders_list
