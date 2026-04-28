import os
import re
import time
import json
from pathlib import Path
import pandas as pd
from google import genai
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

MIN_SORU_SAYISI = 5

# 1. Veriyi Hazırla
print("📂 Veritabanı yükleniyor...")
df = pd.read_csv(ROOT / "database" / "ales_soru_veritabani_tum_sinavlar.csv")
sozel_keywords = ['Paragraf', 'Sözel', 'Anlam', 'Cümle', 'Sıralama']
df_sayisal = df[~df['Ana Konu'].str.contains('|'.join(sozel_keywords), na=False)].dropna(subset=['Soru Metni'])

konu_frekanslari = df_sayisal['Ana Konu'].value_counts()
konular = konu_frekanslari[konu_frekanslari >= MIN_SORU_SAYISI].index.tolist()
print(f"✅ {len(konular)} konu bulundu, analiz başlıyor...\n")

# 2. Gemini Client
GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
client = genai.Client(api_key=GOOGLE_API_KEY)

# 3. Her konu için Gemini analizi
CHECKPOINT_FILE = ROOT / "outputs" / "formul_kartlari_checkpoint.json"

if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        konu_kartlari = json.load(f)
    tamamlanan = {k['konu'] for k in konu_kartlari}
    print(f"♻️  Checkpoint bulundu: {len(konu_kartlari)} konu tamamlanmış, devam ediliyor...\n")
else:
    konu_kartlari = []
    tamamlanan = set()

for i, konu in enumerate(konular, 1):
    if konu in tamamlanan:
        print(f"[{i}/{len(konular)}] {konu} — atlandı")
        continue

    sorular = df_sayisal[df_sayisal['Ana Konu'] == konu]['Soru Metni'].tolist()
    soru_sayisi = len(sorular)
    soru_metinleri = "\n".join(f"{j+1}. {s}" for j, s in enumerate(sorular))

    print(f"[{i}/{len(konular)}] {konu} ({soru_sayisi} soru)...")

    prompt = f"""ALES sınavında '{konu}' konusundan çıkmış {soru_sayisi} gerçek soru aşağıda verilmiştir.
Bu soruları analiz et ve aşağıdaki yapıda kısa, net bir formül kartı oluştur.

ZORUNLU FORMAT KURALLARI:
- Matematik için SADECE $...$ (inline) veya $$...$$ (display) kullan
- $ işaretinin her iki yanında MUTLAKA boşluk bırak: "alan $a$ ve $b$" ✓, "alan$a$" ✗
- Değişken adlarını daima math modunda yaz: $a$ ve $b$, asla düz metin olarak yazma
- Türkçe açıklama metnini ve LaTeX'i ASLA birleştirme: "dikkenarlar $a$, $b$" ✓, "dikkenarlar$a,b$" ✗
- Kelimeler arasında boşluk bırak, kelimeleri birleştirme
- Liste için markdown tire kullan (- madde), asla LaTeX list ortamı kullanma
- Açıklamalar sade Türkçe, formüller LaTeX

## Kritik Formüller
(her satır: $formül$ — kısa Türkçe açıklama)

## Sık Çıkan Kalıplar
(bu konuda ALES nasıl soru soruyor, 3-4 madde)

## Hızlı Çözüm Taktikleri
(sınavda zaman kazandıran kısayollar, 3-5 madde)

SORULAR:
{soru_metinleri}"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt]
        )
        if not response.text:
            raise ValueError("Boş yanıt döndü")
        # Ham markdown'ı sakla — HTML'e dönüştürme tarayıcıda yapılacak
        konu_kartlari.append({
            'konu': konu,
            'soru_sayisi': soru_sayisi,
            'markdown': response.text
        })
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(konu_kartlari, f, ensure_ascii=False, indent=2)
        print(f"   ✅ Tamamlandı")
    except Exception as e:
        print(f"   ❌ Hata: {e}")

    time.sleep(1)

# 4. HTML Oluştur — marked.js + KaTeX ile client-side render
kartlar_json = json.dumps(konu_kartlari, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>ALES Formül Kartları</title>

    <!-- KaTeX -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>

    <!-- marked.js -->
    <script src="https://cdn.jsdelivr.net/npm/marked@12/marked.min.js"></script>

    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            font-size: 15px;
            line-height: 1.7;
            color: #333;
            background: #eef2f7;
            padding: 30px 20px;
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            font-size: 1.8em;
            margin-bottom: 6px;
        }}
        .alt-baslik {{
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(440px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .kart {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        .kart-baslik {{
            background: #2980b9;
            color: white;
            padding: 12px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .konu-adi {{ font-weight: bold; font-size: 1em; }}
        .rozet {{
            background: rgba(255,255,255,0.25);
            border-radius: 12px;
            padding: 2px 10px;
            font-size: 0.8em;
            white-space: nowrap;
        }}
        .kart-icerik {{ padding: 16px 18px; }}
        .kart-icerik h2 {{
            font-size: 0.82em;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: #2980b9;
            border-bottom: 1px solid #e8ecf0;
            padding-bottom: 5px;
            margin: 16px 0 9px;
        }}
        .kart-icerik h2:first-child {{ margin-top: 0; }}
        .kart-icerik h3 {{ font-size: 0.95em; color: #d35400; margin: 10px 0 5px; }}
        .kart-icerik p {{ font-size: 0.9em; margin-bottom: 6px; }}
        .kart-icerik ul, .kart-icerik ol {{ padding-left: 20px; }}
        .kart-icerik li {{ font-size: 0.9em; margin-bottom: 4px; }}
        .kart-icerik strong {{ color: #2c3e50; }}
        .kart-icerik .katex {{ font-size: 1em; }}
        .kart-icerik .katex-display {{ margin: 8px 0; overflow-x: auto; }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            font-size: 0.8em;
            color: #aaa;
        }}
    </style>
</head>
<body>
    <h1>📐 ALES Sayısal Formül Kartları</h1>
    <p class="alt-baslik" id="alt-baslik"></p>
    <div class="grid" id="grid"></div>
    <div class="footer">ALES Oracle Sistemi tarafından oluşturulmuştur.</div>

    <script>
        const kartlar = {kartlar_json};

        document.getElementById('alt-baslik').textContent =
            kartlar.length + ' konu · Frekansa göre sıralı · Gerçek sınav sorularından üretildi';

        const grid = document.getElementById('grid');

        kartlar.forEach(kart => {{
            const div = document.createElement('div');
            div.className = 'kart';
            div.innerHTML = `
                <div class="kart-baslik">
                    <span class="konu-adi">${{kart.konu}}</span>
                    <span class="rozet">${{kart.soru_sayisi}} soru</span>
                </div>
                <div class="kart-icerik">${{marked.parse(kart.markdown)}}</div>
            `;
            grid.appendChild(div);
        }});

        // KaTeX defer ile yükleniyor — DOMContentLoaded'dan sonra render et
        document.addEventListener('DOMContentLoaded', function() {{
            document.querySelectorAll('.kart-icerik').forEach(el => {{
                renderMathInElement(el, {{
                    delimiters: [
                        {{left: '$$', right: '$$', display: true}},
                        {{left: '$', right: '$', display: false}},
                        {{left: '\\\\(', right: '\\\\)', display: false}},
                        {{left: '\\\\[', right: '\\\\]', display: true}}
                    ],
                    throwOnError: false
                }});
            }});
        }});
    </script>
</body>
</html>"""

output_path = ROOT / "outputs" / "ALES_Formul_Kartlari.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

if os.path.exists(CHECKPOINT_FILE):
    os.remove(CHECKPOINT_FILE)

print(f"\n✅ BİTTİ! {len(konu_kartlari)} formül kartı oluşturuldu.")
print(f"📄 Dosya: {output_path}")
print("👉 Tarayıcıda aç, Yazdır → PDF yap.")
