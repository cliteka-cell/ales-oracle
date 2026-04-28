import os
import json
from pathlib import Path
import pandas as pd
from google import genai
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

# 1. Veriyi Hazırla
print("📂 Sayısal veritabanı taranıyor...")
df = pd.read_csv(ROOT / "database" / "ales_soru_veritabani_tum_sinavlar.csv")
sozel_keywords = ['Paragraf', 'Sözel', 'Anlam', 'Cümle', 'Sıralama']
df_sayisal = df[~df['Ana Konu'].str.contains('|'.join(sozel_keywords), na=False)].dropna(subset=['Soru Metni'])

tum_metinler = "\n".join(df_sayisal['Soru Metni'].astype(str).tolist())

# 2. Gemini Analizi
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
client = genai.Client(api_key=GOOGLE_API_KEY)

prompt = f"""
Aşağıdaki ALES sayısal sorularını analiz et ve kapsamlı bir 'Sayısal Strateji Rehberi' oluştur.
TÜM önemli formülleri, denklem şablonlarını ve mantıksal çözüm yollarını çıkar.

Lütfen şu yapıyı kullan:
- Başlık: Konu Adı
- Formüller: LaTeX formatında (Örn: $a^2 + b^2 = c^2$)
- Soru Kalıbı: Sınavda bu konu nasıl soruluyor?
- Çözüm Stratejisi: En hızlı nasıl çözülür?

ZORUNLU FORMAT KURALLARI:
- Matematik için SADECE $...$ (inline) veya $$...$$ (display) kullan
- $ işaretinin her iki yanında MUTLAKA boşluk bırak: "değer $a$ ve $b$" ✓, "değer$a$" ✗
- Parantez içi notları parantez dışındaki kelimeye yapıştırma: "örn: ($4 = 2^2$)" ✓, "örn:$4=22$" ✗
- Türkçe açıklama metnini LaTeX ile birleştirme, aralarında boşluk bırak
- Liste için markdown tire kullan (- madde), asla LaTeX list ortamı kullanma
- Kelimeler arasında boşluk bırak, kelimeleri birleştirme

SORU METİNLERİ:
{tum_metinler}
"""

print("🧠 Gemini tüm sınavları analiz ediyor (13 sınavlık derin analiz)...")
try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[prompt]
    )
    if not response.text:
        raise ValueError("Gemini boş yanıt döndürdü.")
except Exception as e:
    print(f"❌ API hatası: {e}")
    raise

# Ham markdown'ı JS'e göm — render tarayıcıda yapılacak
icerik_json = json.dumps(response.text, ensure_ascii=False)

# 3. HTML Sayfası Oluştur
html_template = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>ALES Sayısal Strateji Rehberi</title>

    <!-- KaTeX -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>

    <!-- marked.js -->
    <script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>

    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 16px; line-height: 1.7; color: #333; max-width: 900px; margin: 40px auto; padding: 20px; background-color: #f4f7f6; }}
        .report-card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        h1 {{ font-size: 1.8em; color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ font-size: 1.3em; color: #2980b9; margin-top: 30px; border-left: 5px solid #3498db; padding-left: 15px; }}
        h3 {{ font-size: 1.1em; color: #d35400; margin-top: 20px; }}
        h4, h5, h6 {{ font-size: 1em; color: #555; }}
        p, li {{ font-size: 1em; }}
        ul, ol {{ padding-left: 22px; }}
        li {{ margin-bottom: 4px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        code {{ background: #f0f0f0; padding: 2px 5px; border-radius: 3px; font-size: 0.9em; }}
        strong {{ color: #2c3e50; }}
        .katex {{ font-size: 1em; }}
        .katex-display {{ margin: 10px 0; overflow-x: auto; }}
        .footer {{ margin-top: 50px; text-align: center; font-size: 0.8em; color: #7f8c8d; }}
    </style>
</head>
<body>
    <div class="report-card">
        <h1>📊 ALES SAYISAL STRATEJİ REHBERİ</h1>
        <p style="text-align: center;"><em>13 Sınavın Analizi ile Hazırlanmış Formül ve Kalıp Sözlüğü</em></p>
        <hr>
        <div class="content" id="icerik"></div>
        <div class="footer">ALES Oracle Sistemi tarafından oluşturulmuştur.</div>
    </div>

    <script>
        const metin = {icerik_json};
        document.getElementById('icerik').innerHTML = marked.parse(metin);

        document.addEventListener('DOMContentLoaded', function() {{
            renderMathInElement(document.getElementById('icerik'), {{
                delimiters: [
                    {{left: '$$', right: '$$', display: true}},
                    {{left: '$', right: '$', display: false}},
                    {{left: '\\\\(', right: '\\\\)', display: false}},
                    {{left: '\\\\[', right: '\\\\]', display: true}}
                ],
                throwOnError: false
            }});
        }});
    </script>
</body>
</html>"""

# 4. Dosyayı Kaydet
output_path = ROOT / "outputs" / "ALES_Strateji_Raporu.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_template)

print("\n✅ ANALİZ BİTTİ!")
print(f"Dosya oluşturuldu: {output_path}")
print("👉 Tarayıcıda aç, Yazdır → PDF yap.")
