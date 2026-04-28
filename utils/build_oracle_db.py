import os
import csv
import json
import time
from pathlib import Path
from google import genai
from PIL import Image
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

# Tüm sınavların olduğu ANA klasör
base_folder = ROOT / "exam_images_dataset"
output_csv = ROOT / "database" / "ales_soru_veritabani_tum_sinavlar.csv"

# 2. Daha önce işlenen dosyaları bul (Kaldığı yerden devam etme özelliği)
islenmis_sayfalar = set()
if os.path.exists(output_csv):
    with open(output_csv, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader, None) # Başlığı atla
        for row in reader:
            if len(row) >= 2:
                # Klasör ve dosya adını birleştirerek kaydet (Örn: 2017_ALES/page_1.png)
                islenmis_sayfalar.add(f"{row[0]}/{row[1]}")

prompt = """
Sen uzman bir ALES sınav analizörüsün. Sana verilen bu sınav sayfasındaki soruları incele.
Sayfadaki her bir soru için aşağıdaki JSON formatında, geçerli bir JSON array (dizisi) döndür.
Soru olmayan, sadece açıklama veya cevap anahtarı olan kısımları yoksay.
Başka hiçbir açıklama yazma, SADECE JSON çıktısı ver:

[
  {
    "soru_no": "Soru Numarası (Sadece rakam)",
    "soru_metni": "Sorunun kısa özeti veya denklemi",
    "ana_konu": "Tek bir temel matematik, mantık veya Türkçe konusu (Örn: Rasyonel Sayılar, Yaş Problemleri, Sözel Mantık, Paragrafta Anlam)",
    "soru_tipi": "Salt İşlem, Problemler, Tablo/Grafik Okuma, Paragraf veya Yeni Nesil Mantık"
  }
]
"""

file_exists = os.path.exists(output_csv)
with open(output_csv, mode='a', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    
    if not file_exists:
        writer.writerow(["Sınav Yılı", "Sayfa Dosyası", "Soru No", "Soru Metni", "Ana Konu", "Soru Tipi"])

    # Ana klasördeki tüm sınav alt klasörlerini bul
    exam_folders = sorted([f.path for f in os.scandir(base_folder) if f.is_dir()])
    
    print(f"Toplam {len(exam_folders)} sınav klasörü bulundu. Fabrika çalışıyor...\n")

    for exam_dir in exam_folders:
        exam_name = os.path.basename(exam_dir)
        print(f"\n📂 BAŞLIYOR: {exam_name}")
        
        # Sayfaları sayısal sıraya diz
        image_files = sorted(
            [f for f in os.listdir(exam_dir) if f.endswith('.png')],
            key=lambda x: int(x.replace('page_', '').replace('.png', ''))
        )
        
        for img_file in image_files:
            unique_id = f"{exam_name}/{img_file}"
            
            if unique_id in islenmis_sayfalar:
                print(f"⏩ Atlanıyor: {unique_id}")
                continue

            img_path = os.path.join(exam_dir, img_file)
            print(f"Okunuyor: {unique_id} ...", end=" ", flush=True)
            
            try:
                image = Image.open(img_path)
                
                # Zeki modele ve hızlı akışa geçtik!
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[image, prompt]
                )
                
                raw_text = response.text.replace("```json", "").replace("```", "").strip()
                
                if raw_text:
                    sorular = json.loads(raw_text)
                    for soru in sorular:
                        writer.writerow([
                            exam_name,
                            img_file,
                            soru.get("soru_no", ""),
                            soru.get("soru_metni", ""),
                            soru.get("ana_konu", ""),
                            soru.get("soru_tipi", "")
                        ])
                    print("✅ Başarılı!")
                else:
                    print("⚠️ Soru bulunamadı.")
                
                # Sadece 2 saniye bekliyoruz (Ücretli planda olduğumuz için limit derdimiz yok)
                time.sleep(2) 
                
            except Exception as e:
                print(f"\n❌ Hata: {e}")
                # Beklenmeyen bir hata olursa 10 saniye dinlenip yola devam etsin
                time.sleep(10)

print(f"\n🎉 TÜM SINAVLAR TAMAMLANDI! Veriler '{output_csv}' dosyasına kaydedildi.")