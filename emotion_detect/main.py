import streamlit as st
import pickle
import re
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from collections import Counter
import io
import urllib.parse

try:
    from streamlit_lottie import st_lottie
except Exception:
    st_lottie = None

try:
    import requests
except Exception:
    requests = None

# Sayfa Ayarları
st.set_page_config(
    page_title="Müzik Duygu Analizi",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "history" not in st.session_state:
    st.session_state["history"] = []
if "lyrics" not in st.session_state:
    st.session_state["lyrics"] = ""
if "last_result" not in st.session_state:
    st.session_state["last_result"] = None

def _get_query_params():
    try:
        return dict(st.query_params)
    except Exception:
        try:
            return st.experimental_get_query_params()
        except Exception:
            return {}

def _set_query_params(params: dict):
    try:
        st.query_params.clear()
        for k, v in params.items():
            st.query_params[k] = v
    except Exception:
        try:
            st.experimental_set_query_params(**params)
        except Exception:
            pass

_qp = _get_query_params()
if not st.session_state["lyrics"] and isinstance(_qp, dict) and _qp.get("lyrics"):
    try:
        raw = _qp.get("lyrics")
        if isinstance(raw, list):
            raw = raw[0]
        st.session_state["lyrics"] = urllib.parse.unquote_plus(str(raw))
    except Exception:
        pass

palette_by_emotion = {
    "mutlu": ("rgba(250,204,21,0.22)", "rgba(34,197,94,0.16)"),
    "üzgün": ("rgba(59,130,246,0.22)", "rgba(99,102,241,0.16)"),
    "aşk": ("rgba(236,72,153,0.24)", "rgba(244,63,94,0.16)"),
    "öfke": ("rgba(239,68,68,0.22)", "rgba(249,115,22,0.16)"),
    "korku": ("rgba(168,85,247,0.20)", "rgba(30,41,59,0.22)"),
    "umut": ("rgba(34,197,94,0.20)", "rgba(56,189,248,0.16)"),
    "melankoli": ("rgba(148,163,184,0.18)", "rgba(99,102,241,0.14)"),
}

_last_pred = None
if isinstance(st.session_state.get("last_result"), dict):
    _last_pred = st.session_state["last_result"].get("prediction")

_a1, _a2 = palette_by_emotion.get(str(_last_pred), ("rgba(139,92,246,0.24)", "rgba(236,72,153,0.16)"))

_css = """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap');

      :root {
        --card-bg: rgba(255,255,255,0.06);
        --card-border: rgba(255,255,255,0.12);
        --shadow: 0 10px 30px rgba(0,0,0,0.25);
        --accent: __ACCENT__;
        --accent2: __ACCENT2__;
        --text-soft: rgba(255,255,255,0.85);
        --text: rgba(255,255,255,0.94);
      }

      @keyframes bg-pan {
        0%   { background-position: 0% 0%,   100% 20%, 0% 0%; }
        50%  { background-position: 35% 20%, 60%  0%, 100% 0%; }
        100% { background-position: 0% 0%,   100% 20%, 0% 0%; }
      }

      @keyframes float-in {
        from { transform: translateY(6px); opacity: 0; }
        to   { transform: translateY(0px); opacity: 1; }
      }

      @keyframes glow {
        0% { box-shadow: 0 10px 26px rgba(0,0,0,0.25); }
        50% { box-shadow: 0 14px 34px rgba(139,92,246,0.25), 0 10px 26px rgba(236,72,153,0.18); }
        100% { box-shadow: 0 10px 26px rgba(0,0,0,0.25); }
      }

      @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        40% { transform: translateY(-6px); }
        70% { transform: translateY(-2px); }
      }

      @keyframes blob-move-1 {
        0% { transform: translate(-10%, -10%) scale(1); }
        50% { transform: translate(8%, 12%) scale(1.12); }
        100% { transform: translate(-10%, -10%) scale(1); }
      }
      @keyframes blob-move-2 {
        0% { transform: translate(10%, -8%) scale(1); }
        50% { transform: translate(-6%, 10%) scale(1.10); }
        100% { transform: translate(10%, -8%) scale(1); }
      }
      @keyframes shimmer {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
      }
      @keyframes eq {
        0%, 100% { transform: scaleY(0.35); opacity: 0.85; }
        50% { transform: scaleY(1.0); opacity: 1; }
      }

      [data-testid="stAppViewContainer"] {
        background: radial-gradient(1200px 600px at 10% 0%, rgba(139,92,246,0.35), transparent 60%),
                    radial-gradient(900px 500px at 90% 20%, rgba(236,72,153,0.28), transparent 55%),
                    linear-gradient(135deg, #0b1220 0%, #070a13 45%, #0b1220 100%);
        background-size: 140% 140%, 140% 140%, 200% 200%;
        animation: bg-pan 18s ease-in-out infinite;
      }

      .bg-blobs {
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
      }
      .blob {
        position: absolute;
        width: 520px;
        height: 520px;
        border-radius: 999px;
        filter: blur(50px);
        opacity: 0.35;
        mix-blend-mode: screen;
      }
      .blob.one {
        left: -140px;
        top: -160px;
        background: radial-gradient(circle at 30% 30%, rgba(139,92,246,0.95), rgba(139,92,246,0.0) 60%);
        animation: blob-move-1 16s ease-in-out infinite;
      }
      .blob.two {
        right: -180px;
        top: 120px;
        background: radial-gradient(circle at 30% 30%, rgba(236,72,153,0.85), rgba(236,72,153,0.0) 60%);
        animation: blob-move-2 18s ease-in-out infinite;
      }
      .blob.three {
        left: 10%;
        bottom: -220px;
        width: 680px;
        height: 680px;
        opacity: 0.22;
        background: radial-gradient(circle at 30% 30%, rgba(56,189,248,0.85), rgba(56,189,248,0.0) 62%);
        animation: blob-move-2 20s ease-in-out infinite;
      }

      [data-testid="stHeader"] { background: transparent; }
      .block-container { padding-top: 1.0rem; padding-bottom: 2.5rem; }

      [data-testid="stMainBlockContainer"] {
        position: relative;
        z-index: 1;
      }

      html, body, [class*="css"], p, li, span, label {
        font-family: 'Poppins', system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif !important;
        color: var(--text) !important;
      }

      h1, h2, h3, h4 {
        color: rgba(255,255,255,0.98) !important;
      }

      [data-testid="stSidebar"] > div {
        background: radial-gradient(900px 520px at 20% 0%, var(--accent), transparent 55%),
                    radial-gradient(700px 420px at 80% 20%, var(--accent2), transparent 55%),
                    linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
        border-right: 1px solid rgba(255,255,255,0.10);
        backdrop-filter: blur(12px);
      }

      [data-testid="stSidebar"] > div::before {
        content: "";
        position: absolute;
        left: 0;
        top: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(90deg, var(--accent), var(--accent2));
        opacity: 0.95;
      }

      [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: rgba(255,255,255,0.98) !important;
      }

      [data-testid="stSidebar"] label {
        color: rgba(255,255,255,0.92) !important;
      }

      [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        background: linear-gradient(135deg, rgba(139,92,246,0.20), rgba(236,72,153,0.12));
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 12px;
        padding: 0.35rem 0.55rem;
        margin-bottom: 0.35rem;
      }

      [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
      [data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"] > div,
      [data-testid="stSidebar"] .stTextInput input,
      [data-testid="stSidebar"] .stNumberInput input,
      [data-testid="stSidebar"] .stTextArea textarea {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-radius: 14px !important;
      }

      [data-testid="stSidebar"] .stSlider [data-baseweb="slider"] {
        padding: 0.45rem 0.4rem;
        border-radius: 14px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.10);
      }

      [data-testid="stSidebar"] .stToggle {
        padding: 0.35rem 0.45rem;
        border-radius: 14px;
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.10);
      }

      [data-testid="stSidebar"] .stButton>button {
        width: 100%;
      }

      .app-hero {
        padding: 1.1rem 1.2rem;
        border-radius: 18px;
        border: 1px solid var(--card-border);
        background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
        box-shadow: var(--shadow);
        animation: float-in 420ms ease-out;
      }
      .app-hero h1 { margin: 0; font-size: 2.15rem; line-height: 1.15; letter-spacing: -0.02em; }
      .app-hero p { margin: 0.35rem 0 0 0; opacity: 0.92; color: var(--text-soft); }

      .hero-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
      }

      .hero-title {
        display: inline-block;
        background: linear-gradient(90deg, rgba(255,255,255,0.98), rgba(236,72,153,0.92), rgba(139,92,246,0.92), rgba(255,255,255,0.98));
        background-size: 240% 240%;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        animation: shimmer 6s ease-in-out infinite;
        text-shadow: 0 0 22px rgba(236,72,153,0.12);
      }

      .neo {
        text-shadow: 0 0 18px rgba(139,92,246,0.18), 0 0 24px rgba(236,72,153,0.12);
      }

      .eq {
        display: inline-flex;
        align-items: flex-end;
        gap: 5px;
        height: 28px;
        padding: 0.35rem 0.55rem;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(10px);
      }
      .eq span {
        width: 6px;
        height: 18px;
        transform-origin: bottom;
        border-radius: 999px;
        background: linear-gradient(180deg, rgba(56,189,248,1), rgba(139,92,246,1), rgba(236,72,153,0.95));
        animation: eq 1.1s ease-in-out infinite;
      }
      .eq span:nth-child(2) { animation-delay: -0.2s; }
      .eq span:nth-child(3) { animation-delay: -0.45s; }
      .eq span:nth-child(4) { animation-delay: -0.15s; }
      .eq span:nth-child(5) { animation-delay: -0.35s; }

      .card {
        padding: 1rem 1rem;
        border-radius: 18px;
        border: 1px solid var(--card-border);
        background: var(--card-bg);
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow);
        transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
        animation: float-in 420ms ease-out;
      }
      .card:hover {
        transform: translateY(-2px);
        border-color: rgba(255,255,255,0.20);
        box-shadow: 0 14px 34px rgba(0,0,0,0.30);
      }
      .muted { opacity: 0.85; color: var(--text-soft); }

      div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.10);
        padding: 0.75rem 0.9rem;
        border-radius: 18px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.18);
        transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
      }
      div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        border-color: rgba(255,255,255,0.18);
        box-shadow: 0 12px 26px rgba(0,0,0,0.22);
      }
      div[data-testid="stMetric"] label { opacity: 0.92; color: var(--text-soft); }

      .stTextArea textarea {
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.14) !important;
        background: rgba(255,255,255,0.04) !important;
      }

      .stButton>button {
        border-radius: 14px;
        padding: 0.6rem 1.0rem;
        border: 1px solid rgba(255,255,255,0.14);
        background: linear-gradient(135deg, rgba(139,92,246,0.95), rgba(236,72,153,0.92));
        color: white;
        box-shadow: 0 10px 26px rgba(0,0,0,0.25);
        transition: transform 160ms ease, filter 160ms ease;
        animation: glow 3.2s ease-in-out infinite;
      }
      .stButton>button:hover {
        transform: translateY(-1px);
        filter: brightness(1.05);
      }

      [data-testid="stTabs"] [role="tab"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 14px;
        margin-right: 0.35rem;
        padding: 0.35rem 0.75rem;
      }
      [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(139,92,246,0.28), rgba(236,72,153,0.18));
        border-color: rgba(255,255,255,0.16);
      }

      div[data-testid="stTabs"] button {
        font-weight: 650;
      }

      .emoji-bounce {
        display: inline-block;
        animation: bounce 1.6s ease-in-out infinite;
        filter: drop-shadow(0 12px 16px rgba(0,0,0,0.35));
      }
    </style>
    """

st.markdown(
    _css.replace("__ACCENT__", str(_a1)).replace("__ACCENT2__", str(_a2)),
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="bg-blobs">
      <div class="blob one"></div>
      <div class="blob two"></div>
      <div class="blob three"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

@st.cache_data(show_spinner=False)
def load_lottie_url(url: str):
    if requests is None:
        return None
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

hero_left, hero_right = st.columns([3.2, 1.2])
with hero_left:
    st.markdown(
        """
        <div class="app-hero">
          <div class="hero-top">
            <h1 class="hero-title">🎵 Şarkı Sözü Duygu Analizi</h1>
            <div class="eq" aria-hidden="true">
              <span></span><span></span><span></span><span></span><span></span>
            </div>
          </div>
          <p class="neo">Şarkı sözlerini yapıştır, duygusunu analiz edelim. Sonuçları olasılık dağılımıyla birlikte gör.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with hero_right:
    lottie_url = "https://assets2.lottiefiles.com/packages/lf20_jcikwtux.json"
    lottie_json = load_lottie_url(lottie_url)
    if st_lottie is not None and lottie_json is not None:
        st_lottie(lottie_json, height=150, key="hero_lottie")
    elif st_lottie is None:
        st.caption("Lottie için: pip install streamlit-lottie")

# Model ve Vectorizer
@st.cache_resource
def load_models():
    model = pickle.load(open('emotion_model.pkl', 'rb'))
    vectorizer = pickle.load(open('tfidf_vectorizer.pkl', 'rb'))
    return model, vectorizer

try:
    model, vectorizer = load_models()
except Exception:
    st.error(
        "Model dosyaları yüklenemedi. 'emotion_model.pkl' ve 'tfidf_vectorizer.pkl' dosyalarının çalışma dizininde olduğundan emin ol."
    )
    st.stop()

# Temizleme Fonksiyonu
def clean_lyrics(text):
    text = text.lower()

    text = re.sub(r"altyazı\s*m\.k\.", "", text)
    text = re.sub(r"m\.k\.", "", text)
    text = re.sub(r"\baltyazı\b", "", text)

    text = re.sub(r"[^a-zçğıöşü0-9?.!,']", " ", text)

    words = text.split()
    words = [w for w in words if len(w) > 1 or w in ["o", "mu", "mı", "ki"]]
    text = " ".join(words)

    text = re.sub(r"\s+", " ", text).strip()
    return text

def analyze_text(text: str):
    clean_text = clean_lyrics(text)
    vec_text = vectorizer.transform([clean_text])
    prediction = model.predict(vec_text)[0]

    prob_df = None
    best_prob = None
    try:
        probabilities = model.predict_proba(vec_text)[0]
        classes = model.classes_
        prob_df = (
            pd.DataFrame(
                {
                    "Duygu": classes,
                    "Olasılık (%)": [round(float(p) * 100, 2) for p in probabilities],
                }
            )
            .sort_values(by="Olasılık (%)", ascending=False)
            .reset_index(drop=True)
        )
        best_prob = float(prob_df.iloc[0]["Olasılık (%)"]) if len(prob_df) else None
    except Exception:
        prob_df = pd.DataFrame({"Duygu": [prediction], "Olasılık (%)": [None]})
        best_prob = None

    return {
        "clean": clean_text,
        "vec": vec_text,
        "prediction": prediction,
        "best_prob": best_prob,
        "prob_df": prob_df,
    }

def explain_prediction(vec_text, predicted_label, top_n: int = 18):
    if not hasattr(vectorizer, "get_feature_names_out"):
        return None
    if not hasattr(model, "coef_"):
        return None

    try:
        feature_names = vectorizer.get_feature_names_out()
        coef = model.coef_

        class_index = None
        if hasattr(model, "classes_"):
            class_index = list(model.classes_).index(predicted_label)
        if class_index is None:
            return None

        row = vec_text.tocsr()[0]
        idx = row.indices
        if idx is None or len(idx) == 0:
            return None

        weights = coef[class_index]
        contrib = row.data * weights[idx]
        df = pd.DataFrame(
            {
                "Kelime": feature_names[idx],
                "Katkı": contrib,
                "TFIDF": row.data,
            }
        ).sort_values("Katkı", ascending=False)

        pos = df.head(top_n).copy()
        neg = df.tail(top_n).sort_values("Katkı").copy()
        return {"positive": pos, "negative": neg}
    except Exception:
        return None

def split_segments(text: str):
    lines = [ln.strip() for ln in text.splitlines()]
    segments = []
    buff = []
    for ln in lines:
        if ln == "":
            if buff:
                segments.append(" ".join(buff).strip())
                buff = []
            continue
        buff.append(ln)
    if buff:
        segments.append(" ".join(buff).strip())
    segments = [s for s in segments if s]
    return segments

def keywords_from_clean_text(clean_text: str, top_n: int = 25):
    words = [w for w in re.findall(r"[a-zçğıöşü]+", clean_text.lower()) if len(w) > 2]
    counts = Counter(words)
    common = counts.most_common(top_n)
    return pd.DataFrame(common, columns=["Kelime", "Frekans"])

emojis = {
    "mutlu": "😊",
    "üzgün": "😢",
    "aşk": "❤️",
    "öfke": "😠",
    "korku": "😨",
    "umut": "🌅",
    "melankoli": "🍷",
}

examples = {
    "- Seç -": "",
    "Melankolik": "Yağmur iner sessizce, içimde bir boşluk var...",
    "Mutlu": "Güneş doğuyor, içim kıpır kıpır, bugün her şey güzel...",
    "Aşk": "Gözlerinde kayboldum, kalbim sana ait...",
    "Öfke": "Beni duymadın, yine aynı yalanlar, artık yeter...",
    "Umut": "Yarınlar var, yeniden başlarız, vazgeçmek yok...",
}

with st.sidebar:
    st.title("⚙️ Kontroller")
    selected_example = st.selectbox("Örnek söz yükle", list(examples.keys()))
    if selected_example != "- Seç -" and st.button("Örneği metin alanına koy"):
        st.session_state["lyrics"] = examples[selected_example]

    st.divider()
    min_chars = st.slider("Minimum karakter", min_value=30, max_value=300, value=60, step=10)
    show_clean_text = st.toggle("Temizlenmiş metni göster", value=True)
    show_table = st.toggle("Olasılık tablosunu göster", value=True)
    show_chart = st.toggle("Grafiği göster", value=True)
    top_k = st.slider("Grafikte gösterilecek duygu", min_value=3, max_value=15, value=7, step=1)

    st.divider()
    if st.button("🧽 Geçmişi temizle"):
        st.session_state["history"] = []
        st.session_state["last_result"] = None

    st.divider()
    st.subheader("📁 Dosya ile analiz")
    uploaded = st.file_uploader("TXT veya CSV yükle", type=["txt", "csv"], accept_multiple_files=False)
    batch_run = st.button("🚀 Dosyayı analiz et")

tab_input, tab_results, tab_history = st.tabs(["✍️ Girdi", "📊 Sonuçlar", "🗂️ Geçmiş"])

with tab_input:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📝 Şarkı sözlerini buraya yapıştır")
    with st.form("analysis_form", clear_on_submit=False):
        lyrics_input = st.text_area(
            "",
            height=260,
            placeholder="Örnek:\nSerin bir maviliğin uzaklığında kayboldum...",
            value=st.session_state["lyrics"],
        )
        submitted = st.form_submit_button("🔍 Analiz Et")
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        st.session_state["lyrics"] = lyrics_input

        if not lyrics_input.strip():
            st.warning("Lütfen şarkı sözlerini gir.")
        elif len(lyrics_input.strip()) < int(min_chars):
            st.warning(f"Metin çok kısa görünüyor. En az {min_chars} karakter öneriyorum.")
        else:
            with st.spinner("Duygular çözümleniyor..."):
                out = analyze_text(lyrics_input)
                clean_text = out["clean"]
                prediction = out["prediction"]
                best_prob = out["best_prob"] if out["best_prob"] is not None else 0.0
                prob_df = out["prob_df"]

            st.session_state["last_result"] = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "input": lyrics_input,
                "clean": clean_text,
                "prediction": prediction,
                "best_prob": best_prob,
                "prob_df": prob_df,
                "vec": out["vec"],
            }
            st.session_state["history"].insert(
                0,
                {
                    "timestamp": st.session_state["last_result"]["timestamp"],
                    "prediction": prediction,
                    "best_prob": best_prob,
                    "text_preview": (lyrics_input.strip().replace("\n", " ")[:80] + "...")
                    if len(lyrics_input.strip()) > 80
                    else lyrics_input.strip().replace("\n", " "),
                },
            )

            st.success("Analiz tamamlandı. 'Sonuçlar' sekmesine geçebilirsin.")
            st.rerun()

with tab_results:
    result = st.session_state.get("last_result")
    if not result:
        st.info("Henüz analiz yapılmadı. Önce 'Girdi' sekmesinden analiz et.")
    else:
        result_tabs = st.tabs(["✨ Özet", "🧠 Neden?", "🧩 Kıta/Satır", "🔑 Anahtarlar", "📤 Paylaş"])

        with result_tabs[0]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("📌 Baskın Duygu")
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                st.metric("Duygu", str(result["prediction"]).upper())
            with c2:
                st.metric("Güven", f"%{result['best_prob']:.2f}")
            with c3:
                st.markdown(
                    f"<div class='muted'>Etiket</div><div class='emoji-bounce' style='font-size:2.1rem; font-weight:700'>{emojis.get(result['prediction'], '✨')}</div>",
                    unsafe_allow_html=True,
                )
            st.markdown('</div>', unsafe_allow_html=True)

            if show_clean_text:
                st.subheader("🧹 Temizlenmiş Şarkı Sözleri")
                st.info(result["clean"])

            st.subheader("📊 Duygu Analizi")
            prob_df = result.get("prob_df")
            if prob_df is None or (hasattr(prob_df, "empty") and prob_df.empty):
                st.info("Bu analiz için olasılık dağılımı üretilemedi (model predict_proba desteklemiyor olabilir).")
            else:
                prob_df = prob_df.copy()
                if "Olasılık (%)" in prob_df.columns:
                    prob_df["Olasılık (%)"] = pd.to_numeric(prob_df["Olasılık (%)"], errors="coerce")

                if show_table:
                    st.dataframe(prob_df, use_container_width=True, hide_index=True)

                if show_chart:
                    chart_df = prob_df.dropna(subset=["Olasılık (%)"]).head(int(top_k)).set_index("Duygu")
                    if chart_df.empty:
                        st.info("Grafik için sayısal olasılık bilgisi bulunamadı.")
                    else:
                        st.bar_chart(chart_df)

        with result_tabs[1]:
            st.subheader("🧠 Neden bu duygu?")
            st.caption("Model destekliyorsa, tahmine en çok katkı yapan kelimeleri gösterir.")
            vec = result.get("vec")
            expl = explain_prediction(vec, result["prediction"], top_n=14) if vec is not None else None
            if expl is None:
                st.info("Bu model türünde açıklama (coef_) desteklenmiyor ya da vectorizer feature isimleri bulunamadı.")
            else:
                colp, coln = st.columns(2)
                with colp:
                    st.markdown("**Pozitif katkı (tahmini güçlendiren)**")
                    st.dataframe(expl["positive"], use_container_width=True, hide_index=True)
                with coln:
                    st.markdown("**Negatif katkı (tahmine ters)**")
                    st.dataframe(expl["negative"], use_container_width=True, hide_index=True)

        with result_tabs[2]:
            st.subheader("🧩 Kıta/Satır bazlı duygu")
            segments = split_segments(result["input"])
            if not segments or len(segments) == 1:
                st.info("Metni satır satır ayırmak için boş satırlarla kıtaları ayırabilirsin.")
            else:
                rows = []
                for i, seg in enumerate(segments, start=1):
                    out = analyze_text(seg)
                    rows.append(
                        {
                            "Parça": i,
                            "Metin": (seg[:80] + "...") if len(seg) > 80 else seg,
                            "Duygu": out["prediction"],
                            "Güven": out["best_prob"],
                        }
                    )
                seg_df = pd.DataFrame(rows)
                st.dataframe(seg_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "⬇️ Parça analizini CSV indir",
                    data=seg_df.to_csv(index=False).encode("utf-8"),
                    file_name="parca_duygu_analizi.csv",
                    mime="text/csv",
                )

        with result_tabs[3]:
            st.subheader("🔑 Anahtar kelimeler")
            kw_df = keywords_from_clean_text(result["clean"], top_n=30)
            ckw1, ckw2 = st.columns([1.2, 1])
            with ckw1:
                st.dataframe(kw_df, use_container_width=True, hide_index=True)
            with ckw2:
                st.bar_chart(kw_df.set_index("Kelime"))

            try:
                from wordcloud import WordCloud

                wc = WordCloud(width=900, height=420, background_color=None, mode="RGBA").generate(
                    " ".join(kw_df["Kelime"].tolist())
                )
                fig = plt.figure(figsize=(10, 4.5))
                plt.imshow(wc, interpolation="bilinear")
                plt.axis("off")
                st.pyplot(fig, clear_figure=True)
            except Exception:
                st.caption("WordCloud için: pip install wordcloud")

        with result_tabs[4]:
            st.subheader("📤 Paylaş")
            st.caption("Aşağıdaki link ile bu sözler otomatik dolu gelir.")
            enc = urllib.parse.quote_plus(result.get("input", ""))
            share_qs = f"?lyrics={enc}"
            st.code(share_qs)
            if st.button("Linki input'a yaz"):
                _set_query_params({"lyrics": enc})
                st.success("Query param güncellendi. Linki kopyalayabilirsin.")

    if batch_run and uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".txt"):
                content = uploaded.read().decode("utf-8", errors="ignore")
                texts = [t.strip() for t in content.split("\n\n") if t.strip()]
                df = pd.DataFrame({"lyrics": texts})
            else:
                df = pd.read_csv(uploaded)
                if "lyrics" not in df.columns:
                    df = df.rename(columns={df.columns[0]: "lyrics"})

            out_rows = []
            for i, row in df.iterrows():
                txt = str(row.get("lyrics", "")).strip()
                if not txt:
                    continue
                out = analyze_text(txt)
                out_rows.append(
                    {
                        "id": i,
                        "prediction": out["prediction"],
                        "best_prob": out["best_prob"],
                        "preview": (txt[:80] + "...") if len(txt) > 80 else txt,
                    }
                )
            out_df = pd.DataFrame(out_rows)
            st.session_state["history"].insert(
                0,
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "prediction": "BATCH",
                    "best_prob": None,
                    "text_preview": f"{uploaded.name} ({len(out_df)} satır)",
                },
            )
            st.success("Batch analiz tamamlandı. Sonuçları aşağıdan indirebilirsin.")
            st.dataframe(out_df, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Batch sonucu CSV indir",
                data=out_df.to_csv(index=False).encode("utf-8"),
                file_name="batch_duygu_analizi.csv",
                mime="text/csv",
            )
        except Exception as e:
            st.error(f"Dosya analizinde hata: {e}")

with tab_history:
    history = st.session_state.get("history", [])
    if not history:
        st.info("Geçmiş boş. Bir analiz yaptığında burada listelenecek.")
    else:
        hist_df = pd.DataFrame(history)
        st.dataframe(hist_df, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Geçmişi CSV indir",
            data=hist_df.to_csv(index=False).encode("utf-8"),
            file_name="duygu_analizi_gecmis.csv",
            mime="text/csv",
        )
