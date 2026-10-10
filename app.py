import os
import io
import json
import re
import random
from datetime import datetime, timedelta, timezone
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. PAGE SETUP (MOBILE VIEWPORT)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Echoes Studio Mobile",
    page_icon="🏛️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: 700; height: 3rem; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; font-weight: 700; height: 3rem; background-color: #10b981; color: white; }
    div[data-testid="stExpander"] { border-radius: 8px; border: 1px solid #334155; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. PERSISTENCE CONFIG
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
        "last_scheduled_date": None
    }

def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

db = load_db()

# ---------------------------------------------------------
# 3. HIGH-RELIABILITY FONT ENGINE
# ---------------------------------------------------------
FONT_SOURCES = {
    "Cinzel_Bold": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/cinzel/static/Cinzel-Bold.ttf",
        "https://fonts.gstatic.com/s/cinzel/v23/8vIQ776mE3tYOmt9_ZUC.ttf"
    ],
    "Cinzel_Reg": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/cinzel/static/Cinzel-Regular.ttf",
        "https://fonts.gstatic.com/s/cinzel/v23/8vIQ776mE3tYOmt9_ZQ.ttf"
    ],
    "Cormorant_Italic": [
        "https://raw.githubusercontent.com/google/fonts/main/ofl/cormorantgaramond/static/CormorantGaramond-Italic.ttf",
        "https://fonts.gstatic.com/s/cormorantgaramond/v19/co3bmX5slCNuHLi8bLeY9MK7whWMhyjYpHtK.ttf"
    ]
}

def ensure_fonts():
    headers = {"User-Agent": "Mozilla/5.0"}
    for name, urls in FONT_SOURCES.items():
        path = os.path.join(FONTS_DIR, f"{name}.ttf")
        if not os.path.exists(path) or os.path.getsize(path) < 10000:
            for u in urls:
                try:
                    res = requests.get(u, headers=headers, timeout=12)
                    if res.status_code == 200 and len(res.content) > 10000:
                        with open(path, "wb") as f:
                            f.write(res.content)
                        break
                except Exception:
                    continue

ensure_fonts()

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
# 4. 50 CURATED HIGH-ENGAGEMENT VISUAL VAULT
# ---------------------------------------------------------
EXPANDED_VAULT = {
    "CLASSICAL_STATUE": [
        {"name": "Classical Roman Marble Bust in Shadow", "url": "https://images.unsplash.com/photo-1580136579312-94651dfd596d?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Chiaroscuro Hellenistic Bronze Philosopher", "url": "https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Weathered Greek Marble Profile", "url": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Roman Travertine Carved Relief", "url": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Winged Victory of Samothrace Drapery", "url": "https://images.unsplash.com/photo-1561214115-f2f134cc4912?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Pensive Stoic Thinker in Museum Hall", "url": "https://images.unsplash.com/photo-1554907984-15263bfd63bd?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Marble Column Capital Detail", "url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "FINE_ART_PAINTING": [
        {"name": "Epic Classical Battle Chiaroscuro", "url": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Renaissance Council in Deep Candlelight", "url": "https://images.unsplash.com/photo-1582561424760-0321d75e81fa?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Dramatic Historic Colonnade Oil Painting", "url": "https://images.unsplash.com/photo-1544717302-de2939b7ef71?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Atmospheric Classical Harbor Twilight", "url": "https://images.unsplash.com/photo-1577083552431-6e5fd01aa342?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Baroque Chiaroscuro Figure Study", "url": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Ancient Roman Forum Oil Panorama", "url": "https://images.unsplash.com/photo-1578321272176-b7bbc0679853?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Mythological Solitude Canvas", "url": "https://images.unsplash.com/photo-1579783901586-78822e0ac93f?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "SEA_AND_CLIFFS": [
        {"name": "Rugged Sea Cliffs Against Storm Surge", "url": "https://images.unsplash.com/photo-1505118380757-91f5f5632de0?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Dark Volcanic Coast & Breaking Ocean Swell", "url": "https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Sheer Atlantic Ocean Cliff Edge", "url": "https://images.unsplash.com/photo-1476673160081-cf065607f449?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Towering Sea Stacks in Heavy Surf", "url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Nordic Basalt Waves at Dusk", "url": "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Deep Oceanic Midnight Surge", "url": "https://images.unsplash.com/photo-1439405326854-014607f694d7?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Unbroken Stone Reef Facing Storm", "url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "CITADEL_AND_ARCHES": [
        {"name": "Roman Colosseum Arches at Twilight", "url": "https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Ancient Classical Stone Portico", "url": "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Atmospheric Stone Fortress Ruins", "url": "https://images.unsplash.com/photo-1564507592333-c60657eea523?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Sunken Roman Temple Columns", "url": "https://images.unsplash.com/photo-1529154036614-a60975f5c760?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Monolithic Vaulted Stone Corridor", "url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Antique Iron Gate to Classical Sanctuary", "url": "https://images.unsplash.com/photo-1533158307587-828f0a76ef46?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Pantheon Ceiling Oculus Rays", "url": "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "ALPINE_AND_SUMMITS": [
        {"name": "Alpine Summit Above Clouds", "url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Granite Mountain Ridge at Sunset", "url": "https://images.unsplash.com/photo-1486870591958-9b9d0d1dda99?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Solitary Peak in Morning Alpenglow", "url": "https://images.unsplash.com/photo-1454496522488-7a8e488e8606?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Glacial Mountain Lake Reflection", "url": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Jagged Dolomite Ridge Above Fog", "url": "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Towering Snow Summit in Solitude", "url": "https://images.unsplash.com/photo-1483728642387-6c3bdd6c93e5?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "High Altitude Glacier Plateau", "url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "MISTY_FOREST": [
        {"name": "Misty Redwood Sunbeams in Silence", "url": "https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Dark Pine Forest in Heavy Fog", "url": "https://images.unsplash.com/photo-1511497584788-87676104235f?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Solitary Ancient Oak in Morning Mist", "url": "https://images.unsplash.com/photo-1473448912268-2022ce9509d8?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Evergreen Ridge Under Cloud Cover", "url": "https://images.unsplash.com/photo-1502082553048-f009c37129b9?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Ancient Birch Forest Pathway", "url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Sunbeams Breaking Through Deep Canopy", "url": "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Still Lake Surrounded by Foggy Pines", "url": "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "MODERN_WORKSPACE": [
        {"name": "Quiet Architect Workspace with Clean Lines", "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Minimalist Slate & Timber Study", "url": "https://images.unsplash.com/photo-1507842229451-7f01be7fe7ab?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Morning Espresso & Leather Journal Focus", "url": "https://images.unsplash.com/photo-1499750310107-5fef28a66643?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Solitary Reader in Neoclassical Library", "url": "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Modern High-Rise Skyline at Dawn", "url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Curated Minimal Desk & Ceramic Lamp", "url": "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Evening City Skyline from Quiet Study", "url": "https://images.unsplash.com/photo-1506157786151-b8491531f063?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Architectural Spiral Concrete Stairs", "url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ]
}

# ---------------------------------------------------------
# 5. SMART NEXT-SLOT CALCULATOR
# ---------------------------------------------------------
def get_next_recommended_slot():
    now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    last_date_str = db.get("last_scheduled_date")
    if last_date_str:
        try:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
            candidate = max(last_date + timedelta(days=1), now_ist.date())
        except ValueError:
            candidate = now_ist.date() + timedelta(days=1)
    else:
        candidate = now_ist.date() if now_ist.hour < 16 else (now_ist.date() + timedelta(days=1))
    return candidate

# ---------------------------------------------------------
# 6. GRAPHICS COMPOSITOR (LOGO STAMP + CLEAN TYPOGRAPHY)
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

def fetch_image(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    raw = Image.open(io.BytesIO(res.content))
    return raw.resize((1080, 1350), Image.Resampling.LANCZOS)

def stamp_brand(canvas):
    logo_file = "logo.png"
    if os.path.exists(logo_file):
        try:
            l_img = Image.open(logo_file).convert("RGBA")
            l_img.thumbnail((120, 120), Image.Resampling.LANCZOS)
            lw, lh = l_img.size
            lx = (1080 - lw) // 2
            ly = 110
            # Soft protective glow shadow
            shadow = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0))
            shadow.paste((0, 0, 0, 230), (lx + 2, ly + 4), mask=l_img.split()[3].filter(ImageFilter.GaussianBlur(6)))
            canvas.alpha_composite(shadow)
            canvas.paste(l_img, (lx, ly), l_img)
            return
        except Exception:
            pass
    
    # Elegant fallback emblem if logo.png is not yet present
    draw = ImageDraw.Draw(canvas)
    crest_f = get_font("Cinzel_Bold", 20)
    crest_t = "E C H O E S   O F   W I S D O M"
    cw = draw.textlength(crest_t, font=crest_f)
    draw.text(((1080 - cw) // 2 + 1, 131), crest_t, font=crest_f, fill=(0, 0, 0, 220))
    draw.text(((1080 - cw) // 2, 130), crest_t, font=crest_f, fill=(218, 175, 55, 230))
    draw.line([(1080 // 2 - 40, 165), (1080 // 2 + 40, 165)], fill=(218, 175, 55, 180), width=1)

def render_post_canvas(bg_img, post_data):
    w, h = 1080, 1350
    canvas = bg_img.convert("RGBA")
    
    # Seamless Vignette
    scrim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(scrim)
    for y in range(h):
        dist = abs(y - h * 0.52) / (h * 0.52)
        alpha = int(45 + 115 * (1.0 - dist ** 1.8))
        s_draw.line([(0, y), (w, y)], fill=(6, 8, 12, min(190, max(25, alpha))))
    canvas = Image.alpha_composite(canvas, scrim)
    
    # Stamp brand header
    stamp_brand(canvas)
    
    draw = ImageDraw.Draw(canvas)
    
    # Category Pill using ASCII bullets (Zero missing-character boxes)
    cat_f = get_font("Cinzel_Bold", 26)
    clean_cat = post_data['category'].strip().upper()
    cat_t = f"•   {clean_cat}   •"
    cw = draw.textlength(cat_t, font=cat_f)
    draw.text(((w - cw) // 2 + 1, 271), cat_t, font=cat_f, fill=(0, 0, 0, 220))
    draw.text(((w - cw) // 2, 270), cat_t, font=cat_f, fill=(218, 175, 55, 255))
    
    # Headline in Cinzel Bold
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
        
    # Champagne Divider
    div_y = start_y + total_hl_h + 35
    draw.line([(w // 2 - 80, div_y), (w // 2 + 80, div_y)], fill=(218, 175, 55, 210), width=2)
    
    # Body Quote in Cormorant Garamond Italic
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
        
    # Attribution using ASCII bullets
    att_f = get_font("Cinzel_Bold", 24)
    clean_att = post_data['attribution'].strip().upper()
    att_t = f"•   {clean_att}   •"
    aw = draw.textlength(att_t, font=att_f)
    draw.text(((w - aw) // 2 + 1, by + 26), att_t, font=att_f, fill=(0, 0, 0, 220))
    draw.text(((w - aw) // 2, by + 25), att_t, font=att_f, fill=(218, 175, 55, 255))
    
    return canvas.convert("RGB")

# ---------------------------------------------------------
# 7. AI SYNTHESIS PIPELINE
# ---------------------------------------------------------
PHILOSOPHERS_POOL = [
    "Marcus Aurelius", "Seneca", "Epictetus", "Friedrich Nietzsche", 
    "Arthur Schopenhauer", "Ralph Waldo Emerson", "Lao Tzu", "Sun Tzu", "Michel de Montaigne"
]

def generate_stoic_concept(raw_api_key, visual_theme, philosopher, custom_directive):
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

    candidate_models = []
    try:
        for m in client.models.list():
            name = m.name.replace("models/", "")
            if any(k in name.lower() for k in ["flash", "pro"]) and not any(k in name.lower() for k in ["embed", "vision", "imagen"]):
                candidate_models.append(name)
    except Exception as e:
        return None, f"Auth Error: {e}"

    if not candidate_models:
        candidate_models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-3.5-flash-lite"]

    errors = []
    for mod in candidate_models:
        try:
            resp = client.models.generate_content(
                model=mod,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            parsed = json.loads(resp.text)
            if "headline" in parsed and "body_text" in parsed:
                return parsed, None
        except Exception as e:
            errors.append(f"{mod}: {e}")
            continue
            
    return None, " | ".join(errors[:2])

# ---------------------------------------------------------
# 8. STREAMLIT UI: CONTROLS & STUDIO
# ---------------------------------------------------------
st.title("🏛️ Echoes Studio")
st.caption("Automated Mobile Production Engine")

api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
elif os.getenv("GEMINI_API_KEY"):
    api_key = str(os.getenv("GEMINI_API_KEY")).strip().strip('"').strip("'")

with st.expander("🔑 API Key Status", expanded=(not bool(api_key))):
    user_key_input = st.text_input("Enter or verify Gemini API Key", value=api_key, type="password")
    if user_key_input:
        api_key = user_key_input.strip().strip('"').strip("'")

rec_slot = get_next_recommended_slot()
st.info(f"📅 **Next Recommended Publishing Window:**\n\n**{rec_slot.strftime('%A, %b %d, %Y')} at 05:30 PM IST** (Spaced away from evening Reels).")

with st.expander("⚙️ Creative Controls & Voice Input", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        backdrop_options = [
            "🎲 Random / AI Best Match",
            "CLASSICAL_STATUE",
            "FINE_ART_PAINTING",
            "SEA_AND_CLIFFS",
            "CITADEL_AND_ARCHES",
            "ALPINE_AND_SUMMITS",
            "MISTY_FOREST",
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

    components.html("""
    <div style="font-family: sans-serif; margin-bottom: 8px;">
        <button id="micBtn" onclick="toggleSpeech()" style="background-color: #3b82f6; color: white; border: none; padding: 8px 14px; border-radius: 6px; font-weight: bold; cursor: pointer;">
            🎤 Tap to Speak Prompt
        </button>
        <span id="micStatus" style="font-size: 13px; color: #94a3b8; margin-left: 8px;"></span>
    </div>
    <script>
        var recognition;
        function toggleSpeech() {
            var status = document.getElementById("micStatus");
            var btn = document.getElementById("micBtn");
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                status.innerText = "Speech API not supported in browser. Use keyboard mic.";
                return;
            }
            var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onstart = function() {
                btn.style.backgroundColor = "#ef4444";
                btn.innerText = "🛑 Listening...";
                status.innerText = "Speak now...";
            };
            recognition.onresult = function(event) {
                var transcript = event.results[0][0].transcript;
                status.innerText = "Captured: " + transcript;
                var inputs = window.parent.document.querySelectorAll('input[type="text"]');
                for (var i = 0; i < inputs.length; i++) {
                    if (inputs[i].placeholder.includes("coworker") || inputs[i].getAttribute("aria-label") === "Voice / Custom Instruction") {
                        inputs[i].value = transcript;
                        inputs[i].dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }
            };
            recognition.onend = function() {
                btn.style.backgroundColor = "#3b82f6";
                btn.innerText = "🎤 Tap to Speak Prompt";
            };
            recognition.start();
        }
    </script>
    """, height=45)

    custom_input = st.text_input(
        "Voice / Custom Instruction",
        placeholder="e.g., Not letting coworker criticism break my stillness"
    )

generate_btn = st.button("🚀 Generate New Master Post", type="primary")

# ---------------------------------------------------------
# 9. EXECUTION & ACTIVE REVIEW
# ---------------------------------------------------------
if generate_btn:
    if not api_key:
        st.error("Please provide a valid Gemini API Key above.")
    else:
        with st.spinner("Synthesizing concept & rendering 4K canvas..."):
            theme_choice = selected_theme
            if theme_choice.startswith("🎲"):
                theme_choice = random.choice(list(EXPANDED_VAULT.keys()))
                
            concept, err = generate_stoic_concept(api_key, theme_choice, selected_philosopher, custom_input)
            
            if err or not concept:
                st.error(f"⚠️ API Error: {err}")
            else:
                vault_items = EXPANDED_VAULT.get(theme_choice, EXPANDED_VAULT["CLASSICAL_STATUE"])
                b_list = db.get("blacklisted_backdrops", [])
                available = [it for it in vault_items if it["name"] not in b_list]
                if not available:
                    available = vault_items
                chosen_item = random.choice(available)
                
                bg_image = fetch_image(chosen_item["url"])
                canvas_result = render_post_canvas(bg_image, concept)
                
                st.session_state["active_post"] = {
                    "concept": concept,
                    "canvas": canvas_result,
                    "backdrop_name": chosen_item["name"],
                    "target_date": rec_slot.strftime("%Y-%m-%d")
                }

# ---------------------------------------------------------
# 10. POST-GENERATION REVIEW & ACTIONS
# ---------------------------------------------------------
if "active_post" in st.session_state:
    post = st.session_state["active_post"]
    concept = post["concept"]
    canvas = post["canvas"]
    
    st.divider()
    st.subheader(f"🖼️ Preview: {concept['headline']}")
    
    st.image(canvas, use_container_width=True)
    
    buf = io.BytesIO()
    canvas.save(buf, format="PNG", quality=98)
    byte_im = buf.getvalue()
    filename = f"{post['target_date'].replace('-', '')}_{re.sub(r'[^a-zA-Z0-9]', '_', concept['headline']).lower()}.png"
    
    st.download_button(
        label="💾 Save Image to Phone Gallery",
        data=byte_im,
        file_name=filename,
        mime="image/png"
    )
    
    st.text_area("Caption (Ready for Meta Business Suite)", concept["post_caption"], height=160)
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✅ Approve & Log Date"):
            db["scheduled_posts"].append({
                "date": post["target_date"],
                "headline": concept["headline"],
                "filename": filename
            })
            db["last_scheduled_date"] = post["target_date"]
            save_db(db)
            st.success(f"Locked for {post['target_date']} at 5:30 PM IST!")
            st.rerun()
            
    with col_b:
        if st.button("❌ Discard & Never Repeat"):
            db["blacklisted_headlines"].append(concept["headline"])
            db["blacklisted_backdrops"].append(post["backdrop_name"])
            save_db(db)
            del st.session_state["active_post"]
            st.warning("Blacklisted headline and visual. Generating alternative...")
            st.rerun()

    st.markdown("""
    <div style="margin-top: 10px;">
        <a href="https://business.facebook.com/latest/composer" target="_blank" style="text-decoration: none;">
            <button style="width: 100%; height: 2.8rem; background-color: #1877f2; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">
                🌐 Open Meta Business Suite Scheduler
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)
