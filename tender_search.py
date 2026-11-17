import time
import urllib.parse
import webbrowser
from playwright.sync_api import sync_playwright
from captcha_solver import solve_captcha_with_ai
from config import URL
from script import parse_tenders_from_html


def search_tender_by_id(tender_id: str, headless: bool = True, launch_system_browser: bool = False, log_callback=None):
  """Searches for a tender using its Tender ID on the active tenders portal,

  generates a fresh live session, and extracts fresh details and link.

  Args:
      tender_id (str): The official Tender ID (e.g. 2026_NTECL_297806_1).
      headless (bool): Whether to run Playwright in headless mode.
      launch_system_browser (bool): Whether to automatically open the fresh URL
        in user's browser.
      log_callback (callable, optional): Callback function for log messages.

  Returns:
      dict: Result containing status, tender details, and fresh direct link.
  """

  def log(msg):
    if log_callback:
      log_callback(msg)
    print(f"[SEARCH_BY_ID] {msg}")

  tender_id = tender_id.strip()
  if not tender_id:
    return {"success": False, "error": "Tender ID cannot be empty."}

  log(f"Initiating search for Tender ID: '{tender_id}'...")

  with sync_playwright() as p:
    browser = p.chromium.launch(headless=headless)
    page = browser.new_page()

    try:
      log(f"Navigating to Active Tenders portal...")
      page.goto(URL, timeout=60000)

      # Fill Tender ID
      tender_input_selector = "input#TenderId, input[name='TenderId']"
      page.wait_for_selector(tender_input_selector, timeout=15000)
      page.fill(tender_input_selector, tender_id)
      log(f"Filled Tender ID field with '{tender_id}'.")

      # AI CAPTCHA solving with retries
      captcha_input_selector = (
          "input#captchaText, input[name='captchaText'], input[name*='Captcha'"
          " i], input[id*='captcha' i]"
      )
      max_retries = 3
      search_success = False

      for attempt in range(max_retries):
        try:
          log(f"Solving CAPTCHA with AI (Attempt {attempt + 1}/{max_retries})...")
          page.wait_for_selector(
              "img#captchaImage, img[id*='captcha' i], img[src*='captcha']",
              timeout=10000,
          )

          solved_code = solve_captcha_with_ai(page)
          if not solved_code:
            raise ValueError("Empty response from AI CAPTCHA solver.")

          page.fill(captcha_input_selector, solved_code)
          time.sleep(1)

          log("Submitting search form...")
          page.click("input#Submit, input[value='Search'], button:has-text('Search')")

          try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
          except Exception:
            pass
          page.wait_for_timeout(2000)

          # Verify if results table has loaded
          html_content = page.content()
          tenders = parse_tenders_from_html(html_content, base_url=page.url or URL)
          if len(tenders) > 0 or page.locator("table#table.list_table tr, table.list_table tr").count() > 2:
            log("CAPTCHA accepted and search results loaded successfully!")
            search_success = True
            break
          else:
            log(f"Attempt {attempt + 1}: CAPTCHA rejected. Refreshing form...")
            page.goto(URL, timeout=60000)
            page.fill(tender_input_selector, tender_id)
        except Exception as e:
          log(f"Error on CAPTCHA attempt {attempt + 1}: {e}")
          try:
            page.goto(URL, timeout=60000)
            page.fill(tender_input_selector, tender_id)
          except Exception:
            pass

      if not search_success:
        return {
            "success": False,
            "error": "Failed to bypass CAPTCHA after retries. Please try again.",
        }

      # Extract results
      html_content = page.content()
      tenders = parse_tenders_from_html(html_content, base_url=page.url or URL)

      matched_tender = None
      for t in tenders:
        if tender_id.lower() in t.get("Tender ID", "").lower() or tender_id.lower() in t.get("Title", "").lower():
          matched_tender = t
          break

      if not matched_tender and tenders:
        # If single result returned, match first
        matched_tender = tenders[0]

      if not matched_tender:
        return {
            "success": False,
            "error": (
                f"No active tender found matching Tender ID '{tender_id}'. The"
                " tender may have closed, been archived, or ID is incorrect."
            ),
        }

      log(f"Found active tender listing: '{matched_tender.get('Title')}'")

      # Navigate to the official tender detail page
      detail_link_locator = page.locator(
          "table#table a[title='View Tender Information'], table.list_table a"
      ).first
      fresh_details_url = matched_tender.get("Link", "")

      if detail_link_locator.count() > 0:
        try:
          with page.expect_navigation(timeout=15000):
            detail_link_locator.click()
          fresh_details_url = page.url
          log(f"Successfully generated fresh live URL: {fresh_details_url}")
        except Exception:
          pass

      # If user wanted to open in system browser
      if launch_system_browser and fresh_details_url:
        log("Opening live portal webpage in system browser...")
        webbrowser.open(fresh_details_url)

      return {
          "success": True,
          "tender_id": tender_id,
          "tender_data": matched_tender,
          "details_url": fresh_details_url,
          "portal_url": page.url,
      }

    finally:
      browser.close()
