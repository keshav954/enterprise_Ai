from dotenv import load_dotenv
from google import genai
import os

print("Step 1")

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print("API Loaded:", api_key is not None)

client = genai.Client(api_key=api_key)

print("Step 2")

try:
    for model in client.models.list():
        print(model.name)
except Exception as e:
    print("ERROR:")
    print(type(e).__name__)
    print(e)

print("Finished")