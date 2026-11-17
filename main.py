import argparse
from notifier import save_outputs, send_email_alert
from scraper import scrape_tenders


def main():
  parser = argparse.ArgumentParser(
      description="Active Tenders Scraper Pipeline with AI CAPTCHA solving."
  )
  parser.add_argument(
      "--limit",
      "-l",
      type=int,
      default=None,
      help=(
          "Maximum number of tenders to extract (e.g. --limit 10). Extracts all"
          " if omitted."
      ),
  )
  parser.add_argument(
      "--max-pages",
      "-p",
      type=int,
      default=None,
      help="Maximum number of pages to paginate (e.g. --max-pages 2).",
  )
  args = parser.parse_args()

  limit_msg = f" (Limit: {args.limit} tenders)" if args.limit else " (All records)"
  print(f"Starting Active Tenders Scraper Pipeline{limit_msg}...")

  # 1. Scrape the active tenders portal with optional limit / max_pages
  tenders = scrape_tenders(limit=args.limit, max_pages=args.max_pages)

  if tenders:
    # 2. Save data to Excel, CSV & JSON files
    excel_file = save_outputs(tenders)

    # 3. Email the results with attachment
    send_email_alert(tenders, excel_file)
  else:
    print(
        "No active tenders were collected. Please verify that the results table"
        " loaded correctly."
    )


if __name__ == "__main__":
  main()
