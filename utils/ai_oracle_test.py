import os
from pathlib import Path
from google import genai
from PIL import Image
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

# 2. Test Edilecek Görseli Seç
image_path = ROOT / "exam_images_dataset" / "2017_ALES_Ilkbahar" / "page_3.png"

if os.path.exists(image_path):
    print(f"Görsel yükleniyor: {image_path}")
    image = Image.open(image_path)
    
    # 3. Prompt Engineering (Sistem Talimatı)
    prompt = """
    Sen uzman bir ALES sınav analizörüsün. Sana verilen bu sınav sayfasındaki soruları dikkatlice incele.
    Sayfadaki her bir soru için sırasıyla aşağıdaki bilgileri çıkar:

    Soru [Soru Numarası]:
    - Soru Metni: [Sorunun anlaşılır, kısa bir özeti. Formüller varsa düz metin olarak belirt]
    - Ana Konu: [Sadece tek bir temel matematik veya mantık konusu. Örn: "Üslü Sayılar", "Yaş Problemleri", "Sözel Mantık", "Geometri - Üçgenler", "Olasılık"]
    - Soru Tipi: [Örn: "Salt İşlem", "Problemler", "Tablo/Grafik Okuma", "Yeni Nesil Mantık"]
    
    Sayfadaki tüm soruları bu formata göre listele.
    """

    print("Gemini 2.5 Flash yapay zekası görseli analiz ediyor, lütfen bekleyin...")
    
    # 4. Yeni API Çağrısı
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[image, prompt]
    )
    
    # 5. Sonucu Ekrana Bas
    print("\n" + "="*40)
    print("🔮 ALES ORACLE TEST SONUCU")
    print("="*40)
    print(response.text)
else:
    print(f"HATA: Görsel dosyası bulunamadı. Lütfen yolun doğru olduğundan emin ol: {image_path}")