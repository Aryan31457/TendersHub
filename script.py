import csv
import os
import re
import urllib.parse
from bs4 import BeautifulSoup


def parse_tenders_from_html(html_content, base_url="https://etenders.gov.in/eprocure/app"):
    """
    Parses active tenders table from raw HTML content.
    Extracts S.No, Published Date, Closing Date, Opening Date,
    Title, Ref No, Tender ID, Organisation Chain, Tender Value (INR), and Link.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    tenders_data = []

    # Locate all table rows in the document
    for row in soup.find_all("tr"):
        cols = row.find_all("td", recursive=False)
        # Fall back if td elements are nested
        if len(cols) != 7:
            cols = row.find_all("td")
            if len(cols) != 7:
                continue

        s_no = cols[0].get_text(strip=True)

        # Ensure we are only grabbing data rows (e.g., S.No starts with digits like "1." or "21")
        if re.match(r"^\d+\.?$", s_no):
            published_date = cols[1].get_text(strip=True)
            closing_date = cols[2].get_text(strip=True)
            opening_date = cols[3].get_text(strip=True)

            # Column 5 combines Title (inside an <a> tag), Ref No, and Tender ID
            title_col = cols[4]
            link_tag = title_col.find("a")
            title = link_tag.get_text(strip=True) if link_tag else ""
            tender_url = link_tag["href"] if link_tag and link_tag.has_attr("href") else ""
            if tender_url and not tender_url.startswith("http"):
                tender_url = urllib.parse.urljoin(base_url, tender_url)

            # Extract bracketed metadata like [DPHCL/AMC/2026-27/10][2026_DPHCL_297981_1]
            raw_col5_text = title_col.get_text(" ", strip=True)
            brackets = re.findall(r"\[(.*?)\]", raw_col5_text)
            ref_no = brackets[-2] if len(brackets) >= 2 else ""
            tender_id = brackets[-1] if len(brackets) >= 1 else ""

            # Fallback for title if <a> tag was not present
            if not title:
                cleaned_title = re.sub(r"\[.*?\]", "", raw_col5_text).strip()
                title = cleaned_title if cleaned_title else raw_col5_text

            org_chain = cols[5].get_text(strip=True).replace("\n", " ")
            tender_value = cols[6].get_text(strip=True).replace("\n", " ")

            tenders_data.append({
                "S.No": s_no.rstrip("."),
                "Published Date": published_date,
                "Closing Date": closing_date,
                "Opening Date": opening_date,
                "Title": title,
                "Ref No": ref_no,
                "Tender ID": tender_id,
                "Organisation Chain": org_chain,
                "Tender Value (INR)": tender_value,
                "Link": tender_url
            })

    return tenders_data


def parse_tenders_file(html_file="tenders.html", output_csv="extracted_tenders.csv"):
    """Reads saved HTML file, parses tenders, and outputs to CSV."""
    if not os.path.exists(html_file):
        print(f"File '{html_file}' not found. Running scraper to fetch active tenders...")
        from scraper import scrape_tenders
        from notifier import save_outputs, send_email_alert
        tenders = scrape_tenders()
        if tenders:
            save_outputs(tenders)
            send_email_alert(tenders, "extracted_tenders.csv")
        return tenders

    with open(html_file, "r", encoding="utf-8") as file:
        html_content = file.read()

    tenders_data = parse_tenders_from_html(html_content)

    if tenders_data:
        keys = tenders_data[0].keys()
        with open(output_csv, "w", newline="", encoding="utf-8") as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(tenders_data)
        print(f"Successfully extracted {len(tenders_data)} tenders to '{output_csv}'.")
    else:
        print(f"No tender rows found in '{html_file}'. Verify the HTML file structure.")

    return tenders_data


# Re-export scrape_tenders and search_tender_by_id
def scrape_tenders(limit=None, max_pages=None):
    from scraper import scrape_tenders as _scrape
    return _scrape(limit=limit, max_pages=max_pages)

def search_tender_by_id(tender_id, headless=True, launch_system_browser=False, log_callback=None):
    from tender_search import search_tender_by_id as _search
    return _search(tender_id=tender_id, headless=headless, launch_system_browser=launch_system_browser, log_callback=log_callback)


if __name__ == "__main__":
    parse_tenders_file()
