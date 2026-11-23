import os, io, json, re, random, base64, requests
from datetime import datetime, timedelta, timezone, time as dt_time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# ---------------------------------------------------------
# 1. PAGE SETUP & OBSIDIAN STUDIO UI
# ---------------------------------------------------------
st.set_page_config(page_title="Echoes Image Studio", page_icon="🏛️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
    header[data-testid="stHeader"] { background: transparent !important; }
    .stApp {
        background-color: #080B11 !important;
        background-image: radial-gradient(circle at 50% -20%, #151e33 0%, #080B11 75%) !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        color: #E2E8F0 !important;
    }
    .block-container { padding-top: 3.2rem !important; padding-bottom: 3rem !important; max-width: 720px !important; }
    div[data-testid="stExpander"] {
        background: #0E1626 !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 12px !important;
        margin-bottom: 1rem !important;
    }
    div[data-testid="stExpander"] summary {
        background: #111B30 !important;
        color: #38BDF8 !important;
        font-size: 13px !important;
        font-weight: 700 !important;
    }
    label[data-testid="stWidgetLabel"] p {
        color: #94A3B8 !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
    }
    .stTextInput>div>div>input, .stTextArea textarea {
        background-color: #0A0F1D !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        color: #F8FAFC !important;
        border-radius: 8px !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
        color: #FFF !important;
        border-radius: 10px !important;
        height: 3.4rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        width: 100% !important;
    }
    .stButton>button:not([kind="primary"]) {
        background: #111B30 !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(56, 189, 248, 0.25) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stDownloadButton>button {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
        color: white !important;
        border-radius: 10px !important;
        height: 3.2rem !important;
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
        margin: 2px;
    }
    .badge-green  { background: rgba(16, 185, 129, 0.12); color: #34D399; border: 1px solid rgba(52, 211, 153, 0.25); }
    .badge-blue   { background: rgba(56, 189, 248, 0.12); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.25); }
    .badge-amber  { background: rgba(245, 158, 11, 0.12); color: #FBBF24; border: 1px solid rgba(251, 191, 36, 0.25); }
    .badge-purple { background: rgba(168, 85, 247, 0.12); color: #C084FC; border: 1px solid rgba(168, 85, 247, 0.25); }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. PATHWAYS & PERSISTENT STORAGE
# ---------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
BG_CACHE_DIR = os.path.join(BASE_DIR, "bg_cache")

for d in [DATA_DIR, FONTS_DIR, BG_CACHE_DIR]:
    os.makedirs(d, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "image_schedule.json")
CARD_VAULT_PATH = os.path.join(DATA_DIR, "image_card_vault.json")
ACTIVE_CARD_PATH = os.path.join(DATA_DIR, "active_image_card.json")
SAVED_BG_PATH = os.path.join(DATA_DIR, "saved_custom_bg.png")
API_KEY_FILE = os.path.join(DATA_DIR, "gemini_key.txt")
CHANNEL_HANDLE_FILE = os.path.join(DATA_DIR, "meta_handle.txt")
GUIDE_URL_FILE = os.path.join(DATA_DIR, "guide_url.txt")
EXCEL_IMAGE_TRACKER = os.path.join(DATA_DIR, "Echoes_Image_Content_Tracker.xlsx")

@st.cache_resource(show_spinner=False)
def ensure_studio_fonts():
    bold_p = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")
    reg_p = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
    serif_p = os.path.join(FONTS_DIR, "DejaVuSerif-Bold.ttf")
    italic_p = os.path.join(FONTS_DIR, "DejaVuSerif-Italic.ttf")
    mono_p = os.path.join(FONTS_DIR, "DejaVuSansMono-Bold.ttf")
    urls = {
        bold_p: "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans-Bold.ttf",
        reg_p: "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf",
        serif_p: "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSerif-Bold.ttf",
        italic_p: "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSerif-Italic.ttf",
        mono_p: "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSansMono-Bold.ttf",
    }
    for path, url in urls.items():
        if not os.path.exists(path) or os.path.getsize(path) < 10000:
            try:
                r = requests.get(url, timeout=8)
                if r.status_code == 200 and len(r.content) > 10000:
                    with open(path, "wb") as f:
                        f.write(r.content)
            except Exception:
                pass
    return bold_p, reg_p, serif_p, italic_p, mono_p

BOLD_FONT_PATH, REG_FONT_PATH, SERIF_FONT_PATH, ITALIC_FONT_PATH, MONO_FONT_PATH = ensure_studio_fonts()

def load_font(path, size):
    try:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    return ImageFont.load_default()

def get_persistent_api_key():
    if st.session_state.get("img_key_input"):
        return st.session_state["img_key_input"].strip().strip('"').strip("'")
    if "GEMINI_API_KEY" in st.secrets:
        return str(st.secrets["GEMINI_API_KEY"]).strip().strip('"').strip("'")
    if os.getenv("GEMINI_API_KEY"):
        return os.getenv("GEMINI_API_KEY").strip()
    if os.path.exists(API_KEY_FILE):
        try:
            with open(API_KEY_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            pass
    return ""

def save_persistent_api_key(val):
    clean = val.strip().strip('"').strip("'")
    try:
        with open(API_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(clean)
    except Exception:
        pass

def get_persistent_handle():
    if "META_CHANNEL_HANDLE" in st.secrets:
        return str(st.secrets["META_CHANNEL_HANDLE"]).strip()
    if os.path.exists(CHANNEL_HANDLE_FILE):
        try:
            with open(CHANNEL_HANDLE_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            pass
    return "@EchoesOfWisdomOfficial"

def save_persistent_handle(val):
    clean = val.strip()
    if clean and not clean.startswith("@"):
        clean = "@" + clean
    try:
        with open(CHANNEL_HANDLE_FILE, "w", encoding="utf-8") as f:
            f.write(clean)
    except Exception:
        pass

def get_persistent_guide_url():
    if os.path.exists(GUIDE_URL_FILE):
        try:
            with open(GUIDE_URL_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            pass
    return "https://theechoesofwisdom.gumroad.com/l/stoic-guide"

def save_persistent_guide_url(val):
    try:
        with open(GUIDE_URL_FILE, "w", encoding="utf-8") as f:
            f.write(val.strip())
    except Exception:
        pass

@st.cache_resource(show_spinner=False)
def get_fast_gemini_client(clean_k):
    try:
        return genai.Client(
            api_key=clean_k,
            http_options=types.HttpOptions(timeout=15000)
        )
    except Exception:
        return genai.Client(api_key=clean_k)

def load_db():
    default_db = {
        "scheduled_posts": [],
        "used_headlines": [],
        "used_card_ids": [],
        "last_date": None,
        "post_time": "17:30"
    }
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_db.update(data)
        except Exception:
            pass
    return default_db

def save_db(data):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

db = load_db()

def load_card_vault_history():
    if os.path.exists(CARD_VAULT_PATH):
        try:
            with open(CARD_VAULT_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_to_card_vault_history(card_item):
    vault = load_card_vault_history()
    h = card_item.get("headline", "")
    vault = [v for v in vault if v.get("headline") != h]
    vault.insert(0, card_item)
    vault = vault[:30]
    try:
        with open(CARD_VAULT_PATH, "w", encoding="utf-8") as f:
            json.dump(vault, f, indent=2)
    except Exception:
        pass

def save_active_card_to_disk(card_item, src_str="Saved Card"):
    try:
        with open(ACTIVE_CARD_PATH, "w", encoding="utf-8") as f:
            json.dump({"card": card_item, "src": src_str}, f, indent=2)
    except Exception:
        pass

def get_next_post_date():
    now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    ld_str = db.get("last_date")
    if ld_str:
        try:
            ld = datetime.strptime(str(ld_str), "%Y-%m-%d").date()
            return (ld + timedelta(days=1)).strftime("%Y-%m-%d")
        except Exception:
            pass
    return now_ist.date().strftime("%Y-%m-%d")

# ---------------------------------------------------------
# 3. 8 CARD FORMATS, 6 PALETTES, 18+ LEADERS & MODERN/ANCIENT VAULT
# ---------------------------------------------------------
PILLAR_DEFINITIONS = {
    "ALL": "🎲 Smart AI Rotation (All 5 Pillars)",
    "SOVEREIGNTY": "🛡️ Silent Power & Boundaries",
    "FINANCE": "⚖️ Financial Sovereignty & Control",
    "LEGACY": "🏛️ Father to Son: Legacy Counsel",
    "LONGEVITY": "⏳ Aging Well: Vitality After 40/60",
    "PARABLES": "🌲 Ancient & Modern Parables"
}

FORMAT_STYLES = {
    "CHISELED_HERO": {
        "label": "🏛️ Chiseled Hero Card (Ornate Frame + Diamond Divider)",
        "desc": "Framed dark art with double corner brackets, diamond dividers, chiseled headline & reflection strip."
    },
    "MINIMAL_TYPO": {
        "label": "✍️ Minimal Typographic Poster (Corner Brackets + Highlight Words)",
        "desc": "Clean obsidian canvas with geometric corner brackets, left accent bar, serif quote & highlighted words."
    },
    "HIGHLIGHT_STORY": {
        "label": "💛 Highlighted Story Card (Warm Cream + Marker Lead-In)",
        "desc": "Warm daylight card with rounded marker-highlighted lead-in phrase and modern/illustrative lower art."
    },
    "SYMBOLIC_PORTRAIT": {
        "label": "📜 Parchment Parable + Portrait (Classic Leader Card)",
        "desc": "Warm parchment canvas with bold crimson/gold serif quote, diamond divider & lower portrait."
    },
    "SYMBOL_SANDWICH": {
        "label": "🔺 Sacred Geometry Emblem Card (Star & Compass Shapes)",
        "desc": "Dark canvas framed by geometric star & compass emblems at top & bottom with provoking hook."
    },
    "BATTLEFIELD_VOW": {
        "label": "⚔️ Full-Bleed Scene + Accent Power Word Vow",
        "desc": "Full-bleed dramatic/modern scene with framed rules and a single vivid accent power word."
    },
    "NUMBERED_CHECKLIST": {
        "label": "📋 5-Point Behavioral Checklist (Numbered Circle Badges)",
        "desc": "Structured 5-point list with circular numbered badges, horizontal rules & reflection footer."
    },
    "MODERN_CONTRAST": {
        "label": "🔀 Ancient Principle vs. Modern Trap (Split Contrast Cards)",
        "desc": "Two rounded contrast boxes comparing what drains your strength vs. what builds lasting power."
    }
}

ACCENT_PALETTES = {
    "IMPERIAL_GOLD":  {"label": "👑 Imperial Gold",    "primary": (235, 192, 96, 255),  "secondary": (254, 240, 138, 220), "bg_tone": "GOLD"},
    "GLACIAL_ICE":    {"label": "❄️ Glacial Cyan",     "primary": (110, 225, 245, 255), "secondary": (165, 243, 252, 220), "bg_tone": "ICE"},
    "FORGE_AMBER":    {"label": "🔥 Forge Amber",      "primary": (245, 162, 72, 255),  "secondary": (253, 224, 71, 220),  "bg_tone": "AMBER"},
    "CRIMSON_IVORY":  {"label": "🩸 Crimson & Ivory",  "primary": (225, 72, 66, 255),   "secondary": (254, 202, 202, 220), "bg_tone": "AMBER"},
    "EMERALD_BONE":   {"label": "🌿 Emerald & Bone",   "primary": (74, 222, 128, 255),  "secondary": (187, 247, 208, 220), "bg_tone": "ICE"},
    "ROYAL_VIOLET":   {"label": "🔮 Royal Violet",     "primary": (216, 140, 255, 255), "secondary": (243, 232, 255, 220), "bg_tone": "GOLD"},
}

LEADER_WISDOM_POOL = [
    {"leader": "ABRAHAM LINCOLN",    "era": "Modern History",   "quote": "\"Give me six hours to chop down a tree and I will spend the first four sharpening the axe.\""},
    {"leader": "MARCUS AURELIUS",    "era": "Ancient Rome",     "quote": "\"You have power over your mind, not outside events. Realize this, and you will find strength.\""},
    {"leader": "WINSTON CHURCHILL",  "era": "Modern History",   "quote": "\"Success is walking from failure to failure without losing your enthusiasm.\""},
    {"leader": "NELSON MANDELA",     "era": "Modern History",   "quote": "\"Resentment is like drinking poison and then hoping it will harm your enemies.\""},
    {"leader": "THEODORE ROOSEVELT", "era": "Modern History",   "quote": "\"The credit belongs to the person who is actually in the arena, whose face is marred by dust and sweat.\""},
    {"leader": "BENJAMIN FRANKLIN",  "era": "Enlightenment",    "quote": "\"Beware of little expenses; a small leak will sink a great ship.\""},
    {"leader": "ALBERT EINSTEIN",    "era": "Modern Science",   "quote": "\"Strive not to be a success, but rather to be of value.\""},
    {"leader": "BRUCE LEE",          "era": "Modern Philosophy","quote": "\"Be water, my friend—empty your mind, be formless, shapeless, adaptable.\""},
    {"leader": "SENECA",             "era": "Ancient Rome",     "quote": "\"We suffer more often in imagination than in reality.\""},
    {"leader": "EPICTETUS",          "era": "Ancient Greece",   "quote": "\"It is not what happens to you, but how you react to it that matters.\""},
    {"leader": "VIKTOR FRANKL",      "era": "Modern Psychology","quote": "\"Between stimulus and response there is a space. In that space is our power to choose.\""},
    {"leader": "CHARLIE MUNGER",     "era": "Modern Finance",   "quote": "\"It is remarkable how much long-term advantage people have gotten by trying to be consistently not stupid.\""},
    {"leader": "MIYAMOTO MUSASHI",   "era": "Feudal Japan",     "quote": "\"Do nothing that is of no use; master the rhythm of patience and timing.\""},
    {"leader": "LAO TZU",            "era": "Ancient China",    "quote": "\"Nature does not hurry, yet everything is accomplished.\""},
    {"leader": "SOCRATES",           "era": "Ancient Greece",   "quote": "\"When the debate is lost, slander becomes the tool of the loser.\""},
    {"leader": "CARL JUNG",          "era": "Modern Psychology","quote": "\"Until you make the unconscious conscious, it will direct your life and you will call it fate.\""},
    {"leader": "GEORGE WASHINGTON",  "era": "Modern History",   "quote": "\"Be courteous to all, but intimate with few, and let those few be well tried before you give them confidence.\""},
    {"leader": "SUN TZU",            "era": "Ancient China",    "quote": "\"Appear weak when you are strong, and strong when you are weak.\""}
]

CONTENT_CARDS_VAULT = [
    # 1. CHISELED_HERO (Ancient + Ornate Frame)
    {
        "id": "IMG_UNGRASPABLE",
        "pillar": "SOVEREIGNTY",
        "format_style": "CHISELED_HERO",
        "palette": "IMPERIAL_GOLD",
        "category": "SILENT POWER",
        "headline": "BECOME COMPLETELY UNGRASPABLE",
        "quote": "\"He who displays no edge cannot be blunted, disarming adversaries through impenetrable strategic calm.\"",
        "author": "LAO TZU • ANCIENT CHINA",
        "accent_word": "UNGRASPABLE",
        "reflection_prompt": "WHEN CHALLENGED PUBLICLY, WHAT HELPS YOU KEEP YOUR COMPOSURE?",
        "sub_prompt": "SHARE YOUR EXPERIENCE IN THE COMMENTS",
        "bg_scene": "Classical dark oil painting of misty mountain peaks and ancient stone watchtower at twilight, museum canvas texture",
        "caption_story": "The loudest person in the room is always the easiest to read. When you refuse to broadcast your anger, your plans, or your insecurities, nobody can find a handle to pull you off balance.",
        "tags": "#Stoicism #EmotionalMastery #SelfControl #Mindset #LifeLessons"
    },
    # 2. MINIMAL_TYPO (Modern Finance + Selective Highlight)
    {
        "id": "IMG_MONEY_TRUTH_MINIMAL",
        "pillar": "FINANCE",
        "format_style": "MINIMAL_TYPO",
        "palette": "IMPERIAL_GOLD",
        "category": "MONEY REALITY",
        "headline": "Hard truth about money:",
        "quote": "Nobody pays your bills out of sympathy. Nobody funds your dreams out of obligation. Nobody protects your future better than you.",
        "author": "BENJAMIN FRANKLIN INSIGHT",
        "accent_word": "protects",
        "reflection_prompt": "WHAT IS ONE MONEY HABIT THAT GAVE YOU PEACE OF MIND?",
        "sub_prompt": "SHARE YOUR PERSPECTIVE IN THE COMMENTS",
        "bg_scene": "Clean minimal obsidian charcoal background with subtle warm radial rim light, editorial poster style",
        "caption_story": "Sympathy never covers a mortgage, and obligation never builds security. Taking full ownership of your habits and savings is the quietest form of independence.",
        "tags": "#MoneyMindset #FinancialFreedom #Discipline #Stoicism #LifeLessons"
    },
    # 3. HIGHLIGHT_STORY (Modern Everyday Realism + Marker Highlight)
    {
        "id": "IMG_MODERN_REBUILD_STORY",
        "pillar": "FINANCE",
        "format_style": "HIGHLIGHT_STORY",
        "palette": "EMERALD_BONE",
        "category": "MODERN REALITY",
        "headline": "Nobody talks about this:",
        "quote": "\"The quietest years of your life—when you skip applause, cut waste, and fix your habits in private—are the exact years that buy your freedom.\"",
        "author": "MODERN REFLECTION",
        "accent_word": "freedom",
        "reflection_prompt": "WHAT ARE YOU REBUILDING QUIETLY BEHIND CLOSED DOORS RIGHT NOW?",
        "sub_prompt": "SHARE YOUR THOUGHTS BELOW",
        "bg_scene": "Modern sunlit city apartment window at dawn with a warm cup of coffee and clean notebook on an oak desk, realistic photography",
        "caption_story": "Most growth happens far away from social media—in early mornings, skipped status purchases, and quiet consistency. Keep showing up even while the scoreboard looks still.",
        "tags": "#Mindset #Discipline #LifeAfter40 #PersonalGrowth #Wisdom"
    },
    # 4. SYMBOLIC_PORTRAIT (Leader Wisdom + Classic Portrait)
    {
        "id": "IMG_LINCOLN_SHARPEN_AXE",
        "pillar": "LEGACY",
        "format_style": "SYMBOLIC_PORTRAIT",
        "palette": "CRIMSON_IVORY",
        "category": "LEADER WISDOM",
        "headline": "Give me six hours to chop down a tree and I will spend the first four sharpening the axe.",
        "quote": "Preparation beats last-minute panic every single time.",
        "author": "ABRAHAM LINCOLN",
        "accent_word": "sharpening",
        "reflection_prompt": "WHERE HAS EXTRA PREPARATION SAVED YOU FROM UNNECESSARY STRESS?",
        "sub_prompt": "SHARE YOUR EXPERIENCE IN THE COMMENTS",
        "bg_scene": "Warm parchment studio portrait of a thoughtful nineteenth-century statesman with weathered features and calm resolve, classic engraving style",
        "caption_story": "Rushing into hard decisions without preparation creates avoidable mistakes. Four hours of quiet planning can save four months of cleanup.",
        "tags": "#AbrahamLincoln #Leadership #Preparation #Wisdom #LifeLessons"
    },
    # 5. SYMBOL_SANDWICH (Sacred Geometry + Provoking Question)
    {
        "id": "IMG_FRANKL_SPACE_BETWEEN",
        "pillar": "SOVEREIGNTY",
        "format_style": "SYMBOL_SANDWICH",
        "palette": "GLACIAL_ICE",
        "category": "INNER FREEDOM",
        "headline": "BETWEEN PROVOCATION AND REACTION LIES YOUR ONLY REAL FREEDOM.",
        "quote": "Lose your temper, and a stranger becomes your master.",
        "author": "VIKTOR FRANKL • MODERN PSYCHOLOGY",
        "accent_word": "FREEDOM",
        "reflection_prompt": "HOW DO YOU STOP YOURSELF FROM REACTING IN THE HEAT OF THE MOMENT?",
        "sub_prompt": "SHARE YOUR PERSPECTIVE BELOW",
        "bg_scene": "Dark obsidian slate background with sacred geometric star and compass lines",
        "caption_story": "Viktor Frankl proved that even under extreme pressure, a human being still owns the space between what happens and how they respond. Guard that space fiercely.",
        "tags": "#ViktorFrankl #SelfControl #EmotionalIntelligence #Mindset #Stoicism"
    },
    # 6. BATTLEFIELD_VOW (Dramatic Scene + Single Accent Word)
    {
        "id": "IMG_ROOSEVELT_ARENA_VOW",
        "pillar": "SOVEREIGNTY",
        "format_style": "BATTLEFIELD_VOW",
        "palette": "FORGE_AMBER",
        "category": "IN THE ARENA",
        "headline": "Ignore the critics. Stay in the arena.",
        "quote": "People who build nothing always have plenty of advice.",
        "author": "THEODORE ROOSEVELT",
        "accent_word": "arena.",
        "reflection_prompt": "HOW DO YOU TUNE OUT CRITICS WHO HAVEN'T WALKED IN YOUR SHOES?",
        "sub_prompt": "SHARE YOUR THOUGHTS BELOW",
        "bg_scene": "Dramatic cinematic scene of a lone weathered contender standing under moody storm clouds and golden sunbeams, epic lighting",
        "caption_story": "It is easy to judge from the bleachers when nothing is on the line. Keep your eyes on the work in front of you and let results answer the noise.",
        "tags": "#TheodoreRoosevelt #Resilience #Discipline #Mindset #Courage"
    },
    # 7. NUMBERED_CHECKLIST (5-Point High-Save List)
    {
        "id": "IMG_FIVE_SILENT_RULES",
        "pillar": "PARABLES",
        "format_style": "NUMBERED_CHECKLIST",
        "palette": "IMPERIAL_GOLD",
        "category": "DAILY CODE",
        "headline": "5 PLACES TO STAY SILENT AT ALL COSTS:",
        "quote": "1. When anger wants the first word. | 2. When you do not know the full facts. | 3. When someone baits you into a pointless fight. | 4. When your private plans are still unfinished. | 5. When actions will prove it better.",
        "author": "ANCIENT & MODERN CODE",
        "accent_word": "SILENT",
        "reflection_prompt": "WHICH OF THESE FIVE MOMENTS IS HARDEST FOR YOU TO HOLD SILENCE?",
        "sub_prompt": "SAVE THIS LIST FOR TOUGH CONVERSATIONS",
        "bg_scene": "Deep dark slate textured background with subtle architectural shadows",
        "caption_story": "Silence is not weakness when you hold composure—it is leverage. A single measured pause can protect a relationship, a career move, or your peace of mind.",
        "tags": "#SelfControl #Boundaries #Communication #Stoicism #LifeLessons"
    },
    # 8. MODERN_CONTRAST (Ancient Principle vs. Modern Trap)
    {
        "id": "IMG_MANDELA_POISON_CONTRAST",
        "pillar": "LONGEVITY",
        "format_style": "MODERN_CONTRAST",
        "palette": "ROYAL_VIOLET",
        "category": "PEACE AFTER 40",
        "headline": "RESENTMENT VS. FREEDOM",
        "quote": "HOLDING BITTERNESS: Drinking poison while hoping your enemy suffers. | LETTING IT GO: Reclaiming your sleep, health, and peace after forty.",
        "author": "NELSON MANDELA WISDOM",
        "accent_word": "FREEDOM",
        "reflection_prompt": "WHAT OLD GRUDGE OR WORRY ARE YOU GLAD YOU FINALLY LEFT BEHIND?",
        "sub_prompt": "YOUR EXPERIENCE HELPS OTHERS GROW",
        "bg_scene": "Moody modern dusk skyline reflected in still dark water",
        "caption_story": "Nelson Mandela warned that holding onto resentment poisons the person carrying it while the other person sleeps peacefully. Forgive for your own freedom.",
        "tags": "#NelsonMandela #PeaceOfMind #LifeAfter40 #EmotionalHealth #Wisdom"
    },
    # 9. MODERN EVERYDAY + BRUCE LEE ADAPTABILITY
    {
        "id": "IMG_BRUCE_LEE_BAMBOO",
        "pillar": "PARABLES",
        "format_style": "HIGHLIGHT_STORY",
        "palette": "EMERALD_BONE",
        "category": "ADAPTABILITY",
        "headline": "A lesson from Bruce Lee:",
        "quote": "\"Notice that the stiffest tree is most easily cracked, while the bamboo survives by bending with the wind.\"",
        "author": "BRUCE LEE",
        "accent_word": "bending",
        "reflection_prompt": "WHEN DID ADAPTING YOUR PLAN WORK BETTER THAN FORCING IT?",
        "sub_prompt": "SHARE YOUR STORY IN THE COMMENTS",
        "bg_scene": "Sunlit modern bamboo grove beside a calm stone walkway in morning mist, crisp natural photography",
        "caption_story": "Rigid pride snaps when life throws an unexpected curveball. Stay anchored in your core principles while staying flexible in your strategy.",
        "tags": "#BruceLee #Adaptability #Mindset #Resilience #Wisdom"
    },
    # 10. MODERN FINANCE + CHARLIE MUNGER
    {
        "id": "IMG_MUNGER_AVOID_STUPIDITY",
        "pillar": "FINANCE",
        "format_style": "MINIMAL_TYPO",
        "palette": "GLACIAL_ICE",
        "category": "COMPOUNDING EDGE",
        "headline": "Charlie Munger's quiet edge:",
        "quote": "You do not need to be brilliant every day. You build massive long-term advantage simply by consistently avoiding foolish mistakes.",
        "author": "CHARLIE MUNGER",
        "accent_word": "avoiding",
        "reflection_prompt": "WHAT IS ONE MISTAKE YOU AVOIDED THAT PAID OFF YEARS LATER?",
        "sub_prompt": "SHARE YOUR PERSPECTIVE IN THE COMMENTS",
        "bg_scene": "Clean minimal obsidian dark background with cool cyan ambient glow",
        "caption_story": "Most financial and personal setbacks come from unforced errors—impulse debt, toxic partnerships, and impatience. Protect your downside first.",
        "tags": "#CharlieMunger #FinancialWisdom #Discipline #Mindset #InvestingInSelf"
    },
    # 11. CHISELED HERO + MUSASHI TIMING
    {
        "id": "IMG_MUSASHI_RHYTHM",
        "pillar": "LEGACY",
        "format_style": "CHISELED_HERO",
        "palette": "FORGE_AMBER",
        "category": "MASTERY & TIMING",
        "headline": "MASTER ONE THING DEEPLY",
        "quote": "\"From one thing, know ten thousand things. Do nothing that is of no use.\"",
        "author": "MIYAMOTO MUSASHI • FEUDAL JAPAN",
        "accent_word": "MASTER",
        "reflection_prompt": "WHAT ONE SKILL HAS PAID YOU BACK ACROSS EVERY STAGE OF LIFE?",
        "sub_prompt": "SHARE YOUR CRAFT IN THE COMMENTS",
        "bg_scene": "Atmospheric painting of a traditional Japanese wooden dojo at dawn with soft golden sunbeams through shoji screens",
        "caption_story": "Dabbling in ten directions produces shallow results. Going deep on one craft builds the discipline that transfers to everything else you touch.",
        "tags": "#MiyamotoMusashi #Mastery #Discipline #Legacy #PersonalGrowth"
    },
    # 12. SYMBOLIC PORTRAIT + CARL JUNG SHADOW
    {
        "id": "IMG_JUNG_UNCONSCIOUS",
        "pillar": "SOVEREIGNTY",
        "format_style": "SYMBOLIC_PORTRAIT",
        "palette": "ROYAL_VIOLET",
        "category": "SELF-AWARENESS",
        "headline": "Until you make the unconscious conscious, it will direct your life and you will call it fate.",
        "quote": "Examine your habits before blaming your circumstances.",
        "author": "CARL JUNG",
        "accent_word": "conscious",
        "reflection_prompt": "WHAT PATTERN DID YOU FINALLY NOTICE AND CHANGE IN YOURSELF?",
        "sub_prompt": "SHARE YOUR REFLECTION BELOW",
        "bg_scene": "Warm parchment classic studio portrait of a thoughtful European psychologist in tweed suit with glasses and calm analytical gaze",
        "caption_story": "Repeating the same relationship or financial mistakes is rarely bad luck. Honest self-observation breaks cycles that willpower alone cannot.",
        "tags": "#CarlJung #Psychology #SelfAwareness #Mindset #Growth"
    }
]

# ---------------------------------------------------------
# 4. PROCEDURAL & CURATED BACKGROUND ENGINE
# ---------------------------------------------------------
def create_atmospheric_canvas(width=1080, height=1350, seed_str="default", tone="GOLD"):
    rng = random.Random(seed_str)
    base = Image.new("RGB", (width, height), (14, 16, 22))
    draw = ImageDraw.Draw(base, "RGBA")

    palettes = {
        "GOLD": [(38, 30, 18), (68, 52, 28), (22, 24, 30)],
        "ICE":  [(16, 28, 38), (28, 48, 62), (14, 18, 26)],
        "AMBER":[(42, 24, 14), (78, 42, 20), (20, 18, 22)],
    }
    cols = palettes.get(tone, palettes["GOLD"])

    for y in range(height):
        ratio = y / float(height)
        r = int(cols[0][0] * (1 - ratio) + cols[2][0] * ratio)
        g = int(cols[0][1] * (1 - ratio) + cols[2][1] * ratio)
        b = int(cols[0][2] * (1 - ratio) + cols[2][2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    for _ in range(20):
        cx = rng.randint(-100, width + 100)
        cy = rng.randint(100, height - 100)
        rx = rng.randint(180, 480)
        ry = rng.randint(120, 360)
        c = cols[1]
        alpha = rng.randint(18, 42)
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(c[0], c[1], c[2], alpha))

    base = base.filter(ImageFilter.GaussianBlur(radius=45))
    arr = np.array(base, dtype=np.int16)
    np_rng = np.random.default_rng(abs(hash(seed_str)) % (2**32))
    grain = np_rng.integers(-9, 10, size=(height, width, 1))
    arr = np.clip(arr + grain, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)

def crop_and_prep_background(pil_img, bottom_crop_pct=0.06, darken_factor=0.52):
    im = pil_img.convert("RGB")
    w, h = im.size
    if bottom_crop_pct > 0:
        new_h = int(h * (1.0 - bottom_crop_pct))
        im = im.crop((0, 0, w, max(100, new_h)))
        w, h = im.size

    target_ratio = 1080.0 / 1350.0
    curr_ratio = w / float(h)
    if curr_ratio > target_ratio:
        crop_w = int(h * target_ratio)
        x0 = (w - crop_w) // 2
        im = im.crop((x0, 0, x0 + crop_w, h))
    else:
        crop_h = int(w / target_ratio)
        y0 = max(0, (h - crop_h) // 4)
        im = im.crop((0, y0, w, y0 + crop_h))

    im = im.resize((1080, 1350), Image.Resampling.LANCZOS)
    im = ImageEnhance.Brightness(im).enhance(darken_factor)
    im = ImageEnhance.Contrast(im).enhance(1.12)
    return im

# ---------------------------------------------------------
# 5. GEOMETRIC ORNAMENTS & 8-FORMAT 4:5 FEED COMPOSITOR
# ---------------------------------------------------------
def wrap_text_lines(draw, text, font, max_width):
    words = text.split()
    lines, curr = [], []
    for w in words:
        test = " ".join(curr + [w])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width or not curr:
            curr.append(w)
        else:
            lines.append(" ".join(curr))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    return lines

def draw_corner_brackets(draw, W, H, color_rgba, margin=44, arm=42, width=3):
    draw.line([(margin, margin), (margin + arm, margin)], fill=color_rgba, width=width)
    draw.line([(margin, margin), (margin, margin + arm)], fill=color_rgba, width=width)
    draw.line([(W - margin - arm, margin), (W - margin, margin)], fill=color_rgba, width=width)
    draw.line([(W - margin, margin), (W - margin, margin + arm)], fill=color_rgba, width=width)
    draw.line([(margin, H - margin), (margin + arm, H - margin)], fill=color_rgba, width=width)
    draw.line([(margin, H - margin - arm), (margin, H - margin)], fill=color_rgba, width=width)
    draw.line([(W - margin - arm, H - margin), (W - margin, H - margin)], fill=color_rgba, width=width)
    draw.line([(W - margin, H - margin - arm), (W - margin, H - margin)], fill=color_rgba, width=width)

def draw_diamond_divider(draw, cx, cy, color_rgba, span=170):
    draw.line([(cx - span, cy), (cx - 18, cy)], fill=color_rgba, width=2)
    draw.line([(cx + 18, cy), (cx + span, cy)], fill=color_rgba, width=2)
    draw.polygon([(cx, cy - 9), (cx + 9, cy), (cx, cy + 9), (cx - 9, cy)], fill=color_rgba)

def render_4x5_master_card(bg_image, card_data, accent_theme="IMPERIAL_GOLD"):
    W, H = 1080, 1350
    canvas = bg_image.copy().convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    for y in range(260):
        a = int(155 * (1 - y / 260.0))
        odraw.line([(0, y), (W, y)], fill=(6, 8, 12, a))
    for y in range(H - 360, H):
        a = int(215 * ((y - (H - 360)) / 360.0))
        odraw.line([(0, y), (W, y)], fill=(6, 8, 12, a))

    strip_top = H - 175
    odraw.rectangle([(0, strip_top), (W, H)], fill=(8, 11, 17, 235))

    pal = ACCENT_PALETTES.get(accent_theme, ACCENT_PALETTES["IMPERIAL_GOLD"])
    gold = pal["primary"]
    white = (248, 250, 252, 255)
    soft_gray = (203, 213, 225, 255)

    odraw.line([(0, strip_top), (W, strip_top)], fill=(gold[0], gold[1], gold[2], 150), width=2)
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    draw_corner_brackets(draw, W, strip_top, (gold[0], gold[1], gold[2], 165), margin=38, arm=46, width=3)

    f_brand = load_font(REG_FONT_PATH, 20)
    f_cat = load_font(BOLD_FONT_PATH, 22)
    f_head = load_font(BOLD_FONT_PATH, 66)
    f_quote = load_font(SERIF_FONT_PATH, 33)
    f_auth = load_font(BOLD_FONT_PATH, 21)
    f_ref_q = load_font(REG_FONT_PATH, 20)
    f_ref_sub = load_font(BOLD_FONT_PATH, 22)

    brand_txt = "E C H O E S   O F   W I S D O M"
    bw = draw.textbbox((0, 0), brand_txt, font=f_brand)[2]
    draw.text(((W - bw) // 2, 68), brand_txt, font=f_brand, fill=gold)
    draw.line([((W - bw) // 2, 102), ((W + bw) // 2, 102)], fill=(gold[0], gold[1], gold[2], 130), width=1)

    cat_txt = card_data.get("category", "SOVEREIGNTY").upper()
    cw = draw.textbbox((0, 0), cat_txt, font=f_cat)[2]
    cx = (W - cw) // 2
    cy = 180
    draw.rounded_rectangle([(cx - 24, cy - 8), (cx + cw + 24, cy + 36)], radius=16, outline=gold, width=2)
    draw.text((cx, cy), cat_txt, font=f_cat, fill=gold)

    head_lines = wrap_text_lines(draw, card_data.get("headline", "").upper(), f_head, 860)
    curr_y = 285 if len(head_lines) >= 3 else 325
    for line in head_lines[:4]:
        lw = draw.textbbox((0, 0), line, font=f_head)[2]
        lx = (W - lw) // 2
        draw.text((lx + 4, curr_y + 5), line, font=f_head, fill=(0, 0, 0, 210))
        draw.text((lx - 1, curr_y - 1), line, font=f_head, fill=(255, 255, 255, 90))
        draw.text((lx, curr_y), line, font=f_head, fill=white)
        curr_y += 82

    curr_y += 18
    draw_diamond_divider(draw, W // 2, curr_y, gold, span=160)
    curr_y += 36

    quote_lines = wrap_text_lines(draw, card_data.get("quote", ""), f_quote, 850)
    for qline in quote_lines[:5]:
        qw = draw.textbbox((0, 0), qline, font=f_quote)[2]
        qx = (W - qw) // 2
        draw.text((qx + 2, curr_y + 3), qline, font=f_quote, fill=(0, 0, 0, 210))
        draw.text((qx, curr_y), qline, font=f_quote, fill=white)
        curr_y += 46

    curr_y += 24
    auth_txt = card_data.get("author", "ANCIENT MAXIM").upper()
    aw = draw.textbbox((0, 0), auth_txt, font=f_auth)[2]
    ax = (W - aw) // 2
    draw.text((ax, curr_y), auth_txt, font=f_auth, fill=gold)
    draw.line([(ax - 44, curr_y + 13), (ax - 14, curr_y + 13)], fill=gold, width=2)
    draw.line([(ax + aw + 14, curr_y + 13), (ax + aw + 44, curr_y + 13)], fill=gold, width=2)

    rq_txt = card_data.get("reflection_prompt", "WHAT IS ONE LESSON LIFE TAUGHT YOU THE HARD WAY?").upper()
    rq_lines = wrap_text_lines(draw, rq_txt, f_ref_q, 980)
    ry = strip_top + 28
    for rl in rq_lines[:2]:
        rw = draw.textbbox((0, 0), rl, font=f_ref_q)[2]
        draw.text(((W - rw) // 2, ry), rl, font=f_ref_q, fill=soft_gray)
        ry += 28

    sub_txt = card_data.get("sub_prompt", "SHARE YOUR PERSPECTIVE IN THE COMMENTS").upper()
    sw = draw.textbbox((0, 0), sub_txt, font=f_ref_sub)[2]
    draw.text(((W - sw) // 2, ry + 14), sub_txt, font=f_ref_sub, fill=gold)

    return canvas.convert("RGB")

def render_feed_card_by_format(bg_image, card_data, accent_theme="IMPERIAL_GOLD", format_style="CHISELED_HERO"):
    if format_style == "CHISELED_HERO":
        return render_4x5_master_card(bg_image, card_data, accent_theme=accent_theme)

    W, H = 1080, 1350
    pal = ACCENT_PALETTES.get(accent_theme, ACCENT_PALETTES["IMPERIAL_GOLD"])
    accent_rgba = pal["primary"]
    hl_rgba = pal["secondary"]

    if format_style == "MINIMAL_TYPO":
        canvas = Image.new("RGBA", (W, H), (8, 10, 15, 255))
        draw = ImageDraw.Draw(canvas)
        draw_corner_brackets(draw, W, H, accent_rgba, margin=54, arm=52, width=3)
        f_lead = load_font(SERIF_FONT_PATH, 42)
        f_body = load_font(SERIF_FONT_PATH, 46)
        f_auth = load_font(BOLD_FONT_PATH, 24)
        f_foot = load_font(REG_FONT_PATH, 22)

        draw.rectangle([(96, 195), (104, 260)], fill=accent_rgba)
        lead_txt = card_data.get("headline", "Hard truth about money:")
        lead_lines = wrap_text_lines(draw, lead_txt, f_lead, 840)
        y = 195
        for line in lead_lines[:2]:
            draw.text((124, y), line, font=f_lead, fill=accent_rgba)
            y += 56

        y += 34
        body_txt = card_data.get("quote", "").strip('"')
        body_lines = wrap_text_lines(draw, body_txt, f_body, 860)
        custom_acc = re.sub(r"[^a-zA-Z]", "", card_data.get("accent_word", "")).lower()
        highlight_words = {"pays", "funds", "protects", "truth", "strength", "peace", "freedom", "clarity", "character", "avoiding", "value", custom_acc}
        for line in body_lines[:8]:
            x = 100
            for w in line.split():
                clean_w = re.sub(r"[^a-zA-Z]", "", w).lower()
                col = accent_rgba if (clean_w and clean_w in highlight_words) else (248, 250, 252, 255)
                draw.text((x, y), w, font=f_body, fill=col)
                x = draw.textbbox((x, y), w + " ", font=f_body)[2]
            y += 64

        y += 28
        draw.line([(100, y), (340, y)], fill=accent_rgba, width=3)
        draw.text((100, y + 20), f"— {card_data.get('author', 'ECHOES OF WISDOM').upper()}", font=f_auth, fill=accent_rgba)

        handle_txt = get_persistent_handle()
        hw = draw.textbbox((0, 0), handle_txt, font=f_foot)[2]
        draw.text(((W - hw) // 2, H - 105), handle_txt, font=f_foot, fill=(148, 163, 184, 255))
        return canvas.convert("RGB")

    if format_style == "HIGHLIGHT_STORY":
        canvas = Image.new("RGBA", (W, H), (244, 241, 234, 255))
        draw = ImageDraw.Draw(canvas)
        f_top = load_font(BOLD_FONT_PATH, 36)
        f_q = load_font(SERIF_FONT_PATH, 42)
        f_auth = load_font(BOLD_FONT_PATH, 22)
        f_handle = load_font(BOLD_FONT_PATH, 22)

        top_head = card_data.get("headline", "I love this saying:")
        th_box = draw.textbbox((0, 0), top_head, font=f_top)
        hx = (W - (th_box[2] - th_box[0])) // 2
        hy = 68
        draw.rounded_rectangle([(hx - 18, hy - 6), (hx + (th_box[2] - th_box[0]) + 18, hy + (th_box[3] - th_box[1]) + 10)], radius=10, fill=hl_rgba)
        draw.text((hx, hy), top_head, font=f_top, fill=(20, 24, 32, 255))

        q_txt = card_data.get("quote", "")
        q_lines = wrap_text_lines(draw, q_txt, f_q, 900)
        qy = 148
        for ql in q_lines[:6]:
            qw = draw.textbbox((0, 0), ql, font=f_q)[2]
            draw.text(((W - qw) // 2, qy), ql, font=f_q, fill=(17, 24, 39, 255))
            qy += 54

        auth_str = f"— {card_data.get('author', 'TIMELESS REFLECTION').upper()}"
        aw = draw.textbbox((0, 0), auth_str, font=f_auth)[2]
        draw.text(((W - aw) // 2, qy + 8), auth_str, font=f_auth, fill=(100, 116, 139, 255))

        art_top = max(550, qy + 52)
        art_im = bg_image.convert("RGB").resize((W, H - art_top), Image.Resampling.LANCZOS)
        canvas.paste(art_im, (0, art_top))
        draw.line([(0, art_top), (W, art_top)], fill=accent_rgba, width=5)

        handle_txt = get_persistent_handle()
        hw = draw.textbbox((0, 0), handle_txt, font=f_handle)[2]
        draw.rounded_rectangle([((W - hw) // 2 - 20, H - 68), ((W + hw) // 2 + 20, H - 24)], radius=14, fill=(10, 14, 22, 215))
        draw.text(((W - hw) // 2, H - 58), handle_txt, font=f_handle, fill=(248, 250, 252, 255))
        return canvas.convert("RGB")

    if format_style == "SYMBOLIC_PORTRAIT":
        canvas = Image.new("RGBA", (W, H), (242, 232, 214, 255))
        draw = ImageDraw.Draw(canvas)
        draw_corner_brackets(draw, W, H, (145, 32, 26, 180), margin=34, arm=42, width=3)
        f_main = load_font(SERIF_FONT_PATH, 50)
        f_sub = load_font(ITALIC_FONT_PATH, 32)
        f_auth = load_font(BOLD_FONT_PATH, 25)

        crimson_ink = (145, 32, 26, 255)
        charcoal_ink = (34, 34, 38, 255)

        m_lines = wrap_text_lines(draw, card_data.get("headline", ""), f_main, 900)
        y = 74
        for ml in m_lines[:4]:
            mw = draw.textbbox((0, 0), ml, font=f_main)[2]
            draw.text(((W - mw) // 2, y), ml, font=f_main, fill=crimson_ink)
            y += 62

        s_lines = wrap_text_lines(draw, card_data.get("quote", "").strip('"'), f_sub, 860)
        y += 12
        for sl in s_lines[:3]:
            sw = draw.textbbox((0, 0), sl, font=f_sub)[2]
            draw.text(((W - sw) // 2, y), sl, font=f_sub, fill=charcoal_ink)
            y += 42

        y += 12
        draw_diamond_divider(draw, W // 2, y, crimson_ink, span=140)
        auth_txt = f"— {card_data.get('author', 'ANCIENT MAXIM').upper()}"
        aw = draw.textbbox((0, 0), auth_txt, font=f_auth)[2]
        draw.text(((W - aw) // 2, y + 18), auth_txt, font=f_auth, fill=charcoal_ink)

        art_y = max(570, y + 66)
        art_im = bg_image.convert("RGB").resize((W, H - art_y), Image.Resampling.LANCZOS)
        canvas.paste(art_im, (0, art_y))
        return canvas.convert("RGB")

    if format_style == "SYMBOL_SANDWICH":
        canvas = Image.new("RGBA", (W, H), (14, 15, 18, 255))
        draw = ImageDraw.Draw(canvas)
        f_mono = load_font(MONO_FONT_PATH, 40)
        f_sub = load_font(SERIF_FONT_PATH, 31)
        f_auth = load_font(BOLD_FONT_PATH, 22)
        silver = (215, 222, 230, 255)

        draw.polygon([(W // 2, 85), (W // 2 - 95, 235), (W // 2 + 95, 235)], outline=accent_rgba, width=5)
        draw.polygon([(W // 2, 265), (W // 2 - 95, 115), (W // 2 + 95, 115)], outline=silver, width=4)
        draw.ellipse([(W // 2 - 22, 153), (W // 2 + 22, 197)], outline=accent_rgba, width=4)

        lines = wrap_text_lines(draw, card_data.get("headline", "").upper(), f_mono, 880)
        y = 335
        for ln in lines[:5]:
            lw = draw.textbbox((0, 0), ln, font=f_mono)[2]
            draw.text(((W - lw) // 2, y), ln, font=f_mono, fill=silver)
            y += 56

        q_lines = wrap_text_lines(draw, card_data.get("quote", "").strip('"'), f_sub, 860)
        y += 28
        for ql in q_lines[:3]:
            qw = draw.textbbox((0, 0), ql, font=f_sub)[2]
            draw.text(((W - qw) // 2, y), ql, font=f_sub, fill=accent_rgba)
            y += 44

        auth_str = f"— {card_data.get('author', 'TIMELESS LAW').upper()}"
        aw = draw.textbbox((0, 0), auth_str, font=f_auth)[2]
        draw.text(((W - aw) // 2, y + 22), auth_str, font=f_auth, fill=silver)

        draw.arc([(W // 2 - 110, H - 215), (W // 2 + 110, H - 75)], start=180, end=360, fill=accent_rgba, width=5)
        draw.line([(W // 2 - 150, H - 120), (W // 2 + 150, H - 120)], fill=silver, width=4)
        draw.polygon([(W // 2, H - 145), (W // 2 + 12, H - 120), (W // 2, H - 95), (W // 2 - 12, H - 120)], fill=accent_rgba)
        return canvas.convert("RGB")

    if format_style == "NUMBERED_CHECKLIST":
        canvas = bg_image.copy().convert("RGBA")
        overlay = Image.new("RGBA", (W, H), (8, 11, 17, 215))
        canvas = Image.alpha_composite(canvas, overlay)
        draw = ImageDraw.Draw(canvas)
        draw_corner_brackets(draw, W, H, accent_rgba, margin=42, arm=44, width=3)

        f_head = load_font(BOLD_FONT_PATH, 46)
        f_num = load_font(BOLD_FONT_PATH, 26)
        f_item = load_font(REG_FONT_PATH, 29)
        f_foot = load_font(BOLD_FONT_PATH, 22)

        h_lines = wrap_text_lines(draw, card_data.get("headline", "5 RULES TO LIVE BY:").upper(), f_head, 900)
        y = 105
        for hl in h_lines[:2]:
            draw.text((88, y), hl, font=f_head, fill=accent_rgba)
            y += 58

        draw.line([(88, y + 12), (992, y + 12)], fill=accent_rgba, width=3)
        y += 46

        raw_q = card_data.get("quote", "").strip('"')
        parts = [p.strip() for p in re.split(r'\|\s*|\n+', raw_q) if p.strip()]
        if len(parts) < 2:
            parts = [s.strip() for s in re.split(r'(?=\b[1-5]\.)', raw_q) if s.strip()]

        for idx, item_txt in enumerate(parts[:5], 1):
            clean_item = re.sub(r'^[1-5][\.\)]\s*', '', item_txt)
            draw.ellipse([(88, y), (138, y + 50)], fill=accent_rgba)
            nw = draw.textbbox((0, 0), str(idx), font=f_num)[2]
            draw.text((88 + (50 - nw) // 2, y + 10), str(idx), font=f_num, fill=(10, 12, 18, 255))

            wrapped = wrap_text_lines(draw, clean_item, f_item, 810)
            iy = y + 6
            for wl in wrapped[:3]:
                draw.text((160, iy), wl, font=f_item, fill=(248, 250, 252, 255))
                iy += 40
            y = max(y + 82, iy + 28)

        draw.line([(88, H - 155), (992, H - 155)], fill=(accent_rgba[0], accent_rgba[1], accent_rgba[2], 140), width=2)
        rq = card_data.get("reflection_prompt", "WHICH RULE MATTERS MOST TO YOU?").upper()
        rw = draw.textbbox((0, 0), rq, font=f_foot)[2]
        draw.text(((W - rw) // 2, H - 122), rq, font=f_foot, fill=accent_rgba)
        h_str = get_persistent_handle()
        hw = draw.textbbox((0, 0), h_str, font=f_foot)[2]
        draw.text(((W - hw) // 2, H - 78), h_str, font=f_foot, fill=(148, 163, 184, 255))
        return canvas.convert("RGB")

    if format_style == "MODERN_CONTRAST":
        canvas = bg_image.copy().convert("RGBA")
        overlay = Image.new("RGBA", (W, H), (10, 12, 18, 200))
        canvas = Image.alpha_composite(canvas, overlay)
        draw = ImageDraw.Draw(canvas)

        f_title = load_font(BOLD_FONT_PATH, 52)
        f_box_h = load_font(BOLD_FONT_PATH, 26)
        f_box_b = load_font(SERIF_FONT_PATH, 34)
        f_auth = load_font(BOLD_FONT_PATH, 23)

        t_txt = card_data.get("headline", "WEAKNESS VS. STRENGTH").upper()
        tw = draw.textbbox((0, 0), t_txt, font=f_title)[2]
        draw.text(((W - tw) // 2, 110), t_txt, font=f_title, fill=(255, 255, 255, 255))
        draw_diamond_divider(draw, W // 2, 190, accent_rgba, span=190)

        raw_q = card_data.get("quote", "").strip('"')
        sides = [s.strip() for s in raw_q.split("|") if s.strip()]
        left_txt = sides[0] if len(sides) >= 1 else "THE TRAP: Reacting emotionally to every noise and insult."
        right_txt = sides[1] if len(sides) >= 2 else "THE EDGE: Holding calm silence and letting actions speak."

        draw.rounded_rectangle([(85, 255), (W - 85, 625)], radius=20, fill=(28, 18, 22, 225), outline=(239, 68, 68, 190), width=3)
        draw.text((125, 290), "WHAT DRAINS YOUR STRENGTH", font=f_box_h, fill=(248, 113, 113, 255))
        ly = 345
        for ln in wrap_text_lines(draw, left_txt, f_box_b, 820)[:4]:
            draw.text((125, ly), ln, font=f_box_b, fill=(241, 245, 249, 255))
            ly += 48

        draw.rounded_rectangle([(85, 685), (W - 85, 1065)], radius=20, fill=(14, 28, 26, 230), outline=accent_rgba, width=3)
        draw.text((125, 720), "WHAT BUILDS LASTING POWER", font=f_box_h, fill=accent_rgba)
        ry = 775
        for ln in wrap_text_lines(draw, right_txt, f_box_b, 820)[:4]:
            draw.text((125, ry), ln, font=f_box_b, fill=(255, 255, 255, 255))
            ry += 48

        auth_str = f"— {card_data.get('author', 'ECHOES OF WISDOM').upper()}"
        aw = draw.textbbox((0, 0), auth_str, font=f_auth)[2]
        draw.text(((W - aw) // 2, 1135), auth_str, font=f_auth, fill=accent_rgba)

        h_str = get_persistent_handle()
        hw = draw.textbbox((0, 0), h_str, font=f_auth)[2]
        draw.text(((W - hw) // 2, 1215), h_str, font=f_auth, fill=(148, 163, 184, 255))
        return canvas.convert("RGB")

    # BATTLEFIELD_VOW
    canvas = bg_image.copy().convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 105))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    f_vow = load_font(BOLD_FONT_PATH, 54)
    f_sub = load_font(SERIF_FONT_PATH, 32)
    f_auth = load_font(BOLD_FONT_PATH, 22)
    accent_word = card_data.get("accent_word", "").strip().lower()
    crimson_hi = (239, 68, 68, 255)

    draw.line([(W // 2 - 120, 495), (W // 2 + 120, 495)], fill=accent_rgba, width=3)
    lines = wrap_text_lines(draw, card_data.get("headline", "Dear self, I will win. I promise."), f_vow, 900)
    y = 530
    for ln in lines[:4]:
        lw = draw.textbbox((0, 0), ln, font=f_vow)[2]
        x = (W - lw) // 2
        draw.text((x + 3, y + 4), ln, font=f_vow, fill=(0, 0, 0, 220))
        cur_x = x
        for word in ln.split():
            w_clean = re.sub(r"[^a-zA-Z]", "", word).lower()
            w_col = crimson_hi if (accent_word and w_clean == accent_word) else (255, 255, 255, 255)
            draw.text((cur_x, y), word, font=f_vow, fill=w_col)
            cur_x = draw.textbbox((cur_x, y), word + " ", font=f_vow)[2]
        y += 68

    q_lines = wrap_text_lines(draw, card_data.get("quote", "").strip('"'), f_sub, 880)
    y += 20
    for ql in q_lines[:2]:
        qw = draw.textbbox((0, 0), ql, font=f_sub)[2]
        qx = (W - qw) // 2
        draw.text((qx + 2, y + 2), ql, font=f_sub, fill=(0, 0, 0, 210))
        draw.text((qx, y), ql, font=f_sub, fill=accent_rgba)
        y += 42

    auth_str = f"— {card_data.get('author', 'ECHOES OF WISDOM').upper()}"
    aw = draw.textbbox((0, 0), auth_str, font=f_auth)[2]
    draw.text(((W - aw) // 2, y + 22), auth_str, font=f_auth, fill=(226, 232, 240, 255))

    return canvas.convert("RGB")

# ---------------------------------------------------------
# 6. AI SYNTHESIS ENGINE (NON-BAIT, LEADERS, MODERN & ANCIENT)
# ---------------------------------------------------------
def synthesize_ai_card(raw_key, pillar_choice="ALL", format_choice="AUTO", palette_choice="AUTO"):
    clean_k = raw_key.strip().strip('"').strip("'")
    used_heads = db.get("used_headlines", [])[-35:]
    available_cards = [
        c for c in CONTENT_CARDS_VAULT
        if (pillar_choice == "ALL" or c["pillar"] == pillar_choice) and c["headline"] not in used_heads
    ]
    if not available_cards:
        available_cards = [c for c in CONTENT_CARDS_VAULT if (pillar_choice == "ALL" or c["pillar"] == pillar_choice)] or CONTENT_CARDS_VAULT

    base_card = dict(random.choice(available_cards))
    if format_choice != "AUTO":
        base_card["format_style"] = format_choice
    if palette_choice != "AUTO":
        base_card["palette"] = palette_choice

    leader_pick = random.choice(LEADER_WISDOM_POOL)

    if not clean_k:
        return base_card, f"Curated Vault ({base_card.get('format_style')})"

    pillar_label = PILLAR_DEFINITIONS.get(base_card["pillar"], "Silent Power")
    fmt_key = base_card.get("format_style", "CHISELED_HERO")
    fmt_label = FORMAT_STYLES.get(fmt_key, FORMAT_STYLES["CHISELED_HERO"])["label"]
    prompt = (
        f"You are Creative Director for 'Echoes of Wisdom', a high-authority Facebook & Instagram page whose core audience is men aged 35-65+ in the US, UK, Canada, and Australia.\n"
        f"TARGET PILLAR: {pillar_label}\n"
        f"CARD FORMAT: {fmt_label} ({fmt_key})\n"
        f"LEADER / THINKER INSPIRATION: {leader_pick['leader']} ({leader_pick['era']}) — {leader_pick['quote']}\n"
        f"FORBIDDEN HEADLINES (DO NOT REPEAT): {', '.join(used_heads) if used_heads else 'None'}\n"
        f"STRICT RULES:\n"
        f"1. Create a fresh, thought-provoking 4:5 Feed Card inspired by {leader_pick['leader']} or a sharp modern vs. ancient contrast.\n"
        f"2. HEADLINE: Crisp, memorable statement or hook (max 65 characters). Avoid tired clichés.\n"
        f"3. QUOTE: 14 to 28 words. If format is NUMBERED_CHECKLIST, write 5 concise numbered points separated by ' | ' (e.g. '1. ... | 2. ... | 3. ... | 4. ... | 5. ...'). If format is MODERN_CONTRAST, write two contrasting sides separated by ' | '.\n"
        f"4. REFLECTION_PROMPT: An authentic, open-ended question (max 70 characters) inviting a real comment. STRICTLY NEVER use engagement bait like 'Drop 1 or 2', 'Comment YES', or numeric polls.\n"
        f"5. CAPTION_STORY: A 3-sentence compelling micro-story or hard truth in crisp international English.\n"
        f"6. BG_SCENE: A vivid scene description—alternate between modern everyday realism (sunlit city apartment, coffee desk, rainy dusk street) and ancient/classic scenes (no text in image).\n"
        f"OUTPUT STRICT JSON ONLY:\n"
        "{\n"
        f'  "pillar": "{base_card["pillar"]}",\n'
        f'  "format_style": "{fmt_key}",\n'
        '  "category": "1-2 WORD UPPERCASE CATEGORY",\n'
        '  "headline": "Fresh headline or statement",\n'
        '  "quote": "Your 14-28 word quote, checklist, or contrast.",\n'
        '  "accent_word": "single_key_word",\n'
        f'  "author": "{leader_pick["leader"]}",\n'
        '  "reflection_prompt": "OPEN-ENDED QUESTION IN UPPERCASE",\n'
        '  "sub_prompt": "SHARE YOUR PERSPECTIVE IN THE COMMENTS",\n'
        '  "bg_scene": "Visual scene description...",\n'
        '  "caption_story": "Three compelling sentences expanding the lesson for mature readers.",\n'
        '  "tags": "#Mindset #LifeLessons #PersonalGrowth #Discipline #Wisdom"\n'
        "}"
    )

    try:
        client = get_fast_gemini_client(clean_k)
        for m in ["gemini-3.8-flash", "gemini-3.8-flash-lite"]:
            try:
                cfg = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.92, max_output_tokens=950)
                res = client.models.generate_content(model=m, contents=prompt, config=cfg)
                raw = res.text.strip()
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                parsed = json.loads(match.group(0) if match else raw)
                if isinstance(parsed, dict) and "headline" in parsed and "quote" in parsed:
                    parsed["id"] = f"AI_{datetime.now().strftime('%H%M%S')}"
                    parsed["palette"] = base_card.get("palette", "IMPERIAL_GOLD")
                    if format_choice != "AUTO":
                        parsed["format_style"] = format_choice
                    return parsed, f"Gemini AI • {leader_pick['leader']}"
            except Exception:
                continue
    except Exception:
        pass

    return base_card, f"Curated Vault ({base_card.get('author','Wisdom')})"

def append_image_excel_tracker(entry):
    if not OPENPYXL_AVAILABLE:
        return False
    headers = [
        "Post ID", "Target Date", "Time (IST)", "Pillar", "Format Style", "Category",
        "Headline", "Author", "File Name", "Feed Caption", "First Comment"
    ]
    if os.path.exists(EXCEL_IMAGE_TRACKER):
        try:
            wb = openpyxl.load_workbook(EXCEL_IMAGE_TRACKER)
            ws = wb.active
        except Exception:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(headers)
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Image Feed Tracker"
        ws.append(headers)

    next_id = f"IMG-{ws.max_row:03d}"
    ws.append([
        next_id,
        entry.get("date", ""),
        entry.get("time", "17:30"),
        entry.get("pillar", ""),
        entry.get("format_style", ""),
        entry.get("category", ""),
        entry.get("headline", ""),
        entry.get("author", ""),
        entry.get("file", ""),
        entry.get("caption", ""),
        entry.get("first_comment", "")
    ])
    wb.save(EXCEL_IMAGE_TRACKER)
    return True

def render_copy_btn(bid, label, text):
    b64_val = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    components.html(f"""
    <div style="margin:0;padding:0;">
        <button id="b_{bid}" onclick="cp_{bid}()" style="width:100%;height:2.6rem;background:rgba(56,189,248,0.12);color:#38BDF8;border:1px solid rgba(56,189,248,0.35);border-radius:8px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-weight:700;font-size:12px;cursor:pointer;">
            📋 {label}
        </button>
    </div>
    <script>
    function cp_{bid}() {{
        const txt = decodeURIComponent(escape(window.atob('{b64_val}')));
        navigator.clipboard.writeText(txt).then(() => {{
            const el = document.getElementById('b_{bid}');
            el.innerText = '✓ COPIED!';
            el.style.background = '#059669';
            el.style.color = '#FFF';
            setTimeout(() => {{
                el.innerText = '📋 {label}';
                el.style.background = 'rgba(56,189,248,0.12)';
                el.style.color = '#38BDF8';
            }}, 1800);
        }});
    }}
    </script>
    """, height=48)

# Restore active card from disk on reload
if "active_card" not in st.session_state and os.path.exists(ACTIVE_CARD_PATH):
    try:
        with open(ACTIVE_CARD_PATH, "r", encoding="utf-8") as af:
            saved_ac = json.load(af)
            if isinstance(saved_ac, dict) and "card" in saved_ac:
                st.session_state["active_card"] = saved_ac["card"]
                st.session_state["active_card_src"] = saved_ac.get("src", "Saved Card")
    except Exception:
        pass

# ---------------------------------------------------------
# 7. STUDIO HEADER & CREDENTIALS
# ---------------------------------------------------------
next_d = get_next_post_date()
st.markdown("""
<div style="font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: #F8FAFC; margin-bottom: 8px;">
    🏛️ ECHOES IMAGE STUDIO <span style="font-size: 13px; color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-weight: 600;">v3.8 // 8 FORMATS, 18+ LEADERS, ORNATE SHAPES & MODERN/ANCIENT ENGINE</span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="margin-bottom: 14px;">
    <span class="badge badge-green">● 8 FORMATS (1080×1350)</span>
    <span class="badge badge-purple">🏛️ 18+ LEADERS & THINKERS</span>
    <span class="badge badge-blue">✨ EMOJIS, SHAPES & HASHTAGS</span>
    <span class="badge badge-amber">📅 NEXT SLOT: {next_d} @ {db.get('post_time', '17:30')} IST</span>
</div>
""", unsafe_allow_html=True)

if "img_banner" in st.session_state:
    st.success(st.session_state.pop("img_banner"))

curr_key = get_persistent_api_key()
with st.expander("🔑 API CREDENTIALS, HANDLE & GUIDE LINK", expanded=(not bool(curr_key))):
    uk = st.text_input("Gemini API Key", value=curr_key, type="password", placeholder="AIzaSy...", key="img_key_input")
    if uk:
        save_persistent_api_key(uk)
        st.caption("✓ Gemini API Key saved")

    c_h1, c_h2 = st.columns(2)
    with c_h1:
        uh = st.text_input("Facebook & Instagram Handle", value=get_persistent_handle())
        if uh != get_persistent_handle():
            save_persistent_handle(uh)
    with c_h2:
        ug = st.text_input("Clean Guide URL (First Comment)", value=get_persistent_guide_url())
        if ug != get_persistent_guide_url():
            save_persistent_guide_url(ug)

vault_hist = load_card_vault_history()
if vault_hist:
    with st.expander(f"📦 RESTORE PREVIOUS CARD ({len(vault_hist)} SAVED IN VAULT)", expanded=False):
        v_labels = [f"🖼️ {v.get('headline','Card')} — {v.get('author','')} ({v.get('format_style','CHISELED_HERO')})" for v in vault_hist]
        v_idx = st.selectbox("Select Saved Card", range(len(vault_hist)), format_func=lambda i: v_labels[i], key="img_vault_sel")
        if st.button("🔄 Restore Selected Card", key="img_vault_btn"):
            st.session_state["active_card"] = vault_hist[v_idx]
            st.session_state["active_card_src"] = "Saved Vault"
            save_active_card_to_disk(vault_hist[v_idx], "Saved Vault")
            st.rerun()

# ---------------------------------------------------------
# 8. CARD SYNTHESIS CONTROLS & DISCARD / REGENERATE
# ---------------------------------------------------------
st.markdown("### ⚡ 1. Synthesize 4:5 Feed Card")
col_p1, col_p2, col_p3 = st.columns([1.2, 1.2, 0.9])
with col_p1:
    chosen_pillar = st.selectbox(
        "Audience Pillar (35-65+)",
        list(PILLAR_DEFINITIONS.keys()),
        format_func=lambda k: PILLAR_DEFINITIONS[k]
    )
with col_p2:
    chosen_fmt = st.selectbox(
        "Card Format Style",
        ["AUTO"] + list(FORMAT_STYLES.keys()),
        format_func=lambda k: "🎲 Auto Format" if k == "AUTO" else FORMAT_STYLES[k]["label"].split(" (")[0]
    )
with col_p3:
    accent_choice = st.selectbox(
        "Color Palette",
        ["AUTO"] + list(ACCENT_PALETTES.keys()),
        format_func=lambda k: "🎲 Auto Color" if k == "AUTO" else ACCENT_PALETTES[k]["label"]
    )

col_btn1, col_btn2 = st.columns([2, 1])
with col_btn1:
    if st.button("🚀 Synthesize Fresh 4:5 Card", type="primary", use_container_width=True):
        with st.spinner("⚡ Synthesizing fresh leader insight & visual layout..."):
            card, src = synthesize_ai_card(get_persistent_api_key(), chosen_pillar, chosen_fmt, accent_choice)
            st.session_state["active_card"] = card
            st.session_state["active_card_src"] = src
            save_to_card_vault_history(card)
            save_active_card_to_disk(card, src)
            st.rerun()
with col_btn2:
    if st.button("🔄 Discard & New Card", use_container_width=True):
        with st.spinner("⚡ Generating a completely different format & leader..."):
            card, src = synthesize_ai_card(get_persistent_api_key(), "ALL", "AUTO", "AUTO")
            st.session_state["active_card"] = card
            st.session_state["active_card_src"] = src
            save_to_card_vault_history(card)
            save_active_card_to_disk(card, src)
            st.rerun()

if "active_card" not in st.session_state:
    st.session_state["active_card"] = CONTENT_CARDS_VAULT[0]
    st.session_state["active_card_src"] = "Curated Vault"

card = st.session_state["active_card"]
resolved_fmt = card.get("format_style", "CHISELED_HERO") if chosen_fmt == "AUTO" else chosen_fmt
resolved_palette = card.get("palette", "IMPERIAL_GOLD") if accent_choice == "AUTO" else accent_choice
st.caption(f"Source: `{st.session_state.get('active_card_src', 'Vault')}` | Format: `{FORMAT_STYLES.get(resolved_fmt, FORMAT_STYLES['CHISELED_HERO'])['label']}`")

# ---------------------------------------------------------
# 9. BACKGROUND ARTWORK & LIVE EDITOR
# ---------------------------------------------------------
st.markdown("### 🎨 2. Background Artwork & Watermark Crop")
st.text_area("AI Image Prompt (Copy for Google Flow / Imagen if generating custom art)", card.get("bg_scene", ""), height=68)
render_copy_btn("bg_pr", "COPY ARTWORK PROMPT", card.get("bg_scene", ""))

col_bg1, col_bg2, col_bg3 = st.columns([2, 1, 1])
with col_bg1:
    uploaded_bg = st.file_uploader("Upload Custom Artwork (Auto-saved on disk)", type=["jpg", "jpeg", "png", "webp"])
    if uploaded_bg:
        with open(SAVED_BG_PATH, "wb") as bf:
            bf.write(uploaded_bg.read())
with col_bg2:
    wm_crop_pct = st.slider("Bottom Watermark Crop %", min_value=0.0, max_value=15.0, value=6.5, step=0.5)
with col_bg3:
    bg_darkness = st.slider("Backdrop Brightness", min_value=0.25, max_value=0.85, value=0.52, step=0.03)

if os.path.exists(SAVED_BG_PATH):
    col_clr_bg1, col_clr_bg2 = st.columns([3, 1])
    with col_clr_bg1:
        st.caption("✓ Custom background artwork active in vault")
    with col_clr_bg2:
        if st.button("🗑️ Clear Custom BG"):
            try: os.remove(SAVED_BG_PATH)
            except Exception: pass
            st.rerun()

st.markdown("### ✍️ 3. Fine-Tune Card Typography & Shapes")
col_t1, col_t2 = st.columns([1, 2])
with col_t1:
    ed_cat = st.text_input("Category Pill", value=card.get("category", "SOVEREIGNTY"))
    ed_auth = st.text_input("Leader / Attribution", value=card.get("author", "MARCUS AURELIUS"))
with col_t2:
    ed_head = st.text_input("Main Headline / Statement", value=card.get("headline", ""))
    ed_quote = st.text_area("Parable / Quote / Checklist Body", value=card.get("quote", ""), height=90)

col_r1, col_r2, col_r3 = st.columns([2, 1, 1])
with col_r1:
    ed_ref_q = st.text_input("Bottom Reflection Question (Non-Bait)", value=card.get("reflection_prompt", ""))
with col_r2:
    ed_accent_w = st.text_input("Accent Highlight Word", value=card.get("accent_word", "win."))
with col_r3:
    ed_ref_sub = st.text_input("Bottom Action Line", value=card.get("sub_prompt", "SHARE YOUR PERSPECTIVE IN THE COMMENTS"))

edited_card = {
    **card,
    "category": ed_cat,
    "headline": ed_head,
    "quote": ed_quote,
    "accent_word": ed_accent_w,
    "author": ed_auth,
    "reflection_prompt": ed_ref_q,
    "sub_prompt": ed_ref_sub,
}

if os.path.exists(SAVED_BG_PATH):
    raw_bg = Image.open(SAVED_BG_PATH)
    prepped_bg = crop_and_prep_background(raw_bg, bottom_crop_pct=wm_crop_pct / 100.0, darken_factor=bg_darkness)
else:
    tone_key = ACCENT_PALETTES.get(resolved_palette, ACCENT_PALETTES["IMPERIAL_GOLD"])["bg_tone"]
    proc_bg = create_atmospheric_canvas(1080, 1350, seed_str=ed_head, tone=tone_key)
    prepped_bg = ImageEnhance.Brightness(proc_bg).enhance(bg_darkness / 0.52)

final_img = render_feed_card_by_format(prepped_bg, edited_card, accent_theme=resolved_palette, format_style=resolved_fmt)

st.markdown("### 🖼️ 4. Master 4:5 Preview & Export")
st.image(final_img, caption=f"1080×1350 (4:5 Feed Portrait — {resolved_fmt} • {resolved_palette})", use_container_width=True)

slug = re.sub(r"[^a-zA-Z0-9]+", "_", ed_head).strip("_").lower() or "echoes_card"
file_name = f"{next_d.replace('-', '')}_{slug}.jpg"
img_buf = io.BytesIO()
final_img.save(img_buf, format="JPEG", quality=95)
st.download_button(f"💾 Download Master 4:5 Image ({file_name})", img_buf.getvalue(), file_name, "image/jpeg")

# ---------------------------------------------------------
# 10. PROVOCATIVE, ENGAGING CAPTION WITH EMOJIS & HASHTAGS
# ---------------------------------------------------------
st.divider()
st.markdown("### 📝 5. Engaging Meta Feed Caption, Emojis & Hashtags")

hashtags_clean = card.get("tags", "#Mindset #LifeLessons #PersonalGrowth #SelfRespect #Discipline #Wisdom")
feed_caption = (
    f"⚡ {ed_head.upper()} 🏛️\n\n"
    f"💡 {card.get('caption_story', '')}\n\n"
    f"💬 {ed_ref_q.capitalize()} 👇\n\n"
    f"🔖 Save this reminder for tough days, or share it with someone building their future.\n"
    f"✨ Follow {get_persistent_handle()} for daily clarity.\n\n"
    f"{hashtags_clean}"
)
st.text_area("1. Meta Feed Post Caption (Zero Engagement Bait)", feed_caption, height=195)
render_copy_btn("feed_cap", "COPY FEED CAPTION", feed_caption)

st.text_input("2. Hashtags Only", hashtags_clean)
render_copy_btn("feed_tags", "COPY HASHTAGS", hashtags_clean)

first_comment = (
    f"🏛️ Want a structured daily system to build emotional composure and mental discipline? ✨\n\n"
    f"📘 Explore The 30-Day Stoic Emotional Mastery Guide & Workbook here:\n"
    f"{get_persistent_guide_url()}\n"
    f"🎟️ Use code FIRST50 at checkout"
)
st.text_area("3. Pinned First Comment (Clean Guide Link)", first_comment, height=115)
render_copy_btn("first_comm", "COPY FIRST COMMENT", first_comment)

# ---------------------------------------------------------
# 11. DIRECT META COMPOSER & SCHEDULE LOCK
# ---------------------------------------------------------
st.markdown("""
<div style="margin: 14px 0 16px 0;">
    <a href="https://business.facebook.com/latest/composer" target="_blank" style="text-decoration: none;">
        <button style="width: 100%; height: 3.2rem; background: #1877F2; color: white; border: none; border-radius: 8px; font-weight: 700; font-family: -apple-system, sans-serif; font-size: 13px; cursor: pointer; box-shadow: 0 4px 15px rgba(24, 119, 242, 0.35);">
            🌐 OPEN META BUSINESS SUITE COMPOSER
        </button>
    </a>
</div>
""", unsafe_allow_html=True)

col_s1, col_s2 = st.columns(2)
with col_s1:
    sched_date = st.date_input("Schedule Date", value=datetime.strptime(next_d, "%Y-%m-%d").date())
with col_s2:
    sched_time = st.text_input("Schedule Time (IST)", value=db.get("post_time", "17:30"))

if st.button("✅ Lock Post & Advance Schedule", type="primary"):
    d_str = sched_date.strftime("%Y-%m-%d")
    db["scheduled_posts"].append({
        "date": d_str,
        "time": sched_time,
        "pillar": edited_card.get("pillar", "SOVEREIGNTY"),
        "format_style": resolved_fmt,
        "headline": ed_head,
        "file": file_name
    })
    if ed_head not in db.get("used_headlines", []):
        db.setdefault("used_headlines", []).append(ed_head)
    db["last_date"] = d_str
    db["post_time"] = sched_time
    save_db(db)

    append_image_excel_tracker({
        "date": d_str,
        "time": sched_time,
        "pillar": edited_card.get("pillar", ""),
        "format_style": resolved_fmt,
        "category": ed_cat,
        "headline": ed_head,
        "author": ed_auth,
        "file": file_name,
        "caption": feed_caption,
        "first_comment": first_comment
    })

    st.session_state["img_banner"] = f"✓ Scheduled '{ed_head}' ({resolved_fmt}) for {d_str} @ {sched_time} IST!"
    st.rerun()

# ---------------------------------------------------------
# 12. SCHEDULED QUEUE & EXCEL EXPORT
# ---------------------------------------------------------
if os.path.exists(EXCEL_IMAGE_TRACKER):
    with open(EXCEL_IMAGE_TRACKER, "rb") as ef:
        st.download_button(
            "📊 Download Image Content Tracker (.xlsx)",
            ef.read(),
            "Echoes_Image_Content_Tracker.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if db.get("scheduled_posts"):
    with st.expander(f"📋 SCHEDULED QUEUE ({len(db['scheduled_posts'])})", expanded=False):
        for item in reversed(db["scheduled_posts"]):
            st.markdown(f"""
            <div style="background: #080B11; border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #38BDF8; font-weight: 700;">{item.get('date')}</span>
                    <span style="color: #64748B;"> @ </span>
                    <span style="color: #FBBF24;">{item.get('time', '17:30')} IST</span>
                    <div style="color: #F8FAFC; font-weight: 600; margin-top: 2px;">{item.get('headline')}</div>
                    <div style="color: #94A3B8; font-size: 11px;">Format: {item.get('format_style', 'CHISELED_HERO')}</div>
                </div>
                <div style="color: #34D399; font-weight: 700; font-size: 11px;">● SCHEDULED</div>
            </div>
            """, unsafe_allow_html=True)
