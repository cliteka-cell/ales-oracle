import os
import re
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
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
    # Convert backtick-wrapped content to inline LaTeX (Gemini sometimes uses backticks for math)
    text = re.sub(r'`([^`]+)`', r'$\1$', text)
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

# ── Kronometre / Zamanlayıcı ──────────────────────────────────────────────────
_dark = st.session_state.get("dark_mode", False)
_bg       = "#1e1e2e" if _dark else "#ffffff"
_card_bg  = "#2a2a3e" if _dark else "#f4f6f9"
_border   = "rgba(255,255,255,0.12)" if _dark else "rgba(0,0,0,0.12)"
_text     = "#e0e0e0" if _dark else "#333333"
_muted    = "#888" if _dark else "#666"
_input_bg = "rgba(255,255,255,0.07)" if _dark else "rgba(0,0,0,0.05)"

components.html(f"""
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
  body {{ background: {_bg}; padding: 4px 0 8px 0; }}
  .widget {{ border: 1px solid {_border}; border-radius: 12px; overflow: hidden; background: {_card_bg}; }}
  .header {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 9px 14px; cursor: pointer;
    background: rgba(41,128,185,0.15); user-select: none;
  }}
  .header-left {{ font-size: 13px; font-weight: 700; color: #4da6e0; display: flex; align-items: center; gap: 6px; }}
  .header-right {{ display: flex; align-items: center; gap: 10px; }}
  .mini-time {{ font-size: 13px; font-weight: 700; color: {_text}; display: none; }}
  .min-btn {{ background: none; border: 1px solid {_border}; color: {_muted}; cursor: pointer;
             font-size: 13px; padding: 1px 8px; border-radius: 5px; line-height: 1.4; }}
  .min-btn:hover {{ background: rgba(128,128,128,0.15); }}
  .body {{ padding: 12px 14px 14px; }}
  .tabs {{ display: flex; gap: 6px; margin-bottom: 10px; }}
  .tab {{ flex: 1; padding: 5px 0; text-align: center; font-size: 12px; border-radius: 7px; cursor: pointer;
         border: 1px solid {_border}; color: {_muted}; background: transparent; transition: all .15s; }}
  .tab.active {{ background: #2980b9; color: #fff; border-color: #2980b9; }}
  .display {{ text-align: center; font-size: 38px; font-weight: 800; color: {_text};
             letter-spacing: 3px; margin: 6px 0 10px; font-variant-numeric: tabular-nums; }}
  .display.warn {{ color: #e74c3c; }}
  .cd-row {{ display: none; align-items: center; justify-content: center; gap: 8px; margin-bottom: 8px; }}
  .cd-row label {{ font-size: 12px; color: {_muted}; }}
  .cd-row input {{ width: 64px; padding: 4px 8px; border-radius: 6px; border: 1px solid {_border};
                  background: {_input_bg}; color: {_text}; font-size: 13px; text-align: center; }}
  .controls {{ display: flex; gap: 8px; }}
  .btn {{ flex: 1; padding: 7px 0; border: none; border-radius: 8px; cursor: pointer;
         font-size: 13px; font-weight: 700; transition: background .15s; }}
  .btn-go  {{ background: #27ae60; color: #fff; }}
  .btn-go:hover  {{ background: #2ecc71; }}
  .btn-stop {{ background: #c0392b; color: #fff; }}
  .btn-stop:hover {{ background: #e74c3c; }}
  .btn-rst {{ background: {_input_bg}; color: {_muted}; border: 1px solid {_border}; }}
  .btn-rst:hover {{ background: rgba(128,128,128,0.2); }}
</style>
<div class="widget">
  <div class="header" onclick="toggleMin()">
    <div class="header-left">⏱ <span id="modeLabel">Kronometre</span></div>
    <div class="header-right">
      <span class="mini-time" id="miniTime">00:00</span>
      <button class="min-btn" id="minBtn" onclick="event.stopPropagation();toggleMin()">—</button>
    </div>
  </div>
  <div class="body" id="body">
    <div class="tabs">
      <button class="tab active" id="t1" onclick="setMode('sw')">⏱ Kronometre</button>
      <button class="tab"        id="t2" onclick="setMode('cd')">⏳ Geri Sayım</button>
    </div>
    <div class="cd-row" id="cdRow">
      <label>Dakika:</label>
      <input type="number" id="minInput" value="30" min="1" max="180">
    </div>
    <div class="display" id="disp">00:00</div>
    <div class="controls">
      <button class="btn btn-go" id="goBtn" onclick="toggle()">▶ Başlat</button>
      <button class="btn btn-rst" onclick="reset()">↺ Sıfırla</button>
    </div>
  </div>
</div>
<script>
  let mode = 'sw', running = false, iv = null, secs = 0, minimized = false;

  function fmt(s) {
    const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), sc = s%60;
    return (h ? String(h).padStart(2,'0')+':' : '') +
           String(m).padStart(2,'0') + ':' + String(sc).padStart(2,'0');
  }
  function setDisp(s) {
    document.getElementById('disp').textContent = fmt(s);
    document.getElementById('disp').className = 'display' + (mode==='cd' && s<=60 && s>0 ? ' warn':'');
    document.getElementById('miniTime').textContent = fmt(s);
  }
  function setMode(m) {
    mode = m; reset();
    document.getElementById('t1').className = 'tab'+(m==='sw'?' active':'');
    document.getElementById('t2').className = 'tab'+(m==='cd'?' active':'');
    document.getElementById('cdRow').style.display = m==='cd' ? 'flex':'none';
    document.getElementById('modeLabel').textContent = m==='sw' ? 'Kronometre':'Geri Sayım';
  }
  function toggle() {
    if (running) {
      clearInterval(iv); running = false;
      document.getElementById('goBtn').textContent = '▶ Devam';
      document.getElementById('goBtn').className = 'btn btn-go';
    } else {
      if (mode==='cd' && secs===0) secs = parseInt(document.getElementById('minInput').value)*60;
      running = true;
      document.getElementById('goBtn').textContent = '⏸ Durdur';
      document.getElementById('goBtn').className = 'btn btn-stop';
      iv = setInterval(()=>{
        mode==='sw' ? secs++ : secs--;
        setDisp(secs);
        if (mode==='cd' && secs<=0) {
          clearInterval(iv); running=false; secs=0;
          document.getElementById('disp').textContent='Süre Doldu!';
          document.getElementById('goBtn').textContent='▶ Başlat';
          document.getElementById('goBtn').className='btn btn-go';
        }
      },1000);
    }
  }
  function reset() {
    clearInterval(iv); running=false; secs=0;
    setDisp(0);
    document.getElementById('goBtn').textContent='▶ Başlat';
    document.getElementById('goBtn').className='btn btn-go';
  }
  function toggleMin() {
    minimized = !minimized;
    document.getElementById('body').style.display = minimized ? 'none':'block';
    document.getElementById('miniTime').style.display = minimized ? 'inline':'none';
    document.getElementById('minBtn').textContent = minimized ? '+' : '—';
  }
</script>
""", height=220)

# ── Soru üret ────────────────────────────────────────────────────────────────
if st.button("✨ Soru Oluştur", type="primary", use_container_width=True):

    st.session_state.pop("sorular_ham", None)
    st.session_state.pop("cevaplar_ham", None)

    prompt = f"""Sen bir ALES sınavı soru yazarısın.
'{konu}' konusunda, {zorluk_aciklama[zorluk]} zorluk seviyesinde 5 özgün ALES sorusu yaz.

ZORUNLU KURALLAR:
- Her soru gerçek ALES formatında olsun (4 şık: A, B, C, D)
- Matematik için SADECE inline LaTeX kullan: $formül$ şeklinde — ASLA backtick (`) kullanma
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