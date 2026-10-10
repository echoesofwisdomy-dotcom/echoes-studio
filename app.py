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
# 1. PAGE SETUP & OBSIDIAN TECH UI
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

    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 2.5rem !important;
    }

    .stApp {
        background-color: #080B11 !important;
        background-image: radial-gradient(circle at 50% -20%, #151e33 0%, #080B11 75%) !important;
        font-family: 'Space Grotesk', -apple-system, sans-serif !important;
        color: #E2E8F0 !important;
    }
    
    .block-container {
        padding-top: 4.2rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 680px !important;
    }

    /* Expander / Accordion Panels */
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

    /* Input Labels */
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

    .stTextInput>div>div>input, .stTextArea textarea, .stDateInput input, .stTimeInput input {
        background-color: #0A0F1D !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 8px !important;
        color: #F8FAFC !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 14px !important;
    }

    /* Primary Buttons */
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

    .stButton>button[kind="primary"]:hover,
    .stButton>button[kind="primary"]:focus,
    .stButton>button[kind="primary"]:active {
        background: linear-gradient(135deg, #0369A1 0%, #0284C7 100%) !important;
        color: #FFFFFF !important;
        border-color: #38BDF8 !important;
        box-shadow: 0 0 35px rgba(56, 189, 248, 0.6) !important;
        transform: translateY(-1px) !important;
    }

    /* Secondary Buttons */
    .stButton>button:not([kind="primary"]) {
        background: #111B30 !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        transition: all 0.2s ease !important;
    }

    .stButton>button:not([kind="primary"]):hover,
    .stButton>button:not([kind="primary"]):focus,
    .stButton>button:not([kind="primary"]):active {
        background: #172544 !important;
        color: #38BDF8 !important;
        border-color: #38BDF8 !important;
        box-shadow: 0 0 18px rgba(56, 189, 248, 0.35) !important;
    }

    /* Download Button */
    .stDownloadButton>button {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        color: white !important;
        border: 1px solid rgba(52, 211, 153, 0.4) !important;
        border-radius: 10px !important;
        height: 3.2rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        box-shadow: 0 0 20px rgba(5, 150, 105, 0.3) !important;
        transition: all 0.2s ease !important;
    }

    .stDownloadButton>button:hover,
    .stDownloadButton>button:focus,
    .stDownloadButton>button:active {
        background: linear-gradient(135deg, #047857 0%, #059669 100%) !important;
        color: #FFFFFF !important;
        border-color: #34D399 !important;
        box-shadow: 0 0 28px rgba(52, 211, 153, 0.5) !important;
    }

    /* Badges */
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
# 2. PERSISTENCE & HISTORY ENGINE (DEDUPLICATION LEDGER)
# ---------------------------------------------------------
DATA_DIR = os.path.join(os.getcwd(), "data")
FONTS_DIR = os.path.join(os.getcwd(), "fonts")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "studio_db.json")

def load_db():
    default_structure = {
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
                for k, v in default_structure.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            pass
    return default_structure

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
# 4. UNICODE MATHEMATICAL BOLD ENGINE (FOR FACEBOOK FEEDS)
# ---------------------------------------------------------
def to_unicode_bold(text):
    """
    Translates standard ASCII text into true Mathematical Sans-Serif Bold Unicode.
    Displays as real bold on Facebook and Instagram without asterisks.
    """
    normal_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    bold_chars   = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    trans = str.maketrans(normal_chars, bold_chars)
    return text.translate(trans)

# ---------------------------------------------------------
# 5. CURATED 50 HIGH-ENGAGEMENT VISUAL VAULT
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
        {"name": "Evening City Skyline from Quiet Study", "url": "https://images.unsplash.com/photo-1506157786151-b8491531f063?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ]
}

# ---------------------------------------------------------
# 6. DYNAMIC CADENCE ENGINE (24-HOUR MILITARY FORMAT)
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
# 7. FAIL-SAFE GRAPHICS & COMPOSITOR
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
    
    # 1. Category Pill with Drawn Vector Wings
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
        
    # 5. Attribution with Vector Wings
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
# 8. HIGH-CONVERSION CAPTION FORMATTER
# ---------------------------------------------------------
def format_high_conversion_caption(raw_hook, lesson, quote, attribution, deb_q, choice1, choice2, tags):
    """
    Builds a structured caption with Unicode Bold on the primary hook
    to maximize click-through before Facebook's '...see more' cutoff.
    """
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
        f"• Follow @EchoesOfWisdom for timeless clarity.",
        "",
        f"{tags.strip()}"
    ]
    return "\n".join(caption_lines)

# ---------------------------------------------------------
# 9. ZERO-DUPLICATION AI SYNTHESIS (GEMINI 3.8 FLASH)
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
    You are the Head Copywriter for 'Echoes of Wisdom'.
    Theme: {visual_theme}
    Featured Thinker: {target_philosopher}
    User Direction/Focus: {custom_directive or 'Synthesize an original, profound, and impactful lesson on mental clarity and unshakeable discipline.'}

    CRITICAL ANTI-DUPLICATION RULE:
    The following headlines have ALREADY BEEN PUBLISHED. You are STRICTLY FORBIDDEN from repeating them:
    {blacklist_str}

    Requirements:
    1. headline: 2 to 4 bold commanding words for the image canvas (e.g. RULE YOUR SOLITUDE, TAMING THE MIND).
    2. body_text: 12 to 18 words on the canvas explaining the hook.
    3. caption_hook: 4 to 7 explosive words designed to stop the mobile scroll (e.g. MOST MEN NEVER CONQUER SILENCE).
    4. caption_lesson: 2 crisp sentences explaining the psychological truth of this quote.
    5. debate_question: 1 compelling question framing an internal dilemma.
    6. choice_1: The Stoic master reaction.
    7. choice_2: The impulsive reaction.
    8. hashtags: 5 curated hashtags (#Stoicism #Philosophy #Discipline #EchoesOfWisdom #MarcusAurelius).

    Output STRICT JSON ONLY:
    {{
      "category": "CONCISE PILLAR (e.g. INNER CITADEL, EMOTIONAL MASTERY, DEEP FOCUS, FORTITUDE)",
      "headline": "BOLD 2-4 WORD HOOK",
      "body_text": "One powerful 12-18 word sentence explaining the hook.",
      "attribution": "{target_philosopher.upper()}",
      "caption_hook": "PUNCHY 4-7 WORD SCROLL STOPPER",
      "caption_lesson": "Two sentences of high-value wisdom.",
      "debate_question": "Which path do you choose?",
      "choice_1": "Master option",
      "choice_2": "Impulsive option",
      "hashtags": "#Stoicism #Philosophy #MarcusAurelius #Wisdom #Discipline"
    }}
    """

    candidate_models = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-flash-latest"]
    errs = []
    
    for mod in candidate_models:
        try:
            resp = client.models.generate_content(
                model=mod,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.9
                )
            )
            parsed = json.loads(resp.text)
            if "headline" in parsed and "body_text" in parsed:
                if parsed["headline"].upper() not in used:
                    db["last_philosopher"] = target_philosopher
                    
                    # Assemble the high-conversion Unicode bold caption
                    full_caption = format_high_conversion_caption(
                        raw_hook=parsed.get("caption_hook", parsed["headline"]),
                        lesson=parsed.get("caption_lesson", parsed["body_text"]),
                        quote=parsed["body_text"],
                        attribution=parsed["attribution"],
                        deb_q=parsed.get("debate_question", "When chaos strikes your day:"),
                        choice1=parsed.get("choice_1", "Stand firm in stillness"),
                        choice2=parsed.get("choice_2", "React and lose control"),
                        tags=parsed.get("hashtags", "#Stoicism #Wisdom #InnerStrength")
                    )
                    parsed["post_caption"] = full_caption
                    return parsed, None
        except Exception as e:
            errs.append(f"{mod}: {e}")
            continue

    return None, " | ".join(errs)

# ---------------------------------------------------------
# 10. OBSIDIAN DASHBOARD UI
# ---------------------------------------------------------
st.markdown("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <div style="font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: #F8FAFC;">
        ⚡ ECHOES STUDIO <span style="font-size: 13px; color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-weight: 500;">v3.1 // VIRAL COPY</span>
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
formatted_time_24h = next_target_dt.strftime("%H:%M")

# Telemetry Status Bar
st.markdown(f"""
<div class="telemetry-bar">
    <div class="badge badge-green"><span class="dot"></span> ENGINE: READY</div>
    <div class="badge badge-blue">⚡ GEMINI 3.8 FLASH</div>
    <div class="badge badge-amber">📅 NEXT DROP: {next_target_dt.strftime('%a, %b %d')} @ {formatted_time_24h} IST</div>
</div>
""", unsafe_allow_html=True)

# Confirmation Banner
if "lock_notification" in st.session_state:
    st.markdown(f"""
    <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; border-radius: 10px; padding: 12px 16px; margin-bottom: 16px; font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #34D399;">
        {st.session_state['lock_notification']}
    </div>
    """, unsafe_allow_html=True)
    del st.session_state["lock_notification"]

# Cadence Manager Accordion
with st.expander("📅 PUBLISHING CADENCE & TIME MANAGER", expanded=False):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        custom_last_d = st.date_input(
            "Last Scheduled Date",
            value=saved_last_date if saved_last_date else datetime.now(timezone(timedelta(hours=5, minutes=30))).date()
        )
    with col_c2:
        parsed_t = parse_time_str(default_time)
        custom_t = st.time_input("Daily Drop Time (24h IST)", value=parsed_t)

    if st.button("💾 Save Schedule Cadence Preference"):
        db["last_scheduled_date"] = custom_last_d.strftime("%Y-%m-%d")
        db["default_time_ist"] = custom_t.strftime("%H:%M")
        save_db(db)
        st.session_state["lock_notification"] = f"✓ CADENCE SAVED: Next slot advances from {db['last_scheduled_date']} @ {db['default_time_ist']} IST"
        st.rerun()

# API Key Resolution
api_key = ""
if "GEMINI_API_KEY" in st.secrets:
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
elif os.getenv("GEMINI_API_KEY"):
    api_key = str(os.getenv("GEMINI_API_KEY")).strip().strip('"').strip("'")

with st.expander("🔑 API CREDENTIALS", expanded=(not bool(api_key))):
    user_key = st.text_input("Gemini API Key", value=api_key, type="password", placeholder="AIzaSy...")
    if user_key:
        api_key = user_key.strip().strip('"').strip("'")

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
# 11. EXECUTION PIPELINE
# ---------------------------------------------------------
if generate_btn:
    if not api_key:
        st.error("Missing Gemini API Key. Open the '🔑 API CREDENTIALS' panel above.")
    else:
        with st.spinner("⚡ Synthesizing unique concept with Gemini 3.8 Flash..."):
            theme_choice = selected_theme
            if theme_choice.startswith("🎲"):
                theme_choice = random.choice(list(EXPANDED_VAULT.keys()))
                
            concept, err = generate_stoic_concept_deduped(api_key, theme_choice, selected_philosopher, custom_input)
            
            if err or not concept:
                st.error(f"⚠️ Synthesis Blocked: {err}. Please verify your Gemini API key.")
            else:
                vault_items = EXPANDED_VAULT.get(theme_choice, EXPANDED_VAULT["CLASSICAL_STATUE"])
                
                # Round-robin backdrop selection
                used_bd = set(db.get("used_backdrops", []))
                fresh_backdrops = [it for it in vault_items if it["name"] not in used_bd]
                
                if not fresh_backdrops:
                    db["used_backdrops"] = [b for b in db.get("used_backdrops", []) if b not in [it["name"] for it in vault_items]]
                    fresh_backdrops = vault_items

                chosen_item = random.choice(fresh_backdrops)
                
                bg_image = fetch_image_resilient(chosen_item["url"], vault_items)
                canvas_result = render_post_canvas(bg_image, concept)
                
                st.session_state["active_post"] = {
                    "concept": concept,
                    "canvas": canvas_result,
                    "backdrop_name": chosen_item["name"],
                    "target_date": next_target_dt.strftime("%Y-%m-%d"),
                    "target_time_display": formatted_time_24h
                }

# ---------------------------------------------------------
# 12. ACTIVE ASSET TERMINAL & 1-TAP INLINE CLIPBOARD
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
        label="💾 Save Master Image to Phone Gallery",
        data=byte_im,
        file_name=filename,
        mime="image/png"
    )
    
    st.text_area("Caption (Ready for Meta Business Suite)", concept["post_caption"], height=200)
    
    # 1-Tap Copy Deck
    escaped_caption = json.dumps(concept["post_caption"])
    components.html(f"""
    <div style="margin: 0; padding: 0;">
        <button id="copyBtn" onclick="copyCaption()" style="width: 100%; height: 2.85rem; background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.4); border-radius: 8px; font-weight: 700; font-family: 'JetBrains Mono', monospace; font-size: 13px; cursor: pointer; letter-spacing: 0.04em; transition: all 0.2s;">
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
                btn.style.borderColor = "#34D399";
                setTimeout(function() {{
                    btn.innerText = "📋 COPY CAPTION TO CLIPBOARD";
                    btn.style.background = "rgba(56, 189, 248, 0.15)";
                    btn.style.color = "#38BDF8";
                    btn.style.borderColor = "rgba(56, 189, 248, 0.4)";
                }}, 2500);
            }}

            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(setSuccess).catch(function() {{
                    fallbackCopy(text);
                }});
            }} else {{
                fallbackCopy(text);
            }}

            function fallbackCopy(str) {{
                var el = document.createElement('textarea');
                el.value = str;
                el.setAttribute('readonly', '');
                el.style.position = 'absolute';
                el.style.left = '-9999px';
                document.body.appendChild(el);
                el.select();
                try {{
                    document.execCommand('copy');
                    setSuccess();
                }} catch(err) {{}}
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
            
            st.session_state["lock_notification"] = f"✓ LOCKED: '{concept['headline']}' logged for {post['target_date']} @ {post.get('target_time_display', '17:30')} IST. Slot advanced!"
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
            st.session_state["lock_notification"] = f"⚠ Concept '{concept['headline']}' blacklisted. Re-rolling visual & prompt..."
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

# ---------------------------------------------------------
# 13. AUDIT LOG & SCHEDULED QUEUE VIEWER
# ---------------------------------------------------------
if db.get("scheduled_posts"):
    with st.expander(f"📋 SCHEDULED QUEUE & LOGGED POSTS ({len(db['scheduled_posts'])})", expanded=False):
        for idx, item in enumerate(reversed(db["scheduled_posts"])):
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
