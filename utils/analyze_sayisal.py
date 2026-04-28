import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Veriyi Yükle
df = pd.read_csv("ales_soru_veritabani_tum_sinavlar.csv")
df = df.dropna(subset=['Ana Konu'])

# Sözel konuları ayıklamak için filtre (Bu konuları listeden çıkarıyoruz)
sozel_keywords = ['Paragraf', 'Sözel', 'Anlam', 'Cümle', 'Sıralama', 'Boşluk Doldurma', 'Anlatım', 'Dil Bilgisi', 'Düşünce']
df_sayisal = df[~df['Ana Konu'].str.contains('|'.join(sozel_keywords), case=False)].copy()

# Konu isimlerini standartlaştır
df_sayisal['Ana Konu'] = df_sayisal['Ana Konu'].str.strip().str.title()

# 2. İstatistik: Sayısal Banko Konular
sayisal_top_10 = df_sayisal['Ana Konu'].value_counts().head(10)

print("\n🔢 ALES SAYISAL - EN ÇOK SORULAN 10 KONU")
print("-" * 50)
print(sayisal_top_10)

# 3. Görselleştirme
plt.figure(figsize=(12, 7))
sns.barplot(x=sayisal_top_10.values, y=sayisal_top_10.index, hue=sayisal_top_10.index, palette="flare", legend=False)
plt.title("ALES Sayısal - Stratejik Soru Dağılımı (Top 10)", fontsize=15, fontweight='bold')
plt.xlabel("Toplam Soru Sayısı")
plt.ylabel("Sayısal Konular")
plt.grid(axis='x', linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig("sayisal_strateji_grafigi.png", dpi=300)

print("\n✅ Sayısal analiz grafiği 'sayisal_strateji_grafigi.png' olarak kaydedildi.")