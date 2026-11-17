from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
import smtplib
import pandas as pd
from config import RECEIVER_EMAIL, SENDER_EMAIL, SENDER_PASSWORD


def save_outputs(tenders):
  """Saves scraped data into timestamped Excel, CSV, and JSON files."""
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  excel_filename = f"active_tenders_{timestamp}.xlsx"
  json_filename = f"active_tenders_{timestamp}.json"
  csv_filename = f"active_tenders_{timestamp}.csv"

  # 1. Save to JSON
  with open(json_filename, "w", encoding="utf-8") as f:
    json.dump(tenders, f, indent=4, ensure_ascii=False)

  # 2. Save to Excel & CSV
  df = pd.DataFrame(tenders)
  df.to_excel(excel_filename, index=False, engine="openpyxl")
  df.to_csv(csv_filename, index=False, encoding="utf-8")
  df.to_csv("extracted_tenders.csv", index=False, encoding="utf-8")

  print(
      f"Successfully saved {len(tenders)} active tenders to '{excel_filename}',"
      f" '{csv_filename}', and '{json_filename}'."
  )
  return excel_filename


def send_email_alert(tenders, attachment_path):
  """Sends an email alert with the Excel report attached."""
  if not tenders or not SENDER_EMAIL or not RECEIVER_EMAIL:
    print("Skipping email delivery: Missing email config or empty list.")
    return

  subject = f"📋 Active Tenders Report ({len(tenders)} Listings) - {datetime.now().strftime('%d %b %Y')}"
  body = (
      f"Attached is the latest export containing {len(tenders)} active tenders"
      " from etenders.gov.in.\n\n"
      "Top Highlights:\n"
  )
  for t in tenders[:5]:
    title = t.get("Title") or t.get("Title and Ref.No./Tender ID") or "Tender"
    closing = t.get("Closing Date") or t.get("Bid Submission Closing Date") or "N/A"
    tender_id = t.get("Tender ID")
    display_title = f"{title} [{tender_id}]" if tender_id else title
    body += f"• {display_title} (Closing: {closing})\n"

  msg = MIMEMultipart()
  msg["From"] = SENDER_EMAIL
  msg["To"] = RECEIVER_EMAIL
  msg["Subject"] = subject
  msg.attach(MIMEText(body, "plain"))

  try:
    with open(attachment_path, "rb") as attachment:
      part = MIMEBase("application", "octet-stream")
      part.set_payload(attachment.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename={os.path.basename(attachment_path)}",
    )
    msg.attach(part)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
      server.starttls()
      server.login(SENDER_EMAIL, SENDER_PASSWORD)
      server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    print("Email alert with Excel attachment sent successfully!")
  except Exception as e:
    print(f"Failed to send email: {e}")
