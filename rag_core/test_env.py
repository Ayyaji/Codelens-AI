import os
from dotenv import load_dotenv

load_dotenv()

groq_api = os.getenv("GROQ_API")

print("Testing .env configuration")
print("="*50)

if groq_api:
    print(f"✅ GROQ_API found: {groq_api[:20]}...{groq_api[-10:]}")
    print(f"   Length: {len(groq_api)} characters")
else:
    print("❌ GROQ_API not found in .env file")
    print("\nCheck:")
    print("1. Does .env file exist in project root?")
    print("2. Does it contain: GROQ_API=your_key_here")
    print("3. No spaces around the = sign")

print("="*50)