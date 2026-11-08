import os
import io
import json
import re
import random
import hashlib
from functools import lru_cache
from datetime import datetime, timedelta, timezone, time
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. PAGE SETUP & OBSIDIAN TECH UI
# ---------------------------------------------------------
st.set_page_config(
    page_title="Echoes Studio // Terminal v3.3",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
    header[data-testid="stHeader"] { background: transparent !important; height: 2.5rem !important; }
    .stApp {
        background-color: #080B11 !important;
        background-image: radial-gradient(circle at 50% -20%, #151e33 0%, #080B11 75%) !important;
        font-family: 'Space Grotesk', -apple-system, sans-serif !important;
        color: #E2E8F0 !important;
    }
    .block-container { padding-top: 4.2rem !important; padding-bottom: 3.5rem !important; max-width: 680px !important; }
    div[data-testid="stExpander"] {
        background: #0E1626 !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5) !important;
        overflow: hidden !important;
        margin-bottom: 1rem !important;
    }
    div[data-testid="stExpander"] summary {
        background: #111B30 !important;
        color: #38BDF8 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
        font-weight: 700 !important;
        padding: 12px 16px !important;
        border-bottom: 1px solid rgba(56, 189, 248, 0.15) !important;
    }
    label[data-testid="stWidgetLabel"] p {
        color: #94A3B8 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
    }
    .stTextInput>div>div>input, .stTextArea textarea, .stDateInput input, .stTimeInput input {
        background-color: #0A0F1D !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 8px !important;
        color: #F8FAFC !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 14px !important;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 50%, #075985 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(56, 189, 248, 0.4) !important;
        border-radius: 10px !important;
        height: 3.4rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        text-transform: uppercase !important;
        width: 100% !important;
    }
    .stButton>button:not([kind="primary"]) {
        background: #111B30 !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }
    .stDownloadButton>button {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        color: white !important;
        border-radius: 10px !important;
        height: 3.2rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        width: 100% !important;
    }
    .badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 6px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-green { background: rgba(16, 185, 129, 0.12); color: #34D399; border: 1px solid rgba(52, 211, 153, 0.25); }
    .badge-blue  { background: rgba(56, 189, 248, 0.12); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.25); }
    .badge-amber { background: rgba(245, 158, 11, 0.12); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.25); }
    .dot { width: 6px; height: 6px; border-radius: 50%; background-color: #34D399; box-shadow: 0 0 8px #34D399; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. PERSISTENCE ENGINE
# ---------------------------------------------------------
DATA_DIR = os.path.join(os.getcwd(), "data")
FONTS_DIR = os.path.join(os.getcwd(), "fonts")
BG_CACHE_DIR = os.path.join(DATA_DIR, "bg_cache")

for d in [DATA_DIR, FONTS_DIR, BG_CACHE_DIR]:
    os.makedirs(d, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "studio_db.json")
HANDLE_PATH = os.path.join(DATA_DIR, "channel_handle.txt")

http_session = requests.Session()
http_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
})

def load_db():
    defaults = {
        "scheduled_posts": [],
        "used_headlines": [],
        "used_backdrops": [],
        "last_philosopher": None,
        "last_scheduled_date": None,
        "default_time_ist": "17:30"
    }
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                defaults.update(data)
                return defaults
        except Exception:
            pass
    return defaults

def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

db = load_db()

def get_persistent_handle():
    if "CHANNEL_HANDLE" in st.secrets:
        return str(st.secrets["CHANNEL_HANDLE"]).strip()
    if os.path.exists(HANDLE_PATH):
        try:
            with open(HANDLE_PATH, "r", encoding="utf-8") as f:
                h = f.read().strip()
                if h: return h
        except Exception:
            pass
    return st.session_state.get("brand_handle", "@EchoesOfWisdomOfficial").strip()

def save_persistent_handle(h_val):
    clean = h_val.strip()
    if clean and not clean.startswith("@"):
        clean = "@" + clean
    st.session_state["brand_handle"] = clean
    try:
        with open(HANDLE_PATH, "w", encoding="utf-8") as f:
            f.write(clean)
    except Exception:
        pass

# ---------------------------------------------------------
# 3. CACHED FONTS
# ---------------------------------------------------------
@st.cache_resource(show_spinner=False)
def ensure_fonts_cached():
    sources = {
        "Cinzel_Bold": "https://fonts.gstatic.com/s/cinzel/v23/8vIQ776mE3tYOmt9_ZUC.ttf",
        "Cinzel_Reg": "https://fonts.gstatic.com/s/cinzel/v23/8vIQ776mE3tYOmt9_ZQ.ttf",
        "Cormorant_Italic": "https://fonts.gstatic.com/s/cormorantgaramond/v19/co3bmX5slCNuHLi8bLeY9MK7whWMhyjYpHtK.ttf"
    }
    for name, url in sources.items():
        path = os.path.join(FONTS_DIR, f"{name}.ttf")
        if not os.path.exists(path) or os.path.getsize(path) < 10000:
            try:
                res = http_session.get(url, timeout=5)
                if res.status_code == 200 and len(res.content) > 10000:
                    with open(path, "wb") as f:
                        f.write(res.content)
            except Exception:
                pass
    return True

ensure_fonts_cached()

@lru_cache(maxsize=32)
def get_font(name, size):
    path = os.path.join(FONTS_DIR, f"{name}.ttf")
    if os.path.exists(path) and os.path.getsize(path) > 10000:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

# ---------------------------------------------------------
# 4. UNICODE BOLD FORMATTER
# ---------------------------------------------------------
def to_unicode_bold(text):
    normal_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    bold_chars   = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    trans = str.maketrans(normal_chars, bold_chars)
    return text.translate(trans)

# ---------------------------------------------------------
# 5. CURATED VISUAL VAULT
# ---------------------------------------------------------
EXPANDED_VAULT = {
    "CLASSICAL_STATUE": [
        {"name": "Classical Roman Marble Bust in Shadow", "url": "https://images.unsplash.com/photo-1580136579312-94651dfd596d?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Chiaroscuro Hellenistic Bronze Philosopher", "url": "https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Weathered Greek Marble Profile", "url": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Winged Victory of Samothrace Drapery", "url": "https://images.unsplash.com/photo-1561214115-f2f134cc4912?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Pensive Stoic Thinker in Museum Hall", "url": "https://images.unsplash.com/photo-1554907984-15263bfd63bd?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "FINE_ART_PAINTING": [
        {"name": "Epic Classical Battle Chiaroscuro", "url": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Renaissance Council in Deep Candlelight", "url": "https://images.unsplash.com/photo-1582561424760-0321d75e81fa?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Dramatic Historic Colonnade Oil Painting", "url": "https://images.unsplash.com/photo-1544717302-de2939b7ef71?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Baroque Chiaroscuro Figure Study", "url": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "SEA_AND_CLIFFS": [
        {"name": "Rugged Sea Cliffs Against Storm Surge", "url": "https://images.unsplash.com/photo-1505118380757-91f5f5632de0?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Dark Volcanic Coast & Breaking Ocean Swell", "url": "https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Sheer Atlantic Ocean Cliff Edge", "url": "https://images.unsplash.com/photo-1476673160081-cf065607f449?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Nordic Basalt Waves at Dusk", "url": "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "CITADEL_AND_ARCHES": [
        {"name": "Roman Colosseum Arches at Twilight", "url": "https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Ancient Classical Stone Portico", "url": "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Atmospheric Stone Fortress Ruins", "url": "https://images.unsplash.com/photo-1564507592333-c60657eea523?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Sunken Roman Temple Columns", "url": "https://images.unsplash.com/photo-1529154036614-a60975f5c760?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "MISTY_FOREST": [
        {"name": "Dark Pine Forest in Heavy Fog", "url": "https://images.unsplash.com/photo-1511497584788-87676104235f?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Solitary Ancient Oak in Morning Mist", "url": "https://images.unsplash.com/photo-1473448912268-2022ce9509d8?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Misty Redwood Sunbeams in Silence", "url": "https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ]
}

# ---------------------------------------------------------
# 6. CADENCE HELPER
# ---------------------------------------------------------
def parse_time_str(t_str):
    try:
        parts = t_str.split(":")
        return time(int(parts[0]), int(parts[1]))
    except Exception:
        return time(17, 30)

def calculate_next_slot(base_date=None, target_time_str="17:30"):
    now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    sched_t = parse_time_str(target_time_str)
    if base_date:
        next_d = base_date + timedelta(days=1)
    else:
        last_d_str = db.get("last_scheduled_date")
        if last_d_str:
            try:
                last_d = datetime.strptime(last_d_str, "%Y-%m-%d").date()
                next_d = max(last_d + timedelta(days=1), now_ist.date())
            except ValueError:
                next_d = now_ist.date() + timedelta(days=1)
        else:
            next_d = now_ist.date() if now_ist.time() < sched_t else now_ist.date() + timedelta(days=1)
    return datetime.combine(next_d, sched_t)

# ---------------------------------------------------------
# 7. HIGH-CONVERSION RENDERING ENGINE
# ---------------------------------------------------------
def wrap_text(draw, text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words: continue
        cur = words[0]
        for w in words[1:]:
            if draw.textlength(f"{cur} {w}", font=font) <= max_width:
                cur = f"{cur} {w}"
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines

def fetch_image_resilient(chosen_url, backup_vault_items=None):
    url_hash = hashlib.md5(chosen_url.encode('utf-8')).hexdigest()
    cache_file = os.path.join(BG_CACHE_DIR, f"{url_hash}.jpg")

    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 5000:
        try:
            return Image.open(cache_file).convert("RGB")
        except Exception:
            pass

    candidates = [chosen_url]
    if backup_vault_items:
        candidates.extend([it["url"] for it in backup_vault_items if it.get("url") != chosen_url])

    for target in candidates[:2]:
        try:
            res = http_session.get(target, timeout=3.5)
            if res.status_code == 200 and len(res.content) > 5000:
                raw = Image.open(io.BytesIO(res.content))
                resized = raw.resize((1080, 1350), Image.Resampling.LANCZOS).convert("RGB")
                try: resized.save(cache_file, "JPEG", quality=90)
                except Exception: pass
                return resized
        except Exception:
            continue

    base = Image.new("RGB", (1080, 1350), (12, 16, 24))
    draw = ImageDraw.Draw(base)
    for y in range(0, 1350, 2):
        ratio = y / 1350.0
        r = int(10 + 18 * (1.0 - abs(ratio - 0.5) * 2))
        g = int(14 + 22 * (1.0 - abs(ratio - 0.5) * 2))
        b = int(24 + 36 * (1.0 - abs(ratio - 0.5) * 2))
        draw.line([(0, y), (1080, y)], fill=(r, g, b), width=2)
    return base

def stamp_brand(canvas, layout_mode="Classic Imperial"):
    w, h = 1080, 1350
    draw = ImageDraw.Draw(canvas)
    crest_f = get_font("Cinzel_Bold", 19)
    crest_t = "E C H O E S   O F   W I S D O M"
    
    if layout_mode == "Editorial Asymmetry":
        draw.text((100, 110), crest_t, font=crest_f, fill=(218, 175, 55, 230))
        draw.line([(100, 145), (280, 145)], fill=(218, 175, 55, 180), width=1)
    else:
        cw = draw.textlength(crest_t, font=crest_f)
        draw.text(((w - cw) // 2, 110), crest_t, font=crest_f, fill=(218, 175, 55, 230))
        draw.line([(w // 2 - 40, 145), (w // 2 + 40, 145)], fill=(218, 175, 55, 180), width=1)

def apply_analog_grain(img, intensity=10):
    arr = np.array(img).astype(np.int16)
    noise = np.random.normal(0, intensity, arr.shape).astype(np.int16)
    noisy_arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(noisy_arr, "RGB")

def render_post_canvas(bg_img, post_data, layout_mode="Classic Imperial", show_dilemma_strip=True, enable_grain=True):
    w, h = 1080, 1350
    canvas = bg_img.convert("RGBA")

    # Fast Vectorized Scrim
    y_coords = np.arange(h)
    dist = np.abs(y_coords - h * 0.52) / (h * 0.52)
    alpha = (45 + 125 * (1.0 - dist ** 1.8)).clip(25, 210).astype(np.uint8)
    scrim_arr = np.zeros((h, w, 4), dtype=np.uint8)
    scrim_arr[:, :, 0] = 6
    scrim_arr[:, :, 1] = 8
    scrim_arr[:, :, 2] = 12
    scrim_arr[:, :, 3] = alpha[:, None]
    scrim = Image.fromarray(scrim_arr, "RGBA")
    canvas = Image.alpha_composite(canvas, scrim)

    stamp_brand(canvas, layout_mode)
    draw = ImageDraw.Draw(canvas)

    cat_f = get_font("Cinzel_Bold", 24)
    clean_cat = post_data.get('category', 'INNER CITADEL').strip().upper()

    # -------------------------------------------------------------
    # LAYOUT OPTION A: CLASSIC IMPERIAL (CENTERED & RELIEF)
    # -------------------------------------------------------------
    if layout_mode == "Classic Imperial":
        # Category Pill
        cw = draw.textlength(clean_cat, font=cat_f)
        cx, cy = (w - cw) // 2, 230
        draw.text((cx + 1, cy + 1), clean_cat, font=cat_f, fill=(0, 0, 0, 220))
        draw.text((cx, cy), clean_cat, font=cat_f, fill=(218, 175, 55, 255))
        draw.line([(cx - 48, cy + 13), (cx - 12, cy + 13)], fill=(218, 175, 55, 210), width=2)
        draw.line([(cx + cw + 12, cy + 13), (cx + cw + 48, cy + 13)], fill=(218, 175, 55, 210), width=2)

        # Chiseled Headline
        hl_f = get_font("Cinzel_Bold", 86)
        hl_lines = wrap_text(draw, post_data['headline'].upper(), hl_f, 880)
        line_h = int(86 * 1.25)
        start_y = 390 if len(hl_lines) >= 2 else 450

        for i, line in enumerate(hl_lines):
            lw = draw.textlength(line, font=hl_f)
            lx = (w - lw) // 2
            ly = start_y + i * line_h
            # Dual-pass chiseled relief
            draw.text((lx + 3, ly + 5), line, font=hl_f, fill=(0, 0, 0, 240))
            draw.text((lx - 1, ly - 1), line, font=hl_f, fill=(218, 175, 55, 120))
            draw.text((lx, ly), line, font=hl_f, fill=(255, 253, 242, 255))

        div_y = start_y + (len(hl_lines) * line_h) + 25
        draw.line([(w // 2 - 70, div_y), (w // 2 + 70, div_y)], fill=(218, 175, 55, 220), width=2)

        # Body Text
        body_f = get_font("Cormorant_Italic", 42)
        body_lines = wrap_text(draw, f'"{post_data["body_text"].strip()}"', body_f, 840)
        by = div_y + 35
        for bl in body_lines:
            bw = draw.textlength(bl, font=body_f)
            bx = (w - bw) // 2
            draw.text((bx + 2, by + 3), bl, font=body_f, fill=(0, 0, 0, 230))
            draw.text((bx, by), bl, font=body_f, fill=(240, 244, 250, 255))
            by += int(42 * 1.34)

        # Attribution
        att_f = get_font("Cinzel_Bold", 23)
        clean_att = post_data.get('attribution', 'SENECA').strip().upper()
        aw = draw.textlength(clean_att, font=att_f)
        ax, ay = (w - aw) // 2, by + 25
        draw.text((ax + 1, ay + 1), clean_att, font=att_f, fill=(0, 0, 0, 220))
        draw.text((ax, ay), clean_att, font=att_f, fill=(218, 175, 55, 255))
        draw.line([(ax - 40, ay + 12), (ax - 10, ay + 12)], fill=(218, 175, 55, 210), width=1)
        draw.line([(ax + aw + 10, ay + 12), (ax + aw + 40, ay + 12)], fill=(218, 175, 55, 210), width=1)

    # -------------------------------------------------------------
    # LAYOUT OPTION B: EDITORIAL ASYMMETRY (LEFT-ANCHORED POST)
    # -------------------------------------------------------------
    else:
        # Vertical Gold Accent Axis
        draw.line([(70, 200), (70, 1050)], fill=(218, 175, 55, 210), width=3)
        
        # Category
        cy = 210
        draw.text((100, cy), clean_cat, font=cat_f, fill=(218, 175, 55, 240))

        # Headline (Left-aligned)
        hl_f = get_font("Cinzel_Bold", 82)
        hl_lines = wrap_text(draw, post_data['headline'].upper(), hl_f, 780)
        line_h = int(82 * 1.25)
        hy = 290

        for line in hl_lines:
            draw.text((103, hy + 4), line, font=hl_f, fill=(0, 0, 0, 240))
            draw.text((100, hy), line, font=hl_f, fill=(255, 253, 242, 255))
            hy += line_h

        # Body Quote
        body_f = get_font("Cormorant_Italic", 42)
        body_lines = wrap_text(draw, f'"{post_data["body_text"].strip()}"', body_f, 760)
        by = hy + 30
        for bl in body_lines:
            draw.text((102, by + 3), bl, font=body_f, fill=(0, 0, 0, 230))
            draw.text((100, by), bl, font=body_f, fill=(240, 244, 250, 255))
            by += int(42 * 1.34)

        # Attribution
        att_f = get_font("Cinzel_Bold", 24)
        clean_att = f"— {post_data.get('attribution', 'MARCUS AURELIUS').strip().upper()}"
        draw.text((100, by + 25), clean_att, font=att_f, fill=(218, 175, 55, 255))

    # -------------------------------------------------------------
    # ON-CANVAS DILEMMA STRIP (Bottom Feed Conversion Trigger)
    # -------------------------------------------------------------
    if show_dilemma_strip and post_data.get("choice_1"):
        d_box = Image.new("RGBA", (w, 140), (8, 12, 18, 220))
        canvas.alpha_composite(d_box, (0, 1170))
        draw = ImageDraw.Draw(canvas)
        draw.line([(0, 1170), (w, 1170)], fill=(56, 189, 248, 180), width=1)

        q_font = get_font("Cinzel_Bold", 18)
        c_font = get_font("Cinzel_Bold", 20)

        dq_text = post_data.get("debate_question", "WHICH DISCIPLINE DO YOU CHOOSE?").strip().upper()
        qw = draw.textlength(dq_text, font=q_font)
        draw.text(((w - qw) // 2, 1185), dq_text, font=q_font, fill=(148, 163, 184, 255))

        c1 = f"1. {post_data.get('choice_1', '').strip().upper()}"
        c2 = f"2. {post_data.get('choice_2', '').strip().upper()}"
        combined_c = f"{c1}   |   {c2}"
        cw_d = draw.textlength(combined_c, font=c_font)
        draw.text(((w - cw_d) // 2, 1235), combined_c, font=c_font, fill=(255, 253, 242, 255))

    final_rgb = canvas.convert("RGB")
    if enable_grain:
        final_rgb = apply_analog_grain(final_rgb, intensity=8)
    return final_rgb

# ---------------------------------------------------------
# 8. CAPTION COMPOSER
# ---------------------------------------------------------
def format_high_conversion_caption(raw_hook, lesson, quote, attribution, deb_q, choice1, choice2, tags, brand_handle=None):
    if not brand_handle:
        brand_handle = get_persistent_handle()
    clean_hook = re.sub(r'[^\w\s]', '', raw_hook).strip().upper()
    bold_hook = to_unicode_bold(clean_hook)

    caption_lines = [
        f"⚡ {bold_hook} 🏛️",
        "",
        lesson.strip(),
        "",
        f'"{quote.strip()}" — {attribution.strip()}',
        "",
        f"🤔 {deb_q.strip()}",
        f"1️⃣ {choice1.strip()}",
        f"2️⃣ {choice2.strip()}",
        "",
        "Drop 1 or 2 below. 👇",
        "",
        f"• Follow {brand_handle} for timeless clarity.",
        "",
        f"{tags.strip()}"
    ]
    return "\n".join(caption_lines)

# ---------------------------------------------------------
# 9. TACTICAL AI SYNTHESIS (SUB-SECOND FLASH)
# ---------------------------------------------------------
PHILOSOPHERS_POOL = [
    "Marcus Aurelius", "Seneca", "Epictetus", "Friedrich Nietzsche", 
    "Arthur Schopenhauer", "Ralph Waldo Emerson", "Lao Tzu", "Sun Tzu", "Michel de Montaigne"
]

def generate_stoic_concept_deduped(raw_api_key, visual_theme, philosopher, custom_directive):
    clean_key = raw_api_key.strip().strip('"').strip("'")
    client = genai.Client(api_key=clean_key)

    used = set(db.get("used_headlines", []))
    for p in db.get("scheduled_posts", []):
        if p.get("headline"):
            used.add(p["headline"].upper())

    recent_blacklist = list(used)[-60:]
    blacklist_str = "\n".join([f"- {h}" for h in recent_blacklist]) if recent_blacklist else "None yet."

    target_philosopher = philosopher
    if philosopher in ["🎲 Random / AI Choice", "Any"]:
        last_phil = db.get("last_philosopher")
        available_phils = [p for p in PHILOSOPHERS_POOL if p != last_phil]
        target_philosopher = random.choice(available_phils)

    prompt = f"""
    You are Head Copywriter for 'Echoes of Wisdom'.
    Theme: {visual_theme}
    Featured Thinker: {target_philosopher}
    User Focus: {custom_directive or 'Synthesize an original, high-stakes tactical rule for personal sovereignty, boundary defense, or ruthless discipline.'}

    CRITICAL RULES:
    1. headline: 2 to 4 bold, commanding uppercase words (e.g. NEVER EXPLAIN SILENCE, WANT LESS TO RULE).
    2. Do NOT repeat these past headlines:
    {blacklist_str}
    3. body_text: One punchy sentence (12-16 words) framing a psychological law.
    4. caption_hook: 4 to 6 explosive words for mobile notification preview.
    5. caption_lesson: 2 crisp sentences explaining the underlying human nature dynamic.
    6. debate_question: Stark internal dilemma question.
    7. choice_1: Master Stoic reaction (3-5 words).
    8. choice_2: Impulsive human reaction (3-5 words).

    Output STRICT JSON ONLY:
    {{
      "category": "TACTICAL PILLAR (e.g. SOVEREIGNTY, BOUNDARY LAW, MENTAL FORTRESS, DETACHMENT)",
      "headline": "2-4 WORDS IN CAPS",
      "body_text": "One powerful 12-16 word sentence explaining the hook.",
      "attribution": "{target_philosopher.upper()}",
      "caption_hook": "PUNCHY SCROLL STOPPER",
      "caption_lesson": "Two sentences of high-value wisdom.",
      "debate_question": "When faced with this choice:",
      "choice_1": "Master reaction",
      "choice_2": "Impulsive reaction",
      "hashtags": "#StoicMindset #EchoesOfWisdom #Discipline #Philosophy #MarcusAurelius"
    }}
    """

    candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-flash-latest"]
    errs = []

    for mod in candidate_models:
        try:
            resp = client.models.generate_content(
                model=mod,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.85
                )
            )
            raw = resp.text.strip()
            raw = re.sub(r'^```json\s*', '', raw, flags=re.MULTILINE)
            raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)
            raw = re.sub(r'```$', '', raw, flags=re.MULTILINE)
            parsed = json.loads(raw.strip())
            
            if "headline" in parsed and "body_text" in parsed:
                if parsed["headline"].upper() not in used:
                    db["last_philosopher"] = target_philosopher
                    full_caption = format_high_conversion_caption(
                        raw_hook=parsed.get("caption_hook", parsed["headline"]),
                        lesson=parsed.get("caption_lesson", parsed["body_text"]),
                        quote=parsed["body_text"],
                        attribution=parsed["attribution"],
                        deb_q=parsed.get("debate_question", "When conflict strikes your peace:"),
                        choice1=parsed.get("choice_1", "Maintain silent composure"),
                        choice2=parsed.get("choice_2", "Defend yourself verbally"),
                        tags=parsed.get("hashtags", "#StoicMindset #EchoesOfWisdom #Discipline"),
                        brand_handle=get_persistent_handle()
                    )
                    parsed["post_caption"] = full_caption
                    return parsed, None
        except Exception as e:
            errs.append(f"{mod}: {e}")
            continue

    return None, " | ".join(errs)

# ---------------------------------------------------------
# 10. STUDIO DASHBOARD INTERFACE
# ---------------------------------------------------------
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <div style="font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: #F8FAFC;">
        ⚡ ECHOES STUDIO <span style="font-size: 13px; color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-weight: 500;">v3.3 // TACTICAL FEED SUITE</span>
    </div>
</div>
""", unsafe_allow_html=True)

default_time = db.get("default_time_ist", "17:30")
saved_last_date_str = db.get("last_scheduled_date")
saved_last_date = None
if saved_last_date_str:
    try: saved_last_date = datetime.strptime(saved_last_date_str, "%Y-%m-%d").date()
    except Exception: pass

next_target_dt = calculate_next_slot(base_date=saved_last_date, target_time_str=default_time)
formatted_time_24h = next_target_dt.strftime("%H:%M")

st.markdown(f"""
<div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px;">
    <div class="badge badge-green"><span class="dot"></span> ENGINE: FLASH ACTIVE</div>
    <div class="badge badge-blue">⚡ DUAL COMPOSITION MATRIX</div>
    <div class="badge badge-amber">📅 NEXT DROP: {next_target_dt.strftime('%a, %b %d')} @ {formatted_time_24h} IST</div>
</div>
""", unsafe_allow_html=True)

if "lock_notification" in st.session_state:
    st.markdown(f"""
    <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; border-radius: 10px; padding: 12px 16px; margin-bottom: 16px; font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #34D399;">
        {st.session_state['lock_notification']}
    </div>
    """, unsafe_allow_html=True)
    del st.session_state["lock_notification"]

with st.expander("📅 CADENCE & BRAND SETTINGS", expanded=False):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        custom_last_d = st.date_input("Last Scheduled Date", value=saved_last_date if saved_last_date else datetime.now(timezone(timedelta(hours=5, minutes=30))).date())
    with col_c2:
        custom_t = st.time_input("Daily Drop Time (IST)", value=parse_time_str(default_time))

    if st.button("💾 Save Schedule Cadence"):
        db["last_scheduled_date"] = custom_last_d.strftime("%Y-%m-%d")
        db["default_time_ist"] = custom_t.strftime("%H:%M")
        save_db(db)
        st.session_state["lock_notification"] = f"✓ Cadence updated: advancing from {db['last_scheduled_date']} @ {db['default_time_ist']} IST"
        st.rerun()

api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
elif os.getenv("GEMINI_API_KEY"):
    api_key = str(os.getenv("GEMINI_API_KEY")).strip().strip('"').strip("'")

curr_handle = get_persistent_handle()

with st.expander("🔑 API CREDENTIALS & BRAND IDENTITY", expanded=(not bool(api_key))):
    user_key = st.text_input("Gemini API Key", value=api_key, type="password", placeholder="AIzaSy...")
    if user_key:
        api_key = user_key.strip().strip('"').strip("'")

    st.divider()
    user_h = st.text_input("Official Brand Handle", value=curr_handle, placeholder="@EchoesOfWisdomOfficial")
    if user_h != curr_handle:
        save_persistent_handle(user_h)
        st.caption(f"✓ Brand handle saved as {user_h}")

with st.expander("🎛️ STUDIO CONTROLS & COMPOSITION", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        selected_theme = st.selectbox("Visual Backdrop", ["🎲 Random / AI Best Match"] + list(EXPANDED_VAULT.keys()))
        selected_layout = st.selectbox("Composition Layout", ["Classic Imperial", "Editorial Asymmetry"])
    with col2:
        selected_philosopher = st.selectbox("Philosopher", ["🎲 Random / AI Choice"] + PHILOSOPHERS_POOL)
        col_t1, col_t2 = st.columns(2)
        with col_t1: show_dilemma = st.checkbox("Dilemma Strip", value=True, help="1 vs 2 poll on image bottom")
        with col_t2: apply_grain = st.checkbox("35mm Film Grain", value=True, help="Removes digital smoothness")

    components.html("""
    <div style="font-family: 'JetBrains Mono', monospace; margin: 4px 0 10px 0;">
        <button id="micBtn" onclick="toggleSpeech()" style="background: rgba(56, 189, 248, 0.12); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.35); padding: 9px 16px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; letter-spacing: 0.05em;">
            🎙️ TAP TO DICTATE CONCEPT
        </button>
        <span id="micStatus" style="font-size: 12px; color: #64748B; margin-left: 10px;"></span>
    </div>
    <script>
        var recognition;
        function toggleSpeech() {
            var status = document.getElementById("micStatus");
            var btn = document.getElementById("micBtn");
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                status.innerText = "Dictation not supported in browser. Use keyboard mic.";
                return;
            }
            var SpeechRecognition = window.SpeechRecognition |

| window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            recognition.onstart = function() {
                btn.style.background = "rgba(239, 68, 68, 0.2)";
                btn.style.color = "#F87171";
                btn.innerText = "🛑 LISTENING...";
            };
            recognition.onresult = function(event) {
                var transcript = event.results[0][0].transcript;
                var inputs = window.parent.document.querySelectorAll('input[type="text"]');
                for (var i = 0; i < inputs.length; i++) {
                    if (inputs[i].placeholder.includes("coworker") |

| inputs[i].getAttribute("aria-label") === "Tactical Prompt / Custom Dilemma") {
                        inputs[i].value = transcript;
                        inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
            };
            recognition.onend = function() {
                btn.style.background = "rgba(56, 189, 248, 0.12)";
                btn.style.color = "#38BDF8";
                btn.innerText = "🎙️ TAP TO DICTATE CONCEPT";
            };
            recognition.start();
        }
    </script>
    """, height=48)

    custom_input = st.text_input(
        "Tactical Prompt / Custom Dilemma",
        placeholder="e.g., Never announce your exit when cutting off a fake friend"
    )

generate_btn = st.button("🚀 Render Master Social Post", type="primary")

# ---------------------------------------------------------
# 11. EXECUTION PIPELINE
# ---------------------------------------------------------
if generate_btn:
    if not api_key:
        st.error("Missing Gemini API Key. Open the 'API CREDENTIALS' accordion.")
    else:
        with st.spinner("⚡ Synthesizing tactical lesson with sub-second Gemini Flash..."):
            theme_choice = selected_theme
            if theme_choice.startswith("🎲"):
                theme_choice = random.choice(list(EXPANDED_VAULT.keys()))

            concept, err = generate_stoic_concept_deduped(api_key, theme_choice, selected_philosopher, custom_input)

            if err or not concept:
                st.error(f"Synthesis Error: {err}")
            else:
                vault_items = EXPANDED_VAULT.get(theme_choice, EXPANDED_VAULT["CLASSICAL_STATUE"])
                used_bd = set(db.get("used_backdrops", []))
                fresh_backdrops = [it for it in vault_items if it["name"] not in used_bd]

                if not fresh_backdrops:
                    db["used_backdrops"] = [b for b in db.get("used_backdrops", []) if b not in [it["name"] for it in vault_items]]
                    fresh_backdrops = vault_items

                chosen_item = random.choice(fresh_backdrops)
                bg_image = fetch_image_resilient(chosen_item["url"], vault_items)
                
                canvas_result = render_post_canvas(
                    bg_img=bg_image,
                    post_data=concept,
                    layout_mode=selected_layout,
                    show_dilemma_strip=show_dilemma,
                    enable_grain=apply_grain
                )

                st.session_state["active_post"] = {
                    "concept": concept,
                    "canvas": canvas_result,
                    "backdrop_name": chosen_item["name"],
                    "target_date": next_target_dt.strftime("%Y-%m-%d"),
                    "target_time_display": formatted_time_24h
                }

# ---------------------------------------------------------
# 12. ACTIVE ASSET TERMINAL & 1-TAP CLIPBOARD
# ---------------------------------------------------------
if "active_post" in st.session_state:
    post = st.session_state["active_post"]
    concept = post["concept"]
    canvas = post["canvas"]

    st.divider()
    st.markdown(f"""
    <div style="font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #38BDF8; font-weight: 700; margin-bottom: 8px;">
        TARGET SCHEDULE // {post['target_date']} @ {post.get('target_time_display', '17:30')} IST
    </div>
    """, unsafe_allow_html=True)

    st.image(canvas, use_container_width=True)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", quality=98)
    byte_im = buf.getvalue()
    filename = f"{post['target_date'].replace('-', '')}_{re.sub(r'[^a-zA-Z0-9]', '_', concept['headline']).lower()}.png"

    st.download_button(
        label="💾 Save Master 4:5 Image to Gallery",
        data=byte_im,
        file_name=filename,
        mime="image/png"
    )

    st.text_area("Meta / Social Caption (Pre-formatted Unicode Bold)", concept["post_caption"], height=200)

    escaped_caption = json.dumps(concept["post_caption"])
    components.html(f"""
    <div style="margin: 0; padding: 0;">
        <button id="copyBtn" onclick="copyCaption()" style="width: 100%; height: 2.85rem; background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size: 13px; cursor: pointer;">
            📋 COPY CAPTION TO CLIPBOARD
        </button>
    </div>
    <script>
        function copyCaption() {{
            var text = {escaped_caption};
            function setSuccess() {{
                var btn = document.getElementById("copyBtn");
                btn.innerText = "✓ COPIED TO CLIPBOARD!";
                btn.style.background = "#059669";
                btn.style.color = "#FFFFFF";
                setTimeout(function() {{
                    btn.innerText = "📋 COPY CAPTION TO CLIPBOARD";
                    btn.style.background = "rgba(56, 189, 248, 0.15)";
                    btn.style.color = "#38BDF8";
                }}, 2500);
            }}
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(setSuccess).catch(function() {{ fallbackCopy(text); }});
            }} else {{ fallbackCopy(text); }}
            function fallbackCopy(str) {{
                var el = document.createElement('textarea');
                el.value = str;
                document.body.appendChild(el);
                el.select();
                try {{ document.execCommand('copy'); setSuccess(); }} catch(err) {{}}
                document.body.removeChild(el);
            }}
        }}
    </script>
    """, height=50)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✅ Lock & Advance Date"):
            db["scheduled_posts"].append({
                "date": post["target_date"],
                "time": post.get("target_time_display", "17:30"),
                "headline": concept["headline"],
                "filename": filename
            })
            if concept["headline"].upper() not in db.get("used_headlines", []):
                db["used_headlines"].append(concept["headline"].upper())
            if post["backdrop_name"] not in db.get("used_backdrops", []):
                db["used_backdrops"].append(post["backdrop_name"])

            db["last_scheduled_date"] = post["target_date"]
            save_db(db)

            st.session_state["lock_notification"] = f"✓ LOCKED: '{concept['headline']}' logged for {post['target_date']} @ {post.get('target_time_display', '17:30')} IST."
            del st.session_state["active_post"]
            st.rerun()

    with col_b:
        if st.button("❌ Blacklist & Regenerate"):
            if concept["headline"].upper() not in db.get("used_headlines", []):
                db["used_headlines"].append(concept["headline"].upper())
            if post["backdrop_name"] not in db.get("used_backdrops", []):
                db["used_backdrops"].append(post["backdrop_name"])
            save_db(db)
            del st.session_state["active_post"]
            st.rerun()

    st.markdown("""
    <div style="margin-top: 12px;">
        <a href="[https://business.facebook.com/latest/composer](https://business.facebook.com/latest/composer)" target="_blank" style="text-decoration: none;">
            <button style="width: 100%; height: 3rem; background: #1877F2; color: white; border: none; border-radius: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size: 13px; cursor: pointer; box-shadow: 0 4px 15px rgba(24, 119, 242, 0.3);">
                🌐 OPEN META BUSINESS SUITE SCHEDULER
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 13. SCHEDULED QUEUE VIEWER
# ---------------------------------------------------------
if db.get("scheduled_posts"):
    with st.expander(f"📋 SCHEDULED QUEUE ({len(db['scheduled_posts'])})", expanded=False):
        for item in reversed(db["scheduled_posts"]):
            st.markdown(f"""
            <div style="background: #0A0F1D; border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; font-family: 'JetBrains Mono', monospace; font-size: 12px;">
                <div>
                    <span style="color: #38BDF8; font-weight: 700;">{item.get('date')}</span>
                    <span style="color: #64748B;"> @ </span>
                    <span style="color: #FBBF24;">{item.get('time', '17:30')} IST</span>
                    <div style="color: #F8FAFC; font-weight: 600; margin-top: 2px;">{item.get('headline')}</div>
                </div>
                <div style="color: #34D399; font-weight: 700; font-size: 11px;">● SCHEDULED</div>
            </div>
            """, unsafe_allow_html=True)
