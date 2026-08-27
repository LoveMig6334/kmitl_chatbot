import os

from dotenv import load_dotenv
from openai import OpenAI

from thai_llm_kmitl.models import DEFAULT_MODEL, MODELS

load_dotenv()

api_key = os.environ.get("THAILLM_API_KEY")
if not api_key:
    raise SystemExit("THAILLM_API_KEY is not set. Copy .env.example to .env and fill it in.")

client = OpenAI(
    base_url=os.environ.get("THAILLM_BASE_URL", "http://thaillm.or.th/api/v1"),
    api_key=api_key,
    default_headers={"User-Agent": "thai-llm-kmitl/0.1"},
)

print("Available models:", ", ".join(MODELS))

# Make the chat completion request
response = client.chat.completions.create(
    model=DEFAULT_MODEL,
    messages=[
        {"role": "user", "content": "สวัสดี ใครคือนายกไทยคนปัจจุบัน หาข้อมูล"}
    ],
    max_tokens=2048,
    temperature=0.3,
)

print(response.choices[0].message.content)
