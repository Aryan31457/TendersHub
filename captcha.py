def handle_manual_captcha(page):
  """Pauses script execution to let the user manually solve the CAPTCHA

  for the Active Tenders page.
  """
  print("\n" + "=" * 50)
  print("ACTION REQUIRED:")
  print("1. Look at the browser window.")
  print(
      "2. Verify sorting preference (e.g., Published Date) or leave defaults."
  )
  print("3. Solve the CAPTCHA and click 'Search'.")
  print("4. Wait until the Active Tenders results table loads at the bottom.")
  print("5. Come back to this terminal and press ENTER to continue.")
  print("=" * 50 + "\n")
  input()  # Waits for user confirmation