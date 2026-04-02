import os
import sys
from dotenv import load_dotenv

# Path to the .env file in the backend
env_path = r"c:\Users\HP\Documents\ISO20022 Validator new\iso20022generatorbackend\.env"
load_dotenv(env_path)

key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

print(f"ENV_PATH: {env_path}")
print(f"KEY_FOUND: {bool(key)}")
print(f"KEY_START: {key[:7] if key else 'None'}...")
print(f"MODEL: {model}")

if not key:
    print("ERROR: No OPENAI_API_KEY found.")
    sys.exit(1)

try:
    from openai import OpenAI
    client = OpenAI(api_key=key)
    print("Client initialized. Sending test request...")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=10
    )
    print(f"SUCCESS: {response.choices[0].message.content}")
except Exception as e:
    print(f"ERROR: {str(e)}")
