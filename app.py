import glob
import io
import json
import os
import webbrowser
import pandas as pd
import streamlit as st
from config import AI_PROVIDER, GEMINI_MODEL, URL
from notifier import save_outputs, send_email_alert
from scraper import scrape_tenders
from tender_search import search_tender_by_id

# Page configuration
st.set_page_config(
    page_title="India eProcurement Tenders Hub",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for polished interface
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        background-color: #DEF7EC;
        color: #03543F;
        margin-right: 0.5rem;
    }
    .tender-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 0.75rem;
        padding: 1.25rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .tender-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1E293B;
        margin-bottom: 0.5rem;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Header
st.markdown(
    '<div class="main-header">🏛️ India eProcurement Tenders Hub</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="sub-header">Automated Active Tenders Scraper & Live Session'
    " Tender ID Search (etenders.gov.in)</div>",
    unsafe_allow_html=True,
)

# Sidebar info
with st.sidebar:
  st.header("⚙️ Configuration & Status")
  st.markdown(f"**Target Portal:** [etenders.gov.in]({URL})")
  st.markdown(f"**AI CAPTCHA Provider:** `{AI_PROVIDER.upper()}`")
  if AI_PROVIDER == "gemini":
    st.markdown(f"**Gemini Model:** `{GEMINI_MODEL}`")

  st.divider()
  st.subheader("💡 Session Expiry Note")
  st.info(
      "Government portal direct links expire quickly due to server session"
      " timeouts. Use the **Search by Tender ID** tab anytime to generate a"
      " fresh session and redirect straight to the live tender webpage!"
  )

  st.divider()
  # Check existing files
  csv_files = glob.glob("*.csv")
  excel_files = glob.glob("*.xlsx")
  st.caption(
      f"Local files available: {len(csv_files)} CSVs, {len(excel_files)} Excel"
      " reports."
  )


# Helper function to load latest tenders from disk
def load_latest_tenders():
  if os.path.exists("extracted_tenders.csv"):
    try:
      return pd.read_csv("extracted_tenders.csv")
    except Exception:
      pass
  return pd.DataFrame()


df_existing = load_latest_tenders()

# Tabs
tab_search, tab_scraper, tab_history = st.tabs([
    "🔍 Search by Tender ID & Open Live Webpage",
    "⚡ Active Tenders Scraper",
    "📊 Saved Tenders Database",
])

# ==============================================================================
# TAB 1: Search by Tender ID & Open Webpage
# ==============================================================================
with tab_search:
  st.subheader("🔍 Search Tender by ID on Active Portal (Fresh Live Session)")
  st.write(
      "Enter a **Tender ID** below. The system automatically navigates to the"
      " active tenders portal, solves the CAPTCHA with AI in ~2 seconds, and"
      " redirects you to the live tender details page with an active session."
  )

  col_id1, col_id2 = st.columns([3, 1])

  # Option to choose from recently scraped tenders if available
  recent_ids = []
  if not df_existing.empty and "Tender ID" in df_existing.columns:
    recent_ids = (
        df_existing["Tender ID"].dropna().astype(str).unique().tolist()
    )

  with col_id1:
    search_query = st.text_input(
        "Enter Tender ID (e.g., 2026_NTECL_297806_1):",
        placeholder="Type or paste Tender ID here...",
        key="tender_id_input",
    )

    if recent_ids:
      selected_recent = st.selectbox(
          "Or select a Tender ID from recently extracted data:",
          ["-- Select from recent --"] + recent_ids[:30],
          key="recent_tender_select",
      )
      if (
          selected_recent
          and selected_recent != "-- Select from recent --"
          and not search_query
      ):
        search_query = selected_recent

  with col_id2:
    st.write("")
    st.write("")
    open_sys_browser = st.checkbox(
        "Auto-open in default browser",
        value=True,
        help="Opens the live webpage directly in your web browser once found.",
    )
    search_btn = st.button(
        "🚀 Search & Redirect", type="primary", use_container_width=True
    )

  if search_btn:
    target_id = search_query.strip()
    if not target_id:
      st.warning("Please enter or select a Tender ID first.")
    else:
      log_placeholder = st.empty()
      logs = []

      def ui_log(msg):
        logs.append(msg)
        log_placeholder.info("\n".join(logs[-4:]))

      with st.spinner(
          f"Searching portal for Tender ID '{target_id}' and solving AI"
          " CAPTCHA..."
      ):
        res = search_tender_by_id(
            target_id,
            headless=True,
            launch_system_browser=open_sys_browser,
            log_callback=ui_log,
        )

      log_placeholder.empty()

      if res.get("success"):
        tender = res.get("tender_data", {})
        live_url = res.get("details_url", "") or tender.get("Link", "")

        st.success(f"✅ Found Active Tender matching ID: `{target_id}`")

        # Display Card
        st.markdown(
            f"""
            <div class="tender-card">
                <div class="tender-title">{tender.get('Title', 'Tender Details')}</div>
                <p><strong>🏛️ Organisation Chain:</strong> {tender.get('Organisation Chain', 'N/A')}</p>
                <p><strong>🆔 Tender ID:</strong> <code>{tender.get('Tender ID', target_id)}</code> &nbsp;|&nbsp; 
                   <strong>📄 Ref No:</strong> {tender.get('Ref No', 'N/A')}</p>
                <p><strong>💰 Tender Value:</strong> {tender.get('Tender Value (INR)', 'N/A')} &nbsp;|&nbsp;
                   <strong>📅 Published:</strong> {tender.get('Published Date', 'N/A')}</p>
                <p><strong>⏰ Bid Closing:</strong> <span style="color:#DC2626; font-weight:600;">{tender.get('Closing Date', 'N/A')}</span> &nbsp;|&nbsp;
                   <strong>🔓 Opening Date:</strong> {tender.get('Opening Date', 'N/A')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Action Buttons
        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
          if live_url:
            st.link_button(
                "🌐 Open Live Official Tender Webpage (New Tab)",
                live_url,
                type="primary",
                use_container_width=True,
            )
        with col_btn2:
          if live_url:
            if st.button("🔄 Re-launch in Browser", use_container_width=True):
              webbrowser.open(live_url)

        if live_url:
          st.caption(f"**Fresh Session Link:** `{live_url}`")
      else:
        st.error(f"❌ {res.get('error', 'Search failed.')}")

# ==============================================================================
# TAB 2: Live Tenders Scraper Pipeline
# ==============================================================================
with tab_scraper:
  st.subheader("⚡ Run Active Tenders Scraper")
  st.write(
      "Extract active tenders in bulk across pages. Solves CAPTCHA"
      " automatically and paginates through results."
  )

  col_opt1, col_opt2, col_opt3 = st.columns([1, 1, 1])
  with col_opt1:
    scrape_mode = st.radio(
        "Extraction Limit:",
        ["Extract 10 Tenders (Quick Test)", "Custom Count", "All Tenders"],
        index=0,
    )
  with col_opt2:
    if scrape_mode == "Custom Count":
      limit_val = st.number_input(
          "Number of tenders:", min_value=1, max_value=5000, value=25, step=5
      )
    elif scrape_mode == "Extract 10 Tenders (Quick Test)":
      limit_val = 10
    else:
      limit_val = 0  # All

    max_p = None
  with col_opt3:
    send_email = st.checkbox("Send Email Report when done", value=False)
    st.write("")
    run_btn = st.button(
        "🚀 Run Scraper Now", type="primary", use_container_width=True
    )

  if run_btn:
    log_area = st.empty()
    status_msg = st.empty()

    with st.spinner("Scraper is running (AI CAPTCHA + pagination in progress)..."):
      effective_limit = limit_val if limit_val > 0 else None
      tenders = scrape_tenders(limit=effective_limit, max_pages=max_p)

    if tenders:
      st.success(
          f"🎉 Scraping Complete! Successfully collected {len(tenders)} active"
          " tenders."
      )

      # Save outputs
      excel_file = save_outputs(tenders)
      if send_email:
        send_email_alert(tenders, excel_file)
        st.info(f"📧 Email report sent to recipient with '{excel_file}'.")

      df_scraped = pd.DataFrame(tenders)

      # Metrics
      m1, m2, m3 = st.columns(3)
      m1.metric("Total Listings Extracted", len(df_scraped))
      unique_orgs = (
          df_scraped["Organisation Chain"].nunique()
          if "Organisation Chain" in df_scraped
          else 0
      )
      m2.metric("Organisations Represented", unique_orgs)
      closing_soon = len(df_scraped)
      m3.metric("Status", "Saved to Excel/CSV/JSON")

      # Interactive Table
      st.dataframe(df_scraped, use_container_width=True, height=400)

      # Download Buttons
      c1, c2, c3 = st.columns(3)
      with c1:
        # Excel download
        buffer = io.BytesIO()
        df_scraped.to_excel(buffer, index=False, engine="openpyxl")
        st.download_button(
            label="📥 Download Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name=os.path.basename(excel_file),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
      with c2:
        csv_data = df_scraped.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download CSV (.csv)",
            data=csv_data,
            file_name="extracted_tenders.csv",
            mime="text/csv",
            use_container_width=True,
        )
      with c3:
        json_data = json.dumps(tenders, indent=4, ensure_ascii=False).encode(
            "utf-8"
        )
        st.download_button(
            label="📥 Download JSON (.json)",
            data=json_data,
            file_name="extracted_tenders.json",
            mime="application/json",
            use_container_width=True,
        )
    else:
      st.error(
          "No tenders were extracted. Please check terminal logs for details."
      )

# ==============================================================================
# TAB 3: Saved Tenders Database
# ==============================================================================
with tab_history:
  st.subheader("📊 Saved Tenders Database (Offline View)")
  st.write("Browse and filter existing tenders extracted from previous runs.")

  if not df_existing.empty:
    search_keyword = st.text_input(
        "Filter by keyword (Title, Organisation, Tender ID):", "", key="filter_keyword"
    )

    df_filtered = df_existing.copy()
    if search_keyword:
      kw = search_keyword.lower()
      df_filtered = df_filtered[
          df_filtered.apply(
              lambda row: any(kw in str(val).lower() for val in row), axis=1
          )
      ]

    st.write(f"Showing **{len(df_filtered)}** of **{len(df_existing)}** tenders")
    st.dataframe(df_filtered, use_container_width=True, height=500)

    # Allow copy-paste or quick search of any row
    st.divider()
    st.caption(
        "💡 To open any expired tender link, copy its **Tender ID** from the"
        " table above, paste it into the **Search by Tender ID** tab, and"
        " click **Search & Redirect**."
    )
  else:
    st.info(
        "No saved tenders file ('extracted_tenders.csv') found yet. Run the"
        " scraper in Tab 2 to populate this view!"
    )
