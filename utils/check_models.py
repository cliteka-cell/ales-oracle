import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

print("Senin API anahtarınla erişilebilen modeller listeleniyor...\n")

# Google'ın sunucusundaki tüm modelleri çekip isimlerini yazdırıyoruz
for model in client.models.list():
    print(model.name)