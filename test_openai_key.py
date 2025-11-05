from openai import OpenAI
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Read API key
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ No OPENAI_API_KEY found in .env file")
    exit()

# Initialize client
client = OpenAI(api_key=api_key)

print("✅ Testing OpenAI API key...")

try:
    # Send a simple test prompt
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say hello"}],
        max_tokens=5
    )
    print("✅ API key is valid. Response:")
    print(response.choices[0].message.content)

except Exception as e:
    print("❌ OpenAI API error:")
    print(e)
