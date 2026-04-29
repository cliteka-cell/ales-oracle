import os
import re
from pathlib import Path
import pandas as pd
import streamlit as st
from google import genai
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

# ── Sayfa ayarları ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ALES Oracle",
    page_icon="📐",
    layout="centered"
)

# ── Giriş ekranı ─────────────────────────────────────────────────────────────
def giris_ekrani():
    st.title("📐 ALES Oracle")
    st.caption("Devam etmek için giriş yapın")
    with st.form("login_form"):
        kullanici = st.text_input("Kullanıcı adı")
        sifre = st.text_input("Şifre", type="password")
        giris = st.form_submit_button("Giriş Yap", use_container_width=True)
    if giris:
        if (kullanici == st.secrets["USERNAME"] and sifre == st.secrets["PASSWORD"]):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Kullanıcı adı veya şifre hatalı.")

if not st.session_state.get("authenticated"):
    giris_ekrani()
    st.stop()

col_title, col_theme = st.columns([5, 1])
with col_title:
    st.title("📐 ALES Oracle — Soru Üretici")
    st.caption("Gerçek sınav verisiyle eğitilmiş konu bazlı pratik sistemi")
with col_theme:
    st.write("")  # dikey hizalama için boşluk
    dark = st.toggle("🌙", value=st.session_state.get("dark_mode", False))
    st.session_state["dark_mode"] = dark

if st.session_state.get("dark_mode"):
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background-color: #1e1e2e; color: #e0e0e0; }
        [data-testid="stSidebar"] { background-color: #2a2a3e; }
        [data-testid="stHeader"] { background-color: #1e1e2e; }
        div[data-testid="stVerticalBlock"] div[data-testid="stHorizontalBlock"] { background-color: transparent; }
        .stSelectbox label, .stSlider label { color: #e0e0e0 !important; }
        div[data-baseweb="select"] > div { background-color: #2a2a3e !important; color: #e0e0e0 !important; }
        div[data-testid="stContainer"] { background-color: #2a2a3e !important; border-color: #444466 !important; }
        .stButton button { background-color: #2980b9; color: white; }
    </style>
    """, unsafe_allow_html=True)


# ── Yardımcı: LaTeX olmayan çevre komutlarını temizle ────────────────────────
def temizle(text: str) -> str:
    text = re.sub(r'\\begin\{itemize\}|\\end\{itemize\}', '', text)
    text = re.sub(r'\\begin\{enumerate\}|\\end\{enumerate\}', '', text)
    text = re.sub(r'\\item\s*', '- ', text)
    text = re.sub(r'\\textbf\{(.+?)\}', r'**\1**', text)
    text = re.sub(r'\\text\{(.+?)\}', r'\1', text)
    # Convert numbered list lines (e.g. "1. foo") to dashes to avoid markdown ordered list rendering
    text = re.sub(r'(?m)^\s*\d+\.\s+', '- ', text)
    return text.strip()


# ── Soruları parse et: her soru ayrı kart ────────────────────────────────────
def sorulari_ayristir(text: str):
    text = temizle(text)
    bloklar = re.split(r'\*\*Soru\s*(\d+)\*\*', text)
    sorular = []
    for i in range(1, len(bloklar), 2):
        no = bloklar[i]
        icerik = bloklar[i + 1].strip() if i + 1 < len(bloklar) else ""
        # A) B) C) D) dört şıkkın art arda geldiği bloğu ara
        # '\n' + icerik ile A) satır başında olmasa da yakalarız
        sik_match = re.search(
            r'\n(A\)[^\n]+)\n(B\)[^\n]+)\n(C\)[^\n]+)\n(D\)[^\n]+)',
            '\n' + icerik
        )
        if sik_match:
            metin = icerik[:sik_match.start()].strip()
            siklar = [sik_match.group(g).strip() for g in range(1, 5)]
        else:
            metin = icerik
            siklar = []
        sorular.append({'no': no, 'metin': metin, 'siklar': siklar})
    return sorular


def soru_karti_goster(soru: dict):
    with st.container(border=True):
        st.markdown(f"**:blue[SORU {soru['no']}]**")
        st.markdown(soru['metin'])
        if soru['siklar']:
            col1, col2 = st.columns(2)
            for i, sik in enumerate(soru['siklar']):
                with (col1 if i % 2 == 0 else col2):
                    st.markdown(sik)


def cevap_karti_goster(no: str, icerik: str):
    with st.container(border=True):
        st.markdown(f"**:green[SORU {no} — Çözüm]**")
        st.markdown(icerik)


# ── Cevapları parse et ────────────────────────────────────────────────────────
def cevaplari_ayristir(text: str):
    text = temizle(text)
    bloklar = re.split(r'\*\*Soru\s*(\d+)\*\*', text)
    cevaplar = {}
    for i in range(1, len(bloklar), 2):
        no = bloklar[i]
        icerik = bloklar[i + 1].strip() if i + 1 < len(bloklar) else ""
        cevaplar[no] = icerik
    return cevaplar


# ── Veri yükle ───────────────────────────────────────────────────────────────
@st.cache_data
def konulari_yukle():
    df = pd.read_csv(ROOT / "database" / "ales_soru_veritabani_tum_sinavlar.csv")
    sozel_keywords = ['Paragraf', 'Sözel', 'Anlam', 'Cümle', 'Sıralama']
    df_sayisal = df[
        ~df['Ana Konu'].str.contains('|'.join(sozel_keywords), na=False)
    ].dropna(subset=['Soru Metni'])
    frekanslar = df_sayisal['Ana Konu'].value_counts()
    konular = frekanslar[frekanslar >= 5].index.tolist()
    return konular, df_sayisal

konular, df_sayisal = konulari_yukle()

# ── Gemini client ─────────────────────────────────────────────────────────────
@st.cache_resource
def gemini_client():
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    return genai.Client(api_key=api_key)

client = gemini_client()

# ── Kontroller ────────────────────────────────────────────────────────────────
konu = st.selectbox("Konu seç", options=konular, help="En çok çıkan konular üstte")

zorluk = st.select_slider(
    "Zorluk seviyesi",
    options=["Kolay", "Orta", "Zor"],
    value="Orta"
)

zorluk_aciklama = {
    "Kolay": "doğrudan formül uygulama, tek adımlı işlem",
    "Orta": "birden fazla adım gerektiren, formülleri birleştiren",
    "Zor": "çok adımlı, sezgi ve yorum gerektiren, tuzak seçenek içeren",
}

ornek_sorular = df_sayisal[df_sayisal['Ana Konu'] == konu]['Soru Metni'].tolist()[:10]
ornek_metin = "\n".join(f"- {s}" for s in ornek_sorular)

# ── Soru üret ────────────────────────────────────────────────────────────────
if st.button("✨ Soru Oluştur", type="primary", use_container_width=True):
    st.session_state.pop("sorular_ham", None)
    st.session_state.pop("cevaplar_ham", None)

    prompt = f"""Sen bir ALES sınavı soru yazarısın.
'{konu}' konusunda, {zorluk_aciklama[zorluk]} zorluk seviyesinde 5 özgün ALES sorusu yaz.

ZORUNLU KURALLAR:
- Her soru gerçek ALES formatında olsun (4 şık: A, B, C, D)
- Matematik için SADECE inline LaTeX kullan: $formül$ şeklinde
- Soru metninde liste gerekiyorsa tire ile yaz (- madde), ASLA numaralı liste (1. 2. 3.) veya \\begin{{itemize}} kullanma
- Şıkları ayrı satırlara yaz: A) ... B) ... C) ... D) ...

Referans sorular (bu konudan gerçek sınavda çıkmış):
{ornek_metin}

ÇIKTI FORMATI — tam olarak bu yapıya uyu, başka bir şey ekleme:

**Soru 1**
[soru metni buraya]
A) [şık]
B) [şık]
C) [şık]
D) [şık]

**Soru 2**
...

(Cevap anahtarını YAZMA)"""

    with st.spinner(f"{konu} — {zorluk} sorular hazırlanıyor..."):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt]
            )
            if not response.text:
                st.error("Gemini boş yanıt döndürdü, tekrar deneyin.")
            else:
                st.session_state["sorular_ham"] = response.text
                st.session_state["konu"] = konu
                st.session_state["zorluk"] = zorluk
        except Exception as e:
            st.error(f"API hatası: {e}")

# ── Soruları göster ───────────────────────────────────────────────────────────
if "sorular_ham" in st.session_state:
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📝 {st.session_state['konu']} — {st.session_state['zorluk']}")
    with col2:
        if st.button("🔄 Yenile", use_container_width=True):
            st.session_state.pop("sorular_ham", None)
            st.session_state.pop("cevaplar_ham", None)
            st.rerun()

    sorular = sorulari_ayristir(st.session_state["sorular_ham"])
    if sorular:
        for soru in sorular:
            soru_karti_goster(soru)
    else:
        # Parse başarısız olursa ham metni göster
        st.markdown(temizle(st.session_state["sorular_ham"]))

    # ── Cevap anahtarı ────────────────────────────────────────────────────────
    st.divider()
    if st.button("✅ Cevap Anahtarını Göster", use_container_width=True):
        cevap_prompt = f"""Aşağıdaki ALES sorularının cevap anahtarını ve adım adım çözümünü ver.

ZORUNLU KURALLAR:
- Her soru için önce "Doğru cevap: X)" yaz
- Sonra adım adım çözümü yaz (kısa ve net, 3-5 adım)
- Matematik için SADECE inline LaTeX: $formül$
- Liste için Markdown (- madde), ASLA \\begin{{itemize}} kullanma

ÇIKTI FORMATI:

**Soru 1**
Doğru cevap: [şık]
- Adım 1: ...
- Adım 2: ...
- Sonuç: ...

**Soru 2**
...

SORULAR:
{st.session_state['sorular_ham']}"""

        with st.spinner("Çözümler hazırlanıyor..."):
            try:
                cevap_resp = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[cevap_prompt]
                )
                st.session_state["cevaplar_ham"] = cevap_resp.text
            except Exception as e:
                st.error(f"API hatası: {e}")

    if "cevaplar_ham" in st.session_state:
        st.subheader("📖 Cevap Anahtarı & Çözümler")
        cevaplar = cevaplari_ayristir(st.session_state["cevaplar_ham"])
        if cevaplar:
            for no, icerik in cevaplar.items():
                cevap_karti_goster(no, icerik)
        else:
            st.markdown(temizle(st.session_state["cevaplar_ham"]))

#python3 -m streamlit run scripts/app.py