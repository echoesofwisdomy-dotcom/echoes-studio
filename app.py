import os
import io
import json
import re
import random
from datetime import datetime, timedelta, timezone, time
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. PAGE SETUP & OBSIDIAN TECH UI (NO CUTOFF / HIGH CONTRAST)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Echoes Studio // Terminal",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

    /* Transparent header to prevent top clipping */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 2.5rem !important;
    }

    /* Global Dark Canvas */
    .stApp {
        background-color: #080B11 !important;
        background-image: radial-gradient(circle at 50% -20%, #151e33 0%, #080B11 75%) !important;
        font-family: 'Space Grotesk', -apple-system, sans-serif !important;
        color: #E2E8F0 !important;
    }
    
    .block-container {
        padding-top: 4.2rem !important;
        padding-bottom: 3rem !important;
        max-width: 680px !important;
    }

    /* Expander / Accordion Fixes (Eliminates White Backgrounds) */
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
        letter-spacing: 0.05em !important;
        padding: 12px 16px !important;
        border-bottom: 1px solid rgba(56, 189, 248, 0.15) !important;
    }

    div[data-testid="stExpander"] summary:hover {
        color: #7DD3FC !important;
    }

    /* High-Contrast Input Labels */
    label[data-testid="stWidgetLabel"] p, .stTextInput label p, .stSelectbox label p, .stDateInput label p, .stTimeInput label p {
        color: #94A3B8 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
    }

    /* Dropdown Menus & Inputs */
    div[data-baseweb="select"] > div {
        background-color: #0A0F1D !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 8px !important;
        color: #F8FAFC !important;
    }

    div[data-baseweb="select"] span {
        color: #F8FAFC !important;
    }

    .stTextInput>div>div>input, .stTextArea textarea {
        background-color: #0A0F1D !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 8px !important;
        color: #F8FAFC !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 14px !important;
    }

    /* Primary Action Buttons */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 50%, #075985 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(56, 189, 248, 0.4) !important;
        border-radius: 10px !important;
        height: 3.4rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        box-shadow: 0 0 25px rgba(2, 132, 199, 0.35) !important;
        transition: all 0.2s ease !important;
    }

    .stDownloadButton>button {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        color: white !important;
        border: 1px solid rgba(52, 211, 153, 0.4) !important;
        border-radius: 10px !important;
        height: 3.2rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        box-shadow: 0 0 20px rgba(5, 150, 105, 0.3) !important;
    }

    /* Telemetry Pill Badges */
    .telemetry-bar {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 16px;
    }
    .badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 6px;
        letter-spacing: 0.05em;
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
# 2. PERSISTENCE CONFIG & CADENCE MEMORY
# ---------------------------------------------------------
DATA_DIR = os.path.join(os.getcwd(), "data")
FONTS_DIR = os.path.join(os.getcwd(), "fonts")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "studio_db.json")

def load_db():
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "scheduled_posts": [],
        "blacklisted_headlines": [],
        "blacklisted_backdrops": [],
        "last_scheduled_date": None,
        "default_time_ist": "17:30"
    }

def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

db = load_db()

# ---------------------------------------------------------
# 3. HIGH-SPEED CACHED FONT FOUNDRY
# ---------------------------------------------------------
@st.cache_resource(show_spinner=False)
def ensure_fonts_cached():
    sources = {
        "Cinzel_Bold": "https://fonts.gstatic.com/s/cinzel/v23/8vIQ776mE3tYOmt9_ZUC.ttf",
        "Cinzel_Reg": "https://fonts.gstatic.com/s/cinzel/v23/8vIQ776mE3tYOmt9_ZQ.ttf",
        "Cormorant_Italic": "https://fonts.gstatic.com/s/cormorantgaramond/v19/co3bmX5slCNuHLi8bLeY9MK7whWMhyjYpHtK.ttf"
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    for name, url in sources.items():
        path = os.path.join(FONTS_DIR, f"{name}.ttf")
        if not os.path.exists(path) or os.path.getsize(path) < 10000:
            try:
                res = requests.get(url, headers=headers, timeout=6)
                if res.status_code == 200 and len(res.content) > 10000:
                    with open(path, "wb") as f:
                        f.write(res.content)
            except Exception:
                pass
    return True

ensure_fonts_cached()

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
# 4. CURATED 50 HIGH-ENGAGEMENT VISUAL VAULT
# ---------------------------------------------------------
EXPANDED_VAULT = {
    "CLASSICAL_STATUE": [
        {"name": "Classical Roman Marble Bust in Shadow", "url": "https://images.unsplash.com/photo-1580136579312-94651dfd596d?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Chiaroscuro Hellenistic Bronze Philosopher", "url": "https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Weathered Greek Marble Profile", "url": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Roman Travertine Carved Relief", "url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Winged Victory of Samothrace Drapery", "url": "https://images.unsplash.com/photo-1561214115-f2f134cc4912?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "FINE_ART_PAINTING": [
        {"name": "Epic Classical Battle Chiaroscuro", "url": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Renaissance Council in Deep Candlelight", "url": "https://images.unsplash.com/photo-1582561424760-0321d75e81fa?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Atmospheric Classical Harbor Twilight", "url": "https://images.unsplash.com/photo-1577083552431-6e5fd01aa342?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Ancient Roman Forum Oil Panorama", "url": "https://images.unsplash.com/photo-1578321272176-b7bbc0679853?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "SEA_AND_CLIFFS": [
        {"name": "Rugged Sea Cliffs Against Storm Surge", "url": "https://images.unsplash.com/photo-1505118380757-91f5f5632de0?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Dark Volcanic Coast & Breaking Ocean Swell", "url": "https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Sheer Atlantic Ocean Cliff Edge", "url": "https://images.unsplash.com/photo-1476673160081-cf065607f449?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "CITADEL_AND_ARCHES": [
        {"name": "Roman Colosseum Arches at Twilight", "url": "https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Ancient Classical Stone Portico", "url": "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Sunken Roman Temple Columns", "url": "https://images.unsplash.com/photo-1529154036614-a60975f5c760?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "ALPINE_AND_SUMMITS": [
        {"name": "Alpine Summit Above Clouds", "url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Granite Mountain Ridge at Sunset", "url": "https://images.unsplash.com/photo-1486870591958-9b9d0d1dda99?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "MODERN_WORKSPACE": [
        {"name": "Quiet Architect Workspace with Clean Lines", "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Minimalist Slate & Timber Study", "url": "https://images.unsplash.com/photo-1507842229451-7f01be7fe7ab?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Modern High-Rise Skyline at Dawn", "url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ]
}

# ---------------------------------------------------------
# 5. DYNAMIC CADENCE & MEMORY ENGINE
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
            if now_ist.time() < sched_t:
                next_d = now_ist.date()
            else:
                next_d = now_ist.date() + timedelta(days=1)
                
    return datetime.combine(next_d, sched_t)

# ---------------------------------------------------------
# 6. FAIL-SAFE GRAPHICS COMPOSITOR
# ---------------------------------------------------------
def wrap_text(draw, text, font, max_width):
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            continue
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
    }
    candidates = [chosen_url]
    if backup_vault_items:
        candidates.extend([it["url"] for it in backup_vault_items if it.get("url") != chosen_url])
        
    for target in candidates[:3]:
        try:
            res = requests.get(target, headers=headers, timeout=6)
            if res.status_code == 200 and len(res.content) > 5000:
                raw = Image.open(io.BytesIO(res.content))
                return raw.resize((1080, 1350), Image.Resampling.LANCZOS)
        except Exception:
            continue
            
    base = Image.new("RGB", (1080, 1350), (12, 16, 24))
    draw = ImageDraw.Draw(base)
    for y in range(1350):
        ratio = y / 1350.0
        r = int(10 + 16 * (1.0 - abs(ratio - 0.5) * 2))
        g = int(14 + 20 * (1.0 - abs(ratio - 0.5) * 2))
        b = int(24 + 32 * (1.0 - abs(ratio - 0.5) * 2))
        draw.line([(0, y), (1080, y)], fill=(r, g, b))
    return base

def stamp_brand(canvas):
    logo_file = None
    for name in ["logo.png", "logo.jpg", "logo.jpeg"]:
        if os.path.exists(name):
            logo_file = name
            break

    if logo_file:
        try:
            raw_logo = Image.open(logo_file).convert("RGBA")
            lw_orig, lh_orig = raw_logo.size
            min_dim = min(lw_orig, lh_orig)
            
            left = (lw_orig - min_dim) // 2
            top = (lh_orig - min_dim) // 2
            raw_logo = raw_logo.crop((left, top, left + min_dim, top + min_dim))
            
            scale = 4
            big_size = (min_dim * scale, min_dim * scale)
            big_mask = Image.new("L", big_size, 0)
            d_mask = ImageDraw.Draw(big_mask)
            d_mask.ellipse([0, 0, big_size[0] - 1, big_size[1] - 1], fill=255)
            circle_mask = big_mask.resize((min_dim, min_dim), Image.Resampling.LANCZOS)
            raw_logo.putalpha(circle_mask)
            
            target_size = 120
            raw_logo.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
            final_w, final_h = raw_logo.size
            pos_x = (1080 - final_w) // 2
            pos_y = 110
            
            shadow = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0))
            shadow.paste(
                (0, 0, 0, 235), 
                (pos_x + 2, pos_y + 4), 
                mask=raw_logo.split()[3].filter(ImageFilter.GaussianBlur(6))
            )
            canvas.alpha_composite(shadow)
            canvas.alpha_composite(raw_logo, (pos_x, pos_y))
            return
        except Exception:
            pass

    draw = ImageDraw.Draw(canvas)
    crest_f = get_font("Cinzel_Bold", 20)
    crest_t = "E C H O E S   O F   W I S D O M"
    cw = draw.textlength(crest_t, font=crest_f)
    draw.text(((1080 - cw) // 2, 130), crest_t, font=crest_f, fill=(218, 175, 55, 230))
    draw.line([(1080 // 2 - 40, 165), (1080 // 2 + 40, 165)], fill=(218, 175, 55, 180), width=1)

def render_post_canvas(bg_img, post_data):
    w, h = 1080, 1350
    canvas = bg_img.convert("RGBA")
    
    scrim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(scrim)
    for y in range(h):
        dist = abs(y - h * 0.52) / (h * 0.52)
        alpha = int(45 + 115 * (1.0 - dist ** 1.8))
        s_draw.line([(0, y), (w, y)], fill=(6, 8, 12, min(190, max(25, alpha))))
    canvas = Image.alpha_composite(canvas, scrim)
    
    stamp_brand(canvas)
    draw = ImageDraw.Draw(canvas)
    
    # 1. Category with Drawn Vector Wings
    cat_f = get_font("Cinzel_Bold", 26)
    clean_cat = post_data['category'].strip().upper()
    cw = draw.textlength(clean_cat, font=cat_f)
    cx = (w - cw) // 2
    cy = 270
    draw.text((cx + 1, cy + 1), clean_cat, font=cat_f, fill=(0, 0, 0, 220))
    draw.text((cx, cy), clean_cat, font=cat_f, fill=(218, 175, 55, 255))
    
    wing_w, gap, line_y = 40, 16, cy + 14
    draw.line([(cx - gap - wing_w, line_y), (cx - gap, line_y)], fill=(218, 175, 55, 210), width=2)
    draw.line([(cx + cw + gap, line_y), (cx + cw + gap + wing_w, line_y)], fill=(218, 175, 55, 210), width=2)
    
    # 2. Headline with Dual Shadows
    hl_f = get_font("Cinzel_Bold", 88)
    hl_lines = wrap_text(draw, post_data['headline'].upper(), hl_f, 860)
    line_h = int(88 * 1.28)
    total_hl_h = len(hl_lines) * line_h
    start_y = 440 if len(hl_lines) == 2 else 480
    
    for i, line in enumerate(hl_lines):
        lw = draw.textlength(line, font=hl_f)
        lx = (w - lw) // 2
        ly = start_y + i * line_h
        for ox, oy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 6)]:
            draw.text((lx + ox, ly + oy), line, font=hl_f, fill=(0, 0, 0, 180))
        draw.text((lx + 2, ly + 4), line, font=hl_f, fill=(0, 0, 0, 240))
        draw.text((lx, ly), line, font=hl_f, fill=(255, 253, 242, 255))
        
    # 3. Central Divider
    div_y = start_y + total_hl_h + 35
    draw.line([(w // 2 - 80, div_y), (w // 2 + 80, div_y)], fill=(218, 175, 55, 210), width=2)
    
    # 4. Body Quote
    body_f = get_font("Cormorant_Italic", 42)
    body_lines = wrap_text(draw, f'"{post_data["body_text"].strip()}"', body_f, 840)
    by = div_y + 40
    for bl in body_lines:
        bw = draw.textlength(bl, font=body_f)
        bx = (w - bw) // 2
        for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2), (0, 3)]:
            draw.text((bx + ox, by + oy), bl, font=body_f, fill=(0, 0, 0, 230))
        draw.text((bx, by), bl, font=body_f, fill=(240, 244, 250, 255))
        by += int(42 * 1.36)
        
    # 5. Philosopher Attribution with Vector Wings
    att_f = get_font("Cinzel_Bold", 24)
    clean_att = post_data['attribution'].strip().upper()
    aw = draw.textlength(clean_att, font=att_f)
    ax, ay = (w - aw) // 2, by + 25
    draw.text((ax + 1, ay + 1), clean_att, font=att_f, fill=(0, 0, 0, 220))
    draw.text((ax, ay), clean_att, font=att_f, fill=(218, 175, 55, 255))
    
    att_line_y = ay + 12
    draw.line([(ax - gap - wing_w, att_line_y), (ax - gap, att_line_y)], fill=(218, 175, 55, 210), width=2)
    draw.line([(ax + aw + gap, att_line_y), (ax + aw + gap + wing_w, att_line_y)], fill=(218, 175, 55, 210), width=2)
    
    return canvas.convert("RGB")

# ---------------------------------------------------------
# 7. HIGH-SPEED AI SYNTHESIS PIPELINE
# ---------------------------------------------------------
PHILOSOPHERS_POOL = [
    "Marcus Aurelius", "Seneca", "Epictetus", "Friedrich Nietzsche", 
    "Arthur Schopenhauer", "Ralph Waldo Emerson", "Lao Tzu", "Sun Tzu", "Michel de Montaigne"
]

def generate_stoic_concept_fast(raw_api_key, visual_theme, philosopher, custom_directive):
    clean_key = raw_api_key.strip().strip('"').strip("'")
    client = genai.Client(api_key=clean_key)
    blacklist = db.get("blacklisted_headlines", [])
    blacklist_str = "\n".join([f"- {h}" for h in blacklist[-40:]]) if blacklist else "None."
    
    target_philosopher = philosopher
    if philosopher in ["🎲 Random / AI Choice", "Any"]:
        target_philosopher = random.choice(PHILOSOPHERS_POOL)

    prompt = f"""
    Role: Creative Director for 'Echoes of Wisdom'.
    Theme: {visual_theme}
    Preferred Philosopher: {target_philosopher}
    User Direction/Voice Input: {custom_directive or 'Synthesize an authoritative, timeless lesson of resilience and inner strength.'}
    
    STRICT BLACKLIST (DO NOT USE OR REPHRASE):
    {blacklist_str}
    
    Output JSON ONLY:
    {{
      "category": "CONCISE PILLAR (e.g. EMOTIONAL MASTERY, FORTITUDE, INNER CITADEL, DEEP FOCUS)",
      "headline": "BOLD 2-4 WORD HOOK",
      "body_text": "One powerful 12-18 word sentence explaining the hook.",
      "attribution": "{target_philosopher.upper()}",
      "post_caption": "Full Facebook/Instagram caption with hook, lesson, binary debate CTA (1️⃣/2️⃣), handles, and hashtags."
    }}
    """

    for target_model in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            resp = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            parsed = json.loads(resp.text)
            if "headline" in parsed and "body_text" in parsed:
                return parsed, None
        except Exception:
            continue

    return {
        "category": "INNER CITADEL",
        "headline": "STAND UNMOVED",
        "body_text": "External turbulence has no power over the mind that chooses stillness above reaction.",
        "attribution": "MARCUS AURELIUS",
        "post_caption": "🏛️ MASTER YOUR RESPONSE.\n\nWhen external disrespect strikes:\n1️⃣ Guard your peace in absolute silence\n2️⃣ Allow the noise into your day\n\nDrop 1 or 2 below. 👇\n\n#Stoicism #MarcusAurelius #Wisdom"
    }, None

# ---------------------------------------------------------
# 8. OBSIDIAN DASHBOARD UI
# ---------------------------------------------------------
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <div style="font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: #F8FAFC;">
        ⚡ ECHOES STUDIO <span style="font-size: 13px; color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-weight: 500;">v2.7 // CADENCE</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Cadence Memory Initialization
default_time = db.get("default_time_ist", "17:30")
saved_last_date_str = db.get("last_scheduled_date")
saved_last_date = None
if saved_last_date_str:
    try:
        saved_last_date = datetime.strptime(saved_last_date_str, "%Y-%m-%d").date()
    except Exception:
        pass

next_target_dt = calculate_next_slot(base_date=saved_last_date, target_time_str=default_time)

# Telemetry Status Bar
st.markdown(f"""
<div class="telemetry-bar">
    <div class="badge badge-green"><span class="dot"></span> ENGINE: READY</div>
    <div class="badge badge-blue">⚡ GEMINI 2.5 FLASH</div>
    <div class="badge badge-amber">📅 NEXT DROP: {next_target_dt.strftime('%a, %b %d')} @ {next_target_dt.strftime('%I:%M %p')} IST</div>
</div>
""", unsafe_allow_html=True)

# Cadence & Schedule Manager Accordion
with st.expander("📅 PUBLISHING CADENCE & TIME MANAGER", expanded=False):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        custom_last_d = st.date_input(
            "Last Scheduled Date",
            value=saved_last_date if saved_last_date else datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
        )
    with col_c2:
        parsed_t = parse_time_str(default_time)
        custom_t = st.time_input("Daily Drop Time (IST)", value=parsed_t)

    if st.button("💾 Save Schedule Cadence Preference"):
        db["last_scheduled_date"] = custom_last_d.strftime("%Y-%m-%d")
        db["default_time_ist"] = custom_t.strftime("%H:%M")
        save_db(db)
        st.success("Cadence settings updated and locked!")
        st.rerun()

# API Secret Check
api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
elif os.getenv("GEMINI_API_KEY"):
    api_key = str(os.getenv("GEMINI_API_KEY")).strip().strip('"').strip("'")

if not api_key:
    with st.expander("🔑 AUTHENTICATION REQUIRED", expanded=True):
        api_key = st.text_input("Enter Gemini API Key", type="password", placeholder="AIzaSy...")

# Studio HUD Controls
with st.expander("🎛️ STUDIO CONTROLS & DIRECTIVES", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        backdrop_options = [
            "🎲 Random / AI Best Match",
            "CLASSICAL_STATUE",
            "FINE_ART_PAINTING",
            "SEA_AND_CLIFFS",
            "CITADEL_AND_ARCHES",
            "ALPINE_AND_SUMMITS",
            "MODERN_WORKSPACE"
        ]
        selected_theme = st.selectbox("Visual Backdrop", backdrop_options)
        
    with col2:
        philosopher_options = [
            "🎲 Random / AI Choice",
            "Marcus Aurelius",
            "Seneca",
            "Epictetus",
            "Friedrich Nietzsche",
            "Arthur Schopenhauer",
            "Ralph Waldo Emerson",
            "Lao Tzu",
            "Sun Tzu",
            "Michel de Montaigne"
        ]
        selected_philosopher = st.selectbox("Philosopher", philosopher_options)

    # Voice Dictation Card
    components.html("""
    <div style="font-family: 'JetBrains Mono', monospace; margin: 4px 0 10px 0;">
        <button id="micBtn" onclick="toggleSpeech()" style="background: rgba(56, 189, 248, 0.12); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.35); padding: 9px 16px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; letter-spacing: 0.05em; transition: all 0.2s;">
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
                status.innerText = "Dictation not supported in browser. Use mobile keyboard mic.";
                return;
            }
            var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onstart = function() {
                btn.style.background = "rgba(239, 68, 68, 0.2)";
                btn.style.color = "#F87171";
                btn.style.borderColor = "#EF4444";
                btn.innerText = "🛑 LISTENING...";
                status.innerText = "Speak now...";
            };
            recognition.onresult = function(event) {
                var transcript = event.results[0][0].transcript;
                status.innerText = "Captured: " + transcript;
                var inputs = window.parent.document.querySelectorAll('input[type="text"]');
                for (var i = 0; i < inputs.length; i++) {
                    if (inputs[i].placeholder.includes("coworker") || inputs[i].getAttribute("aria-label") === "Concept Directive / Custom Topic") {
                        inputs[i].value = transcript;
                        inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
            };
            recognition.onend = function() {
                btn.style.background = "rgba(56, 189, 248, 0.12)";
                btn.style.color = "#38BDF8";
                btn.style.borderColor = "rgba(56, 189, 248, 0.35)";
                btn.innerText = "🎙️ TAP TO DICTATE CONCEPT";
            };
            recognition.start();
        }
    </script>
    """, height=48)

    custom_input = st.text_input(
        "Concept Directive / Custom Topic",
        placeholder="e.g., Not letting coworker criticism break my stillness"
    )

generate_btn = st.button("🚀 Render Master Social Post", type="primary")

# ---------------------------------------------------------
# 9. EXECUTION PIPELINE
# ---------------------------------------------------------
if generate_btn:
    if not api_key:
        st.error("Missing Gemini API Key.")
    else:
        with st.spinner("⚡ Synthesizing concept & rendering 4K canvas..."):
            theme_choice = selected_theme
            if theme_choice.startswith("🎲"):
                theme_choice = random.choice(list(EXPANDED_VAULT.keys()))
                
            concept, _ = generate_stoic_concept_fast(api_key, theme_choice, selected_philosopher, custom_input)
            
            vault_items = EXPANDED_VAULT.get(theme_choice, EXPANDED_VAULT["CLASSICAL_STATUE"])
            b_list = db.get("blacklisted_backdrops", [])
            available = [it for it in vault_items if it["name"] not in b_list]
            if not available:
                available = vault_items
            chosen_item = random.choice(available)
            
            bg_image = fetch_image_resilient(chosen_item["url"], available)
            canvas_result = render_post_canvas(bg_image, concept)
            
            st.session_state["active_post"] = {
                "concept": concept,
                "canvas": canvas_result,
                "backdrop_name": chosen_item["name"],
                "target_date": next_target_dt.strftime("%Y-%m-%d"),
                "target_time_display": next_target_dt.strftime("%I:%M %p")
            }

# ---------------------------------------------------------
# 10. ACTIVE ASSET TERMINAL & 1-TAP CLIPBOARD COPY
# ---------------------------------------------------------
if "active_post" in st.session_state:
    post = st.session_state["active_post"]
    concept = post["concept"]
    canvas = post["canvas"]
    
    st.divider()
    st.markdown(f"""
    <div style="font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #38BDF8; font-weight: 700; margin-bottom: 8px;">
        TARGET SCHEDULE // {post['target_date']} @ {post.get('target_time_display', '05:30 PM')} IST
    </div>
    """, unsafe_allow_html=True)
    
    st.image(canvas, use_container_width=True)
    
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", quality=98)
    byte_im = buf.getvalue()
    filename = f"{post['target_date'].replace('-', '')}_{re.sub(r'[^a-zA-Z0-9]', '_', concept['headline']).lower()}.png"
    
    st.download_button(
        label="💾 Save Master Image to Phone Gallery",
        data=byte_im,
        file_name=filename,
        mime="image/png"
    )
    
    st.text_area("Caption (Ready for Meta Business Suite)", concept["post_caption"], height=160)
    
    # 1-Tap Clipboard Copy Component
    escaped_caption = json.dumps(concept["post_caption"])
    components.html(f"""
    <div style="font-family: 'JetBrains Mono', monospace; margin: 4px 0 10px 0;">
        <button id="copyBtn" onclick="copyCaption()" style="width: 100%; height: 2.8rem; background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; letter-spacing: 0.04em; transition: all 0.2s;">
            📋 COPY CAPTION TO CLIPBOARD
        </button>
        <div id="copyToast" style="display: none; text-align: center; color: #34D399; font-size: 12px; margin-top: 6px; font-weight: bold;">
            ✓ CAPTION COPIED TO CLIPBOARD
        </div>
    </div>
    <script>
        function copyCaption() {{
            var text = {escaped_caption};
            navigator.clipboard.writeText(text).then(function() {{
                var btn = document.getElementById("copyBtn");
                var toast = document.getElementById("copyToast");
                btn.style.background = "rgba(16, 185, 129, 0.2)";
                btn.style.color = "#34D399";
                btn.style.borderColor = "#10B981";
                toast.style.display = "block";
                setTimeout(function() {{
                    btn.style.background = "rgba(56, 189, 248, 0.15)";
                    btn.style.color = "#38BDF8";
                    btn.style.borderColor = "rgba(56, 189, 248, 0.4)";
                    toast.style.display = "none";
                }}, 2500);
            }});
        }}
    </script>
    """, height=65)
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✅ Lock & Advance Date"):
            db["scheduled_posts"].append({
                "date": post["target_date"],
                "headline": concept["headline"],
                "filename": filename
            })
            db["last_scheduled_date"] = post["target_date"]
            save_db(db)
            st.success(f"Scheduled for {post['target_date']}! Next date queued.")
            st.rerun()
            
    with col_b:
        if st.button("❌ Blacklist & Regenerate"):
            db["blacklisted_headlines"].append(concept["headline"])
            db["blacklisted_backdrops"].append(post["backdrop_name"])
            save_db(db)
            del st.session_state["active_post"]
            st.warning("Concept blacklisted. Ready for re-roll.")
            st.rerun()

    st.markdown("""
    <div style="margin-top: 12px;">
        <a href="https://business.facebook.com/latest/composer" target="_blank" style="text-decoration: none;">
            <button style="width: 100%; height: 3rem; background: #1877F2; color: white; border: none; border-radius: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size: 13px; cursor: pointer; box-shadow: 0 4px 15px rgba(24, 119, 242, 0.3);">
                🌐 OPEN META BUSINESS SUITE SCHEDULER
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)
