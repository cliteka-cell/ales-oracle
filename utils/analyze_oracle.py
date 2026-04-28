import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Veriyi Yükle
dosya_adi = "ales_soru_veritabani_tum_sinavlar.csv"
df = pd.read_csv(dosya_adi)

# 2. Veri Temizliği
# Sadece numaraların veya boşlukların olduğu (konusu olmayan) satırları atıyoruz
df = df.dropna(subset=['Ana Konu'])

# Konu isimlerinde küçük/büyük harf veya boşluk farklılıklarını standartlaştırıyoruz 
# (Örn: "Üslü sayılar" ile "Üslü Sayılar" aynı sayılsın diye)
df['Ana Konu'] = df['Ana Konu'].astype(str).str.strip().str.title()
df['Soru Tipi'] = df['Soru Tipi'].astype(str).str.strip().str.title()

print(f"\n📊 Toplam işlenen geçerli soru sayısı: {len(df)}")

# 3. İSTATİSTİK 1: En Çok Çıkan Konular (Bankolar)
top_konular = df['Ana Konu'].value_counts().head(15)

print("\n🔥 ALES'İN EN ÇOK SORULAN 15 KONUSU (BANKO KONULAR) 🔥")
print("-" * 50)
print(top_konular)

# 4. İSTATİSTİK 2: Soru Tiplerinin Dağılımı
soru_tipleri = df['Soru Tipi'].value_counts()
print("\n📋 SORU TİPİ DAĞILIMI")
print("-" * 50)
print(soru_tipleri)

# 5. Görselleştirme (Grafik Çizimi)
plt.figure(figsize=(12, 8))
# Seaborn ile şık bir bar grafiği çiziyoruz
sns.barplot(x=top_konular.values, y=top_konular.index, hue=top_konular.index, legend=False, palette="viridis")

# Grafiğe başlık ve etiketler ekliyoruz
plt.title("ALES - En Çok Çıkan 15 Konu (Tüm Sınavların Analizi)", fontsize=16, fontweight='bold')
plt.xlabel("Toplam Soru Sayısı", fontsize=12)
plt.ylabel("Konular", fontsize=12)
plt.grid(axis='x', linestyle='--', alpha=0.7)

# Grafiği bilgisayara kaydediyoruz
plt.tight_layout()
grafik_adi = "ales_banko_konular_grafigi.png"
plt.savefig(grafik_adi, dpi=300)

print(f"\n✅ Analiz tamamlandı! Harika bir grafik oluşturuldu ve '{grafik_adi}' ismiyle kaydedildi.")