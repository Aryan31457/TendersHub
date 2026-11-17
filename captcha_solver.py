import base64
import os
import re
from config import (
    AI_PROVIDER,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_MODEL,
)
from google import genai
from google.genai import types
from openai import OpenAI


def solve_captcha_with_ai(
    page,
    captcha_img_selector="img#captchaImage, img[id*='captcha' i], img[src*='captcha']",
):
  """Takes a targeted screenshot of the CAPTCHA element and routes it

  to either Gemini or Qwen based on the AI_PROVIDER environment setting.
  Preserves strict case-sensitivity and uses fast low-latency models.
  """
  print(f"[LOG] Capturing screenshot of CAPTCHA element...")

  captcha_element = page.locator(captcha_img_selector).first
  screenshot_path = "temp_captcha.png"
  captcha_element.screenshot(path=screenshot_path)
  print(f"[LOG] CAPTCHA screenshot captured successfully to '{screenshot_path}'.")

  solved_text = ""

  prompt_text = (
      "Read the alphanumeric text inside this CAPTCHA image accurately.\n"
      "IMPORTANT: This CAPTCHA is strictly CASE-SENSITIVE. Preserve the exact"
      " uppercase and lowercase casing for every character (do NOT change"
      " lowercase to uppercase or vice versa).\n"
      "Return ONLY the exact characters of the code with no spaces, quotes,"
      " punctuation, or conversational filler."
  )

  try:
    if AI_PROVIDER == "gemini":
      if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing in your .env file.")

      client = genai.Client(api_key=GEMINI_API_KEY)
      with open(screenshot_path, "rb") as f:
        image_bytes = f.read()

      part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")

      primary_model = GEMINI_MODEL or "gemini-3-flash-preview"
      candidate_models = [primary_model]
      for m in ["gemini-3-flash-preview", "gemini-3.8-flash", "gemini-3.1-flash-lite"]:
        if m not in candidate_models:
          candidate_models.append(m)

      last_error = None
      for model_name in candidate_models:
        try:
          print(f"[LOG] Sending CAPTCHA image to AI agent (Gemini - {model_name})...")
          response = client.models.generate_content(
              model=model_name,
              contents=[part, prompt_text],
          )
          raw_text = response.text or ""
          # Extract only the code from response text if model added filler
          cleaned = raw_text.strip().replace(" ", "").replace("`", "").replace("'", "").replace('"', "")
          # If model returned something like "Thecodeis:ABC12", extract the code
          if ":" in cleaned:
            cleaned = cleaned.split(":")[-1].strip()
          solved_text = cleaned
          if solved_text:
            break
        except Exception as e:
          print(f"[LOG] Model '{model_name}' encountered latency/error ({e}), trying fallback...")
          last_error = e

      if not solved_text and last_error:
        raise last_error

    elif AI_PROVIDER == "qwen":
      if not QWEN_API_KEY:
        raise ValueError("QWEN_API_KEY is missing in your .env file.")

      model_name = QWEN_MODEL or "qwen-vl-max"
      print(f"[LOG] Sending CAPTCHA image to AI agent (Qwen - {model_name})...")

      client = OpenAI(api_key=QWEN_API_KEY, base_url=QWEN_BASE_URL)

      with open(screenshot_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

      response = client.chat.completions.create(
          model=model_name,
          messages=[
              {
                  "role": "user",
                  "content": [
                      {
                          "type": "image_url",
                          "image_url": {
                              "url": f"data:image/png;base64,{base64_image}"
                          },
                      },
                      {"type": "text", "text": prompt_text},
                  ],
              }
          ],
      )
      raw_text = response.choices[0].message.content or ""
      cleaned = raw_text.strip().replace(" ", "").replace("`", "").replace("'", "").replace('"', "")
      if ":" in cleaned:
        cleaned = cleaned.split(":")[-1].strip()
      solved_text = cleaned

    else:
      raise ValueError(
          f"Invalid AI_PROVIDER '{AI_PROVIDER}'. Choose either 'gemini' or"
          " 'qwen'."
      )

  finally:
    # Cleanup temporary local screenshot file
    if os.path.exists(screenshot_path):
      try:
        os.remove(screenshot_path)
      except Exception:
        pass

  print(
      f"[LOG] AI agent responded with CAPTCHA: '{solved_text}'"
      " (Case-Sensitive preserved)"
  )
  return solved_text
