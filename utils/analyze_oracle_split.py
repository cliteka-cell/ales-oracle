import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("ales_soru_veritabani_tum_sinavlar.csv")
df = df.dropna(subset=['Ana Konu'])
df['Ana Konu'] = df['Ana Konu'].astype(str).str.strip().str.title()

# Sayısal ve Sözel konuları ayırmak için anahtar kelimeler
sozel_keywords = ['Paragraf', 'Sözel', 'Anlam', 'Cümle', 'Sıralama', 'Boşluk Doldurma', 'Anlatım']

# Basit bir filtreleme ile ikiye bölüyoruz
df_sozel = df[df['Ana Konu'].str.contains('|'.join(sozel_keywords))]
df_sayisal = df[~df['Ana Konu'].str.contains('|'.join(sozel_keywords))]

def plot_top_10(data, title, filename, color):
    top_10 = data['Ana Konu'].value_counts().head(10)
    plt.figure(figsize=(10, 6))
    sns.barplot(x=top_10.values, y=top_10.index, palette=color)
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel("Soru Sayısı")
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    print(f"✅ {title} grafiği kaydedildi: {filename}")

# İki ayrı grafik oluştur
plot_top_10(df_sayisal, "ALES SAYISAL - En Çok Çıkan 10 Konu", "ales_sayisal_banko.png", "magma")
plot_top_10(df_sozel, "ALES SÖZEL - En Çok Çıkan 10 Konu", "ales_sozel_banko.png", "mako")

# Terminal çıktısı
print("\n🔢 SAYISAL TOP 10:")
print(df_sayisal['Ana Konu'].value_counts().head(10))
print("\n✍️ SÖZEL TOP 10:")
print(df_sozel['Ana Konu'].value_counts().head(10))