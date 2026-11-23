import os, io, json, re, random, base64
from datetime import datetime, timedelta, timezone, time as dt_time
from PIL import Image, ImageEnhance
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
st.set_page_config(page_title="Echoes Flow Image Studio", page_icon="🏛️", layout="centered", initial_sidebar_state="collapsed")

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
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "image_schedule.json")
CARD_VAULT_PATH = os.path.join(DATA_DIR, "flow_prompt_vault.json")
ACTIVE_CARD_PATH = os.path.join(DATA_DIR, "active_flow_card.json")
SAVED_FLOW_IMG_PATH = os.path.join(DATA_DIR, "saved_flow_image.png")
SAVED_LOGO_PATH = os.path.join(DATA_DIR, "brand_logo.png")
API_KEY_FILE = os.path.join(DATA_DIR, "gemini_key.txt")
CHANNEL_HANDLE_FILE = os.path.join(DATA_DIR, "meta_handle.txt")
GUIDE_URL_FILE = os.path.join(DATA_DIR, "guide_url.txt")
EXCEL_IMAGE_TRACKER = os.path.join(DATA_DIR, "Echoes_Image_Content_Tracker.xlsx")

def find_active_logo_path():
    if os.path.exists(SAVED_LOGO_PATH):
        return SAVED_LOGO_PATH
    repo_logo = os.path.join(BASE_DIR, "logo.png")
    if os.path.exists(repo_logo):
        return repo_logo
    return None

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
        "used_styles": [],
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

def save_active_card_to_disk(card_item, src_str="Saved Prompt"):
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
# 3. 8 DISTINCT FULL-BLEED 4:3 GOOGLE FLOW STYLES, 6 PALETTES & LEADERS
# ---------------------------------------------------------
PILLAR_DEFINITIONS = {
    "ALL": "🎲 Smart AI Rotation (All 5 Pillars)",
    "SOVEREIGNTY": "🛡️ Silent Power & Boundaries",
    "FINANCE": "⚖️ Financial Sovereignty & Control",
    "LEGACY": "🏛️ Father to Son: Legacy Counsel",
    "LONGEVITY": "⏳ Aging Well: Vitality After 40/60",
    "PARABLES": "🌲 Ancient & Modern Parables"
}

FLOW_VISUAL_STYLES = {
    "01_MODERN_WINDOW_APARTMENT": {
        "label": "01. 🏙️ Modern Window Apartment + Clean Sans-Serif",
        "typo_spec": "ultra-bold modern white and emerald-green sans-serif typography arranged cleanly in the upper-left negative space",
        "art_spec": "full-bleed 35mm editorial lifestyle photograph of a thoughtful person beside a tall apartment window overlooking a sunlit city at morning"
    },
    "02_CLASSIC_OIL_CHIAROSCURO": {
        "label": "02. 🏛️ Classical Chiaroscuro Oil Painting + Gold Serif",
        "typo_spec": "bold chiseled gold serif typography centered in the upper third with subtle drop shadow and thin horizontal gold divider lines",
        "art_spec": "edge-to-edge museum-grade chiaroscuro oil painting with dramatic golden-hour rim lighting, deep shadows, and fine canvas texture"
    },
    "03_MINIMAL_OBSIDIAN_POSTER": {
        "label": "03. ✍️ Minimal Obsidian Poster + Highlighted Power Words",
        "typo_spec": "high-contrast editorial serif typography on a matte obsidian-black background with thin geometric corner brackets and key power words highlighted in glowing gold",
        "art_spec": "full-bleed minimalist dark charcoal studio backdrop with subtle radial rim light and faint geometric lines"
    },
    "04_MONOCHROME_STREET_GRIT": {
        "label": "04. 🖤 Stark Monochrome Street Documentary + White & Red Text",
        "typo_spec": "bold condensed white sans-serif typography with a single vivid crimson-red accent word, positioned cleanly in open shadow space",
        "art_spec": "full-bleed high-contrast black-and-white 35mm street documentary photograph with mist, natural film grain, and moody silhouettes"
    },
    "05_ENGRAVED_PORTRAIT_PARCHMENT": {
        "label": "05. 📜 Vintage Engraved Portrait + Crimson & Charcoal Serif",
        "typo_spec": "refined crimson-red and charcoal editorial serif typography printed cleanly on warm textured paper on the left half",
        "art_spec": "detailed vintage engraved studio portrait of a wise thinker or mentor on the right half in balanced 4:3 horizontal composition"
    },
    "06_STORYBOOK_MARKER_HIGHLIGHT": {
        "label": "06. 💛 Warm Hand-Painted Illustration + Marker Highlight",
        "typo_spec": "bold dark serif typography with a warm marker highlight behind the opening phrase positioned cleanly in the upper sky area",
        "art_spec": "edge-to-edge expressive warm hand-painted illustration of a peaceful traveler in golden rain or sunlit hills with rich color harmony"
    },
    "07_SACRED_GEOMETRY_SHADOW": {
        "label": "07. 🔺 Sacred Geometry Compass + Symbolic Lion Shadow",
        "typo_spec": "spaced uppercase typewriter-monospace silver-white typography framed by subtle geometric compass lines",
        "art_spec": "full-bleed moody dark slate symbolic artwork featuring a lone figure casting a poised lion shadow in morning mist"
    },
    "08_FIVE_POINT_CHECKLIST": {
        "label": "08. 📋 5-Point Behavioral Checklist + Gold Number Badges",
        "typo_spec": "bold uppercase header with a thin gold underline followed by 5 cleanly aligned numbered points (1 to 5) with circular gold number badges",
        "art_spec": "full-bleed dark architectural stone and soft volumetric light beam backdrop behind structured typography"
    },
    "09_SPLIT_CONTRAST_COMPARISON": {
        "label": "09. 🔀 Two-Side Contrast Card (What Drains vs. What Builds)",
        "typo_spec": "clean split-screen comparison typography with two contrasting rounded dark cards side by side in the upper-middle frame",
        "art_spec": "full-bleed atmospheric dusk twilight backdrop with subtle depth and clean visual separation"
    },
    "10_RAINY_CAFE_REFLECTION": {
        "label": "10. ☕ Rainy Cafe Window & Coffee Notebook + Warm Serif",
        "typo_spec": "warm ivory serif typography with subtle drop shadow placed cleanly in the upper-right dark interior space",
        "art_spec": "full-bleed cozy 35mm photograph of a steaming ceramic coffee mug and leather notebook beside a rain-streaked cafe window at twilight"
    },
    "11_MOUNTAIN_SUMMIT_DAWN": {
        "label": "11. 🏔️ Alpine Granite Ridge at Sunrise + Condensed Block",
        "typo_spec": "tall condensed bone-white and amber block lettering centered in the clear morning sky above the mountain ridge",
        "art_spec": "full-bleed cinematic wide-angle photograph of a lone hiker standing on a sunlit alpine granite ridge above a sea of morning clouds"
    },
    "12_JAPANESE_INK_SUMI": {
        "label": "12. 🎋 Japanese Sumi-e Brush Ink & Red Seal + Minimal Serif",
        "typo_spec": "crisp charcoal serif typography with a small vermilion-red square stamp accent on textured off-white rice paper",
        "art_spec": "minimalist Japanese sumi-e ink wash painting of bamboo leaves and misty mountain peaks with generous negative space"
    },
    "13_ARCHITECTURAL_BRUTALISM": {
        "label": "13. 🏗️ Concrete & Sunlight Geometry + Industrial Sans",
        "typo_spec": "sharp geometric white and electric-cyan sans-serif typography aligned with dramatic architectural shadow lines",
        "art_spec": "full-bleed minimalist architectural photograph of raw concrete colonnades and sharp diagonal shafts of golden sunlight"
    },
    "14_VINTAGE_LIBRARY_STUDY": {
        "label": "14. 📚 Candlelit Wood-Paneled Library + Antique Gold Serif",
        "typo_spec": "classic antique gold serif typography framed by thin ornamental rules in the shadowed upper left",
        "art_spec": "full-bleed warm atmospheric photograph of an old wood-paneled study with leather-bound books, brass desk lamp, and antique globe"
    },
    "15_COASTAL_LIGHTHOUSE_STORM": {
        "label": "15. 🌊 Stormy Coastal Lighthouse + High-Contrast White Block",
        "typo_spec": "bold weather-worn white block typography with subtle slate shadow in the dark stormy sky",
        "art_spec": "full-bleed dramatic seascape photograph of a solitary stone lighthouse holding a steady beam through crashing ocean waves and mist"
    },
    "16_FORGE_ANVIL_SPARKS": {
        "label": "16. 🔨 Blacksmith Forge & Glowing Steel + Molten Amber Type",
        "typo_spec": "heavy chiseled molten-amber and white slab-serif typography in the dark upper workshop space",
        "art_spec": "full-bleed dramatic close-up photograph of glowing hot steel on an anvil with golden sparks flying in a dark stone forge"
    },
    "17_OLD_POCKET_WATCH_TIME": {
        "label": "17. ⏳ Vintage Brass Pocket Watch & Hourglass + Literary Italic",
        "typo_spec": "refined literary italic serif typography in warm champagne gold and ivory",
        "art_spec": "full-bleed macro still-life photograph of an antique brass pocket watch and hourglass resting on dark walnut wood in warm side light"
    },
    "18_FOREST_PATH_MIST": {
        "label": "18. 🌲 Ancient Redwood Forest Mist + Emerald & White Serif",
        "typo_spec": "clean luminous emerald and bone-white serif typography floating in the misty upper canopy space",
        "art_spec": "full-bleed atmospheric photograph of sunbeams piercing through morning fog in an ancient pine and redwood forest"
    },
    "19_CHESSBOARD_STRATEGY": {
        "label": "19. ♟️ Wooden Chessboard Macro + Sharp Monospace",
        "typo_spec": "crisp typewriter-monospace silver and gold typography positioned cleanly in the dark background above the board",
        "art_spec": "full-bleed shallow-depth-of-field macro photograph of carved wooden chess pieces in dramatic side lighting"
    },
    "20_DESERT_DUNES_SOLITUDE": {
        "label": "20. 🏜️ Golden Desert Dunes at Twilight + Minimalist Sans",
        "typo_spec": "clean wide-tracked uppercase white sans-serif typography centered in the deep twilight indigo sky",
        "art_spec": "full-bleed serene photograph of sweeping golden sand dunes with sharp wind-carved ridges under a deep twilight sky"
    },
    "21_HARBOR_DAWN_VESSEL": {
        "label": "21. ⛵ Quiet Wooden Boat on Glass Lake + Soft Gold Serif",
        "typo_spec": "elegant soft-gold and white serif typography reflected in the calm upper sky space",
        "art_spec": "full-bleed tranquil sunrise photograph of a solitary wooden rowboat moored on mirror-still lake water in golden mist"
    },
    "22_WORKSHOP_BLUEPRINT_CRAFT": {
        "label": "22. 📐 Craftsman Workbench & Blueprints + Technical Sans",
        "typo_spec": "crisp architectural white and cyan sans-serif typography with thin technical rule lines",
        "art_spec": "full-bleed overhead-angle photograph of precision woodworking hand tools, compass, and rolled drafting paper on an oak bench"
    },
    "23_AUTUMN_PARK_BENCH": {
        "label": "23. 🍂 Quiet Park Bench & Autumn Leaves + Warm Editorial Serif",
        "typo_spec": "warm cream and amber serif typography nestled in the soft-focus golden foliage upper area",
        "art_spec": "full-bleed candid 35mm photograph of an older mentor and younger man talking calmly beside a park bench in warm autumn light"
    },
    "24_NIGHT_CITY_RAIN_NEON": {
        "label": "24. 🌃 Rain-Slicked City Street at Night + Clean White Block",
        "typo_spec": "bold modern white sans-serif typography with a subtle cyan accent underline in the dark upper sky",
        "art_spec": "full-bleed moody cinematic night photograph of a man in a dark trench coat walking down a quiet rain-slicked city street with warm reflections"
    },
    "25_SUNDIAL_STONE_COURTYARD": {
        "label": "25. ☀️ Ancient Roman Stone Sundial + Chiseled Roman Serif",
        "typo_spec": "classic Roman chiseled gold and ivory serif typography centered cleanly above the stone pedestal",
        "art_spec": "full-bleed warm afternoon photograph of a weathered stone sundial casting a sharp shadow in a quiet Mediterranean courtyard"
    },
    "26_TRAIN_WINDOW_JOURNEY": {
        "label": "26. 🚆 Vintage Train Window Overlooking Hills + Warm Serif",
        "typo_spec": "clean warm-ivory serif typography positioned in the shadowed interior frame beside the window",
        "art_spec": "full-bleed nostalgic photograph looking out a classic train compartment window at misty green hills at sunrise"
    },
    "27_COMPASS_MAP_EXPEDITION": {
        "label": "27. 🧭 Antique Brass Compass on Weathered Map + Gold Slab",
        "typo_spec": "bold antique-gold and ivory slab-serif typography arranged cleanly in the upper dark corner",
        "art_spec": "full-bleed macro photograph of an open brass magnetic compass resting on a vintage parchment map lit by warm lantern glow"
    },
    "28_STARRY_NIGHT_SILHOUETTE": {
        "label": "28. 🌌 Clear Starry Night Over Mountain Ridge + Silver Serif",
        "typo_spec": "crisp silver-white serif typography centered in the vast starry night sky above the horizon",
        "art_spec": "full-bleed long-exposure photograph of a lone silhouette standing on a dark ridge beneath a crystal-clear Milky Way night sky"
    }
}
COLOR_PALETTES = {
    "IMPERIAL_GOLD":  {"label": "👑 Imperial Gold & Obsidian",   "desc": "radiant imperial gold and crisp ivory-white lettering against deep obsidian shadows"},
    "GLACIAL_ICE":    {"label": "❄️ Glacial Cyan & Steel",       "desc": "frost glacial cyan and pure white lettering against cool steel-blue shadows"},
    "FORGE_AMBER":    {"label": "🔥 Molten Amber & Charcoal",    "desc": "molten forge amber-orange and warm cream lettering against dark charcoal"},
    "CRIMSON_IVORY":  {"label": "🩸 Deep Crimson & Warm Cream",  "desc": "deep editorial crimson and charcoal-black ink on warm textured paper"},
    "EMERALD_BONE":   {"label": "🌿 Luminous Emerald & Bone",    "desc": "luminous emerald-green and bone-white lettering against deep forest slate"},
    "ROYAL_VIOLET":   {"label": "🔮 Royal Orchid & Gold",        "desc": "electric orchid-violet and antique gold lettering against deep midnight tones"}
}

LEADER_PRINCIPLES = [
    {"leader": "Abraham Lincoln",    "era": "19th-Century Leadership", "principle": "Spend four hours sharpening the axe before taking a single swing at the tree."},
    {"leader": "Marcus Aurelius",    "era": "Ancient Rome",            "principle": "You command your own mind, never external events; real strength begins inward."},
    {"leader": "Winston Churchill",  "era": "Modern History",          "principle": "Keep walking forward through setbacks without surrendering your resolve."},
    {"leader": "Nelson Mandela",     "era": "Modern History",          "principle": "Holding onto bitterness harms only the person carrying it; forgive to walk free."},
    {"leader": "Theodore Roosevelt", "era": "Modern History",          "principle": "Honor belongs to the person inside the arena doing the work, never the critic in the stands."},
    {"leader": "Benjamin Franklin",  "era": "Enlightenment",           "principle": "Watch small daily leaks in spending and time before they sink a great ship."},
    {"leader": "Albert Einstein",    "era": "Modern Science",          "principle": "Focus on becoming genuinely valuable rather than merely chasing applause."},
    {"leader": "Bruce Lee",          "era": "Modern Philosophy",       "principle": "Stay adaptable like flowing water—rigid pride snaps under sudden pressure."},
    {"leader": "Seneca",             "era": "Ancient Rome",            "principle": "We suffer far more in our own imagination than in actual reality."},
    {"leader": "Epictetus",          "era": "Ancient Greece",          "principle": "Events do not disturb us; our own interpretation of them does."},
    {"leader": "Viktor Frankl",      "era": "Modern Psychology",       "principle": "Between provocation and reaction lies a pause, and in that pause lives your freedom."},
    {"leader": "Charlie Munger",     "era": "Modern Finance",          "principle": "Long-term advantage comes from consistently avoiding foolish, impulsive mistakes."},
    {"leader": "Miyamoto Musashi",   "era": "Feudal Japan",            "principle": "Master one craft deeply and refuse to waste energy on useless distractions."},
    {"leader": "Lao Tzu",            "era": "Ancient China",           "principle": "Nature never rushes, yet every season accomplishes its work on time."},
    {"leader": "Socrates",           "era": "Ancient Greece",          "principle": "When someone loses a fair argument, personal insults become their last refuge."}
]

FLOW_CURATED_VAULT = [
    {
        "id": "FLOW_MODERN_MONEY",
        "pillar": "FINANCE",
        "flow_style": "MODERN_EDITORIAL_PHOTO",
        "palette": "EMERALD_BONE",
        "headline": "NOBODY PAYS YOUR BILLS OUT OF SYMPATHY",
        "subtext": "Quiet savings buy the freedom to say no without panic.",
        "author": "BENJAMIN FRANKLIN PRINCIPLE",
        "visual_subject": "A thoughtful man in his late thirties wearing a dark knit sweater sitting at a sunlit wooden desk by a city apartment window with a black coffee mug and clean notebook, natural morning window light",
        "reflection_prompt": "What is one money habit that gave you real peace of mind as you got older?",
        "caption_story": "In my twenties, I thought looking successful mattered more than owning my time. By forty, I realized sympathy never covers a mortgage and obligation never builds security. Every dollar you refuse to waste on empty status buys your independence when life tests your household.",
        "tags": "#MoneyMindset #FinancialFreedom #Discipline #Stoicism #LifeLessons"
    },
    {
        "id": "FLOW_LINCOLN_AXE",
        "pillar": "LEGACY",
        "flow_style": "WARM_PARCHMENT_PORTRAIT",
        "palette": "CRIMSON_IVORY",
        "headline": "SHARPEN THE AXE BEFORE YOU SWING",
        "subtext": "Four hours of quiet preparation prevent four months of regret.",
        "author": "ABRAHAM LINCOLN",
        "visual_subject": "Detailed vintage engraved studio portrait of a thoughtful nineteenth-century statesman with weathered features and calm resolve on the right side of the frame against warm textured paper",
        "reflection_prompt": "Where has extra preparation saved you from unnecessary stress or regret?",
        "caption_story": "Most people rush into major career, money, or family decisions without slowing down to think two moves ahead. Quiet planning turns steady effort into real leverage. Prepare in private so you never have to panic in public.",
        "tags": "#AbrahamLincoln #Leadership #Preparation #Wisdom #LifeLessons"
    },
    {
        "id": "FLOW_FRANKL_PAUSE",
        "pillar": "SOVEREIGNTY",
        "flow_style": "SACRED_GEOMETRY_MYTHIC",
        "palette": "GLACIAL_ICE",
        "headline": "BETWEEN PROVOCATION AND REACTION LIES YOUR FREEDOM",
        "subtext": "Lose your temper, and a stranger becomes your master.",
        "author": "VIKTOR FRANKL",
        "visual_subject": "A solitary man standing calmly in a misty dark courtyard casting the shadow of a poised lion behind him, framed by minimal geometric compass lines",
        "reflection_prompt": "What helps you pause before reacting when someone tries to provoke you?",
        "caption_story": "Even under intense pressure, you still own the two-second space between what happens and how you respond. The moment an insult pulls you out of character, someone else holds the remote control to your mood. Guard that space fiercely.",
        "tags": "#ViktorFrankl #SelfControl #EmotionalIntelligence #Mindset #Stoicism"
    },
    {
        "id": "FLOW_ROOSEVELT_ARENA",
        "pillar": "SOVEREIGNTY",
        "flow_style": "MONOCHROME_GRIT_SCENE",
        "palette": "FORGE_AMBER",
        "headline": "IGNORE THE CRITICS. STAY IN THE ARENA.",
        "subtext": "People who build nothing always have plenty of advice.",
        "author": "THEODORE ROOSEVELT",
        "visual_subject": "Stark black-and-white 35mm documentary shot of a weathered boxer or craftsman standing resolute in a misty industrial yard with dramatic side light",
        "reflection_prompt": "How do you tune out critics who haven't walked in your shoes?",
        "caption_story": "It is easy to judge from the bleachers when nothing is on the line. Real respect belongs to the person doing the work, taking the hits, and refining their craft when nobody claps. Keep your eyes on your own standard.",
        "tags": "#TheodoreRoosevelt #Resilience #Discipline #Mindset #Courage"
    },
    {
        "id": "FLOW_MANDELA_POISON",
        "pillar": "LONGEVITY",
        "flow_style": "STORYBOOK_WARM_ILLUSTRATION",
        "palette": "ROYAL_VIOLET",
        "headline": "BITTERNESS ONLY POISONS THE ONE WHO CARRIES IT",
        "subtext": "Let go of old grudges to reclaim your peace after forty.",
        "author": "NELSON MANDELA",
        "visual_subject": "Full-bleed warm hand-painted illustration of an older traveler sitting peacefully on a sunlit mountain ridge overlooking a calm valley at golden hour",
        "reflection_prompt": "What old grudge or worry are you glad you finally left behind?",
        "caption_story": "Carrying bitterness ages your spirit and steals your sleep while the other person moves on without a second thought. Forgiving is not excusing bad behavior—it is refusing to let someone live rent-free in your head. Lighten your load.",
        "tags": "#NelsonMandela #PeaceOfMind #LifeAfter40 #EmotionalHealth #Wisdom"
    },
    {
        "id": "FLOW_FIVE_SILENT_PLACES",
        "pillar": "PARABLES",
        "flow_style": "NUMBERED_CHECKLIST_POSTER",
        "palette": "IMPERIAL_GOLD",
        "headline": "5 PLACES TO STAY SILENT AT ALL COSTS:",
        "subtext": "1. When anger wants the first word. 2. When you lack full facts. 3. When baited into a fight. 4. When plans are unfinished. 5. When actions prove it better.",
        "author": "ANCIENT & MODERN CODE",
        "visual_subject": "Dark obsidian architectural stone backdrop with a subtle golden shaft of light and clean layout space for 5 numbered points",
        "reflection_prompt": "Which of these five moments is hardest for you to hold silence in real life?",
        "caption_story": "Silence is not weakness when you hold composure—it is leverage. A single measured pause can protect a marriage, a business deal, or your dignity when emotions run hot. Save this checklist for tough conversations.",
        "tags": "#SelfControl #Boundaries #Communication #Stoicism #LifeLessons"
    },
    {
        "id": "FLOW_MUSASHI_CRAFT",
        "pillar": "LEGACY",
        "flow_style": "CLASSIC_OIL_RELIEF",
        "palette": "IMPERIAL_GOLD",
        "headline": "MASTER ONE CRAFT DEEPLY",
        "subtext": "Deep skill in one discipline builds clarity across your entire life.",
        "author": "MIYAMOTO MUSASHI",
        "visual_subject": "Edge-to-edge classical chiaroscuro oil painting of a master woodworker guiding an apprentice over precision hand tools by warm lantern light in a quiet timber workshop",
        "reflection_prompt": "What one skill or habit has paid you back across every stage of life?",
        "caption_story": "Chasing ten shiny shortcuts produces shallow results. Going deep on one real skill builds patience, judgment, and self-command that transfer to everything else you touch.",
        "tags": "#MiyamotoMusashi #Mastery #Discipline #Legacy #PersonalGrowth"
    },
    {
        "id": "FLOW_MUNGER_FOLLY",
        "pillar": "FINANCE",
        "flow_style": "DARK_MINIMAL_TYPO",
        "palette": "GLACIAL_ICE",
        "headline": "CONSISTENTLY AVOID FOOLISH MISTAKES",
        "subtext": "Long-term advantage comes from protecting your downside first.",
        "author": "CHARLIE MUNGER",
        "visual_subject": "Matte obsidian-black background with subtle radial cyan rim light and thin geometric corner frame lines",
        "reflection_prompt": "What is one mistake you avoided that ended up paying off years later?",
        "caption_story": "You do not need to be brilliant every day to build a strong life. Simply avoiding impulse debt, toxic partnerships, and impatient decisions puts you ahead of almost everyone over ten years.",
        "tags": "#CharlieMunger #FinancialWisdom #Discipline #Mindset #InvestingInSelf"
    }
]

# ---------------------------------------------------------
# 4. GOOGLE FLOW PROMPT ARCHITECT (NATIVE 4:3 FULL-BLEED)
# ---------------------------------------------------------
def build_google_flow_image_prompt(card_data, flow_style_key="MODERN_EDITORIAL_PHOTO", palette_key="IMPERIAL_GOLD", handle_str="@EchoesOfWisdomOfficial"):
    style_meta = FLOW_VISUAL_STYLES.get(flow_style_key, FLOW_VISUAL_STYLES["MODERN_EDITORIAL_PHOTO"])
    pal_meta = COLOR_PALETTES.get(palette_key, COLOR_PALETTES["IMPERIAL_GOLD"])

    headline = card_data.get("headline", "").strip()
    subtext = card_data.get("subtext", "").strip()
    author = card_data.get("author", "").strip()
    subject = card_data.get("visual_subject", "").strip()

    sub_clause = f' Directly beneath the headline in smaller clean lettering is the supporting line: "{subtext}".' if subtext else ""
    auth_clause = f' Below the text is a thin accent divider line and subtle attribution reading: "— {author}".' if author else ""

    return (
        f"[4:3 full-bleed social media feed graphic] {style_meta['art_spec']}. "
        f"SUBJECT & SCENE: {subject}. "
        f"TYPOGRAPHY & LAYOUT: {style_meta['typo_spec']}, rendered in {pal_meta['desc']}. "
        f"The main headline reads verbatim: \"{headline}\".{sub_clause}{auth_clause} "
        f"Positioned subtly in the top-left corner is a small, clean brand handle reading \"{handle_str}\". "
        f"COMPOSITION & SAFE ZONE: Keep ALL text, lines, and attributions strictly within the upper and middle 82% of the frame, leaving the bottom 18% completely free of any text or lines so zero cropping is ever required. Edge-to-edge full-bleed 4:3 framing with NO outer border frames, razor-sharp accurate spelling, no text overlapping faces, strictly two arms per person, photorealistic 8k."
    )

def synthesize_flow_card_package(raw_key, pillar_choice="ALL", flow_style_choice="AUTO", palette_choice="AUTO"):
    clean_k = raw_key.strip().strip('"').strip("'")
    used_heads = db.get("used_headlines", [])[-35:]
    available = [
        c for c in FLOW_CURATED_VAULT
        if (pillar_choice == "ALL" or c["pillar"] == pillar_choice) and c["headline"] not in used_heads
    ]
    if not available:
        available = [c for c in FLOW_CURATED_VAULT if (pillar_choice == "ALL" or c["pillar"] == pillar_choice)] or FLOW_CURATED_VAULT

    base = dict(random.choice(available))
    used_st = db.get("used_styles", [])[-28:]
    if flow_style_choice == "AUTO":
        unused_style_keys = [k for k in FLOW_VISUAL_STYLES.keys() if k not in used_st]
        if not unused_style_keys:
            unused_style_keys = list(FLOW_VISUAL_STYLES.keys())
        resolved_style = random.choice(unused_style_keys)
    else:
        resolved_style = flow_style_choice
    resolved_pal = base.get("palette", "IMPERIAL_GOLD") if palette_choice == "AUTO" else palette_choice
    base["flow_style"] = resolved_style
    base["palette"] = resolved_pal

    leader_pick = random.choice(LEADER_PRINCIPLES)
    handle_str = get_persistent_handle()

    if not clean_k:
        base["flow_prompt"] = build_google_flow_image_prompt(base, resolved_style, resolved_pal, handle_str)
        return base, f"Curated Vault • {base.get('author','Wisdom')}"

    pillar_label = PILLAR_DEFINITIONS.get(base["pillar"], "Silent Power")
    style_meta = FLOW_VISUAL_STYLES.get(resolved_style, FLOW_VISUAL_STYLES["MODERN_EDITORIAL_PHOTO"])
    pal_meta = COLOR_PALETTES.get(resolved_pal, COLOR_PALETTES["IMPERIAL_GOLD"])

    ai_prompt = (
        f"You are Executive Creative Director for 'Echoes of Wisdom' (Facebook & Instagram 4:3 Feed Posts for men aged 35-65+ in US, UK, Canada, Australia).\n"
        f"TARGET PILLAR: {pillar_label}\n"
        f"VISUAL FORMAT FOR GOOGLE FLOW: {style_meta['label']} — {style_meta['art_spec']}\n"
        f"TYPOGRAPHY STYLE FOR GOOGLE FLOW: {style_meta['typo_spec']} in {pal_meta['desc']}\n"
        f"LEADER / THINKER PRINCIPLE: {leader_pick['leader']} ({leader_pick['era']}) — {leader_pick['principle']}\n"
        f"FORBIDDEN HEADLINES: {', '.join(used_heads) if used_heads else 'None'}\n"
        f"STRICT QUALITY & COMMENT-ENGAGEMENT RULES:\n"
        f"1. Create a deeply relatable, thought-provoking 4:3 feed post inspired by {leader_pick['leader']} or a real-life turning point (money habits, quiet boundaries, father-to-son wisdom, aging with clarity, or human nature).\n"
        f"2. HEADLINE: 4 to 10 crisp, punchy words to render on the image (spelled cleanly so Google Flow renders every word accurately).\n"
        f"3. SUBTEXT: 1 sharp supporting sentence (6 to 14 words) or 5 concise numbered rules if using a checklist style.\n"
        f"4. VISUAL_SUBJECT: Vivid edge-to-edge full-bleed 4:3 scene description—alternate between modern everyday realism (sunlit city apartment, quiet coffee desk, rainy dusk street, family doorway) and classic/ancient scenes, with NO outer border frames.\n"
        f"5. REFLECTION_PROMPT: Write a specific, personal, experience-based question that makes readers want to share their own story in the comments (e.g., 'What is one hard lesson about money or loyalty that took you years to learn?' — NEVER generic filler and NEVER engagement bait like 'Drop 1 or 2').\n"
        f"6. CAPTION_STORY: Write 3 rich, human, conversational sentences that tell a relatable micro-story or hard truth readers feel compelled to save and discuss.\n"
        f"OUTPUT STRICT JSON ONLY:\n"
        "{\n"
        f'  "pillar": "{base["pillar"]}",\n'
        f'  "flow_style": "{resolved_style}",\n'
        f'  "palette": "{resolved_pal}",\n'
        '  "headline": "Punchy headline for image text overlay",\n'
        '  "subtext": "Short supporting line for image text overlay",\n'
        f'  "author": "{leader_pick["leader"]}",\n'
        '  "visual_subject": "Detailed full-bleed 4:3 subject & setting description...",\n'
        '  "reflection_prompt": "Personal experience-based question for comments?",\n'
        '  "caption_story": "Three compelling, human sentences expanding the lesson.",\n'
        '  "tags": "#Mindset #LifeLessons #PersonalGrowth #Discipline #Wisdom"\n'
        "}"
    )

    try:
        client = get_fast_gemini_client(clean_k)
        for m in ["gemini-3.8-flash", "gemini-3.8-flash-lite"]:
            try:
                cfg = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.92, max_output_tokens=1000)
                res = client.models.generate_content(model=m, contents=ai_prompt, config=cfg)
                raw = res.text.strip()
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                parsed = json.loads(match.group(0) if match else raw)
                if isinstance(parsed, dict) and "headline" in parsed and "visual_subject" in parsed:
                    parsed["id"] = f"FLOW_{datetime.now().strftime('%H%M%S')}"
                    parsed["flow_style"] = resolved_style
                    parsed["palette"] = resolved_pal
                    parsed["flow_prompt"] = build_google_flow_image_prompt(parsed, resolved_style, resolved_pal, handle_str)
                    return parsed, f"Gemini AI • {leader_pick['leader']}"
            except Exception:
                continue
    except Exception:
        pass

    base["flow_prompt"] = build_google_flow_image_prompt(base, resolved_style, resolved_pal, handle_str)
    return base, f"Curated Vault • {base.get('author','Wisdom')}"

# ---------------------------------------------------------
# 5. FULL-BLEED WATERMARK CROPPER, LOGO OVERLAY & EXPORT ENGINE
# ---------------------------------------------------------
def process_uploaded_flow_image(
    pil_img,
    bottom_crop_pct=0.0,
    clean_br_corner=True,
    logo_path=None,
    logo_pos="Bottom-Right (Covers Sparkle)",
    logo_scale_pct=11,
    logo_opacity=0.95,
    sharpness_boost=1.05,
    contrast_boost=1.04
):
    im = pil_img.convert("RGBA")
    w, h = im.size

    if bottom_crop_pct > 0:
        new_h = int(h * (1.0 - bottom_crop_pct))
        im = im.crop((0, 0, w, max(100, new_h)))
        w, h = im.size

    target_w = 1440
    target_h = int(round(target_w * (h / float(w))))
    im = im.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Zero-crop bottom-right sparkle removal: sample clean background patch just left of the sparkle & blend smoothly
    if clean_br_corner and bottom_crop_pct == 0:
        patch_w = int(target_w * 0.11)
        patch_h = int(target_h * 0.11)
        src_box = (target_w - patch_w * 2 - 12, target_h - patch_h, target_w - patch_w - 12, target_h)
        dst_box = (target_w - patch_w, target_h - patch_h)
        if src_box[0] > 0 and src_box[1] > 0:
            clean_patch = im.crop(src_box).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            im.paste(clean_patch, dst_box)

    if logo_path and os.path.exists(logo_path) and logo_pos != "None":
        try:
            lg = Image.open(logo_path).convert("RGBA")
            lw = max(48, int(target_w * (logo_scale_pct / 100.0)))
            lh = max(24, int(lg.height * (lw / float(lg.width))))
            lg = lg.resize((lw, lh), Image.Resampling.LANCZOS)
            if logo_opacity < 1.0:
                alpha = lg.split()[3]
                alpha = alpha.point(lambda p: int(p * logo_opacity))
                lg.putalpha(alpha)

            pad = 24
            if "Bottom-Right" in logo_pos:
                pos = (target_w - lw - pad, target_h - lh - pad)
            elif "Bottom-Left" in logo_pos:
                pos = (pad, target_h - lh - pad)
            elif "Top-Right" in logo_pos:
                pos = (target_w - lw - pad, pad)
            else:
                pos = (pad, pad)

            im.alpha_composite(lg, dest=pos)
        except Exception:
            pass

    out_rgb = im.convert("RGB")
    if contrast_boost != 1.0:
        out_rgb = ImageEnhance.Contrast(out_rgb).enhance(contrast_boost)
    if sharpness_boost != 1.0:
        out_rgb = ImageEnhance.Sharpness(out_rgb).enhance(sharpness_boost)
    return out_rgb

def append_image_excel_tracker(entry):
    if not OPENPYXL_AVAILABLE:
        return False
    headers = [
        "Post ID", "Target Date", "Time (IST)", "Pillar", "Flow Style",
        "Headline", "Leader / Author", "File Name", "Feed Caption", "First Comment"
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
        entry.get("flow_style", ""),
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

if "flow_cycle_id" not in st.session_state:
    st.session_state["flow_cycle_id"] = 0

if not st.session_state.get("just_locked_cycle") and "active_flow_card" not in st.session_state and os.path.exists(ACTIVE_CARD_PATH):
    try:
        with open(ACTIVE_CARD_PATH, "r", encoding="utf-8") as af:
            saved_ac = json.load(af)
            if isinstance(saved_ac, dict) and "card" in saved_ac:
                st.session_state["active_flow_card"] = saved_ac["card"]
                st.session_state["active_flow_src"] = saved_ac.get("src", "Saved Prompt")
    except Exception:
        pass

# ---------------------------------------------------------
# 6. STUDIO HEADER, CREDENTIALS & PERSISTENT BRAND LOGO VAULT
# ---------------------------------------------------------
next_d = get_next_post_date()
st.markdown("""
<div style="font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: #F8FAFC; margin-bottom: 8px;">
    🏛️ ECHOES FLOW IMAGE STUDIO <span style="font-size: 13px; color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-weight: 600;">v4.10 // KEYERROR FIX, 8.0% DEFAULT WATERMARK CROP & 28 VISUAL STYLES</span>
</div>
""", unsafe_allow_html=True)

active_logo = find_active_logo_path()
st.markdown(f"""
<div style="margin-bottom: 14px;">
    <span class="badge badge-green">● 28 UNIQUE VISUAL STYLES (NO REPEAT)</span>
    <span class="badge badge-purple">🏛️ 15+ LEADERS & THINKERS</span>
    <span class="badge badge-blue">{'✓ BRAND LOGO READY' if active_logo else '🖼️ UPLOAD LOGO BELOW'}</span>
    <span class="badge badge-amber">📅 NEXT SLOT: {next_d} @ {db.get('post_time', '17:30')} IST</span>
</div>
""", unsafe_allow_html=True)

if "img_banner" in st.session_state:
    st.success(st.session_state.pop("img_banner"))

curr_key = get_persistent_api_key()
with st.expander("🔑 API CREDENTIALS, BRAND LOGO VAULT & HANDLE", expanded=(not bool(curr_key))):
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

    st.divider()
    st.markdown("#### 🏛️ Persistent Brand Logo (Auto-Stamped in App — Easier & Cleaner Than Flow)")
    col_lg1, col_lg2 = st.columns([2, 1])
    with col_lg1:
        logo_up = st.file_uploader("Upload Transparent PNG Logo (Saved permanently in vault)", type=["png", "webp", "jpg"], key="v45_logo_up")
        if logo_up:
            with open(SAVED_LOGO_PATH, "wb") as lf:
                lf.write(logo_up.read())
            st.success("✓ Brand logo saved permanently!")
            st.rerun()
    with col_lg2:
        cur_lg = find_active_logo_path()
        if cur_lg:
            st.image(cur_lg, caption="Active Logo", width=95)
            if st.button("🗑️ Remove Logo", key="v45_rm_logo"):
                if os.path.exists(SAVED_LOGO_PATH):
                    try: os.remove(SAVED_LOGO_PATH)
                    except Exception: pass
                st.rerun()

vault_hist = load_card_vault_history()
if vault_hist:
    with st.expander(f"📦 RESTORE PREVIOUS PROMPT ({len(vault_hist)} SAVED IN VAULT)", expanded=False):
        v_labels = [f"🖼️ {v.get('headline','Prompt')} — {v.get('author','')} ({v.get('flow_style','')})" for v in vault_hist]
        v_idx = st.selectbox("Select Saved Prompt", range(len(vault_hist)), format_func=lambda i: v_labels[i], key="img_vault_sel")
        if st.button("🔄 Restore Selected Prompt", key="img_vault_btn"):
            st.session_state["active_flow_card"] = vault_hist[v_idx]
            st.session_state["active_flow_src"] = "Saved Vault"
            save_active_card_to_disk(vault_hist[v_idx], "Saved Vault")
            st.rerun()

# ---------------------------------------------------------
# 7. STEP 1: GENERATE NATIVE 4:3 GOOGLE FLOW IMAGE + TEXT PROMPT
# ---------------------------------------------------------
st.markdown("### ⚡ 1. Generate Native 4:3 Google Flow Prompt")
col_p1, col_p2, col_p3 = st.columns([1.2, 1.2, 0.9])
with col_p1:
    chosen_pillar = st.selectbox(
        "Audience Pillar (35-65+)",
        list(PILLAR_DEFINITIONS.keys()),
        format_func=lambda k: PILLAR_DEFINITIONS[k]
    )
with col_p2:
    chosen_style = st.selectbox(
        "Google Flow Visual & Font Style",
        ["AUTO"] + list(FLOW_VISUAL_STYLES.keys()),
        format_func=lambda k: "🎲 Auto Style" if k == "AUTO" else FLOW_VISUAL_STYLES[k]["label"].split(" (")[0]
    )
with col_p3:
    chosen_palette = st.selectbox(
        "Color Palette",
        ["AUTO"] + list(COLOR_PALETTES.keys()),
        format_func=lambda k: "🎲 Auto Color" if k == "AUTO" else COLOR_PALETTES[k]["label"].split(" &")[0]
    )

col_btn1, col_btn2 = st.columns([2, 1])
with col_btn1:
    if st.button("🚀 Generate Fresh 4:3 Flow Prompt", type="primary", use_container_width=True):
        with st.spinner("⚡ Crafting full-bleed 4:3 Google Flow prompt with embedded typography & leader wisdom..."):
            st.session_state["just_locked_cycle"] = False
            card, src = synthesize_flow_card_package(get_persistent_api_key(), chosen_pillar, chosen_style, chosen_palette)
            st.session_state["active_flow_card"] = card
            st.session_state["active_flow_src"] = src
            if card.get("flow_style") not in db.get("used_styles", []):
                db.setdefault("used_styles", []).append(card.get("flow_style"))
                save_db(db)
            save_to_card_vault_history(card)
            save_active_card_to_disk(card, src)
            st.rerun()
with col_btn2:
    if st.button("🔄 Discard & New Prompt", use_container_width=True):
        with st.spinner("⚡ Generating a completely different leader, format & style..."):
            st.session_state["just_locked_cycle"] = False
            card, src = synthesize_flow_card_package(get_persistent_api_key(), "ALL", "AUTO", "AUTO")
            st.session_state["active_flow_card"] = card
            st.session_state["active_flow_src"] = src
            if card.get("flow_style") not in db.get("used_styles", []):
                db.setdefault("used_styles", []).append(card.get("flow_style"))
                save_db(db)
            save_to_card_vault_history(card)
            save_active_card_to_disk(card, src)
            st.rerun()

if "active_flow_card" not in st.session_state:
    default_c = dict(FLOW_CURATED_VAULT[0])
    default_c["flow_prompt"] = build_google_flow_image_prompt(default_c, default_c["flow_style"], default_c["palette"], get_persistent_handle())
    st.session_state["active_flow_card"] = default_c
    st.session_state["active_flow_src"] = "Curated Vault"

if not st.session_state.get("just_locked_cycle", False) and "active_flow_card" in st.session_state:
    card = st.session_state["active_flow_card"]
    default_style_key = next(iter(FLOW_VISUAL_STYLES.keys()))
    resolved_style = card.get("flow_style", default_style_key) if chosen_style == "AUTO" else chosen_style
    if resolved_style not in FLOW_VISUAL_STYLES:
        resolved_style = default_style_key
    resolved_pal = card.get("palette", "IMPERIAL_GOLD") if chosen_palette == "AUTO" else chosen_palette
    src_label = str(st.session_state.get("active_flow_src") or "Vault")
    style_label = FLOW_VISUAL_STYLES[resolved_style]["label"]
    st.caption(f"Source: `{src_label}` | Style: `{style_label}`")

    with st.expander("✏️ Customize Text Overlay & Scene Before Copying Flow Prompt", expanded=False):
        col_e1, col_e2 = st.columns([2, 1])
        with col_e1:
            ed_head = st.text_input("Image Headline Text", value=card.get("headline", ""))
            ed_sub = st.text_input("Image Supporting Line", value=card.get("subtext", ""))
        with col_e2:
            ed_auth = st.text_input("Leader / Attribution", value=card.get("author", ""))
            ed_handle = st.text_input("Subtle Watermark Handle", value=get_persistent_handle())
        ed_subj = st.text_area("Visual Subject & Scene", value=card.get("visual_subject", ""), height=75)

    edited_card_for_prompt = {
        **card,
        "headline": ed_head,
        "subtext": ed_sub,
        "author": ed_auth,
        "visual_subject": ed_subj
    }
    live_flow_prompt = build_google_flow_image_prompt(edited_card_for_prompt, resolved_style, resolved_pal, ed_handle)

    st.text_area("📋 Copy & Paste This Prompt Into Google Flow (Select 4:3 — Full-Bleed, Zero Borders)", live_flow_prompt, height=155)
    render_copy_btn("flow_pr", "COPY GOOGLE FLOW 4:3 IMAGE PROMPT", live_flow_prompt)

    # ---------------------------------------------------------
    # 8. STEP 2: UPLOAD FLOW IMAGE -> CROP WATERMARK & STAMP LOGO
    # ---------------------------------------------------------
    st.divider()
    st.markdown("### ✂️ 2. Upload 4:3 Google Flow Image, Crop Watermark & Stamp Logo")

    uploaded_flow_img = st.file_uploader("Upload your 4:3 image generated from Google Flow", type=["png", "jpg", "jpeg", "webp"], key=f"flow_up_{st.session_state.get('flow_cycle_id', 0)}")
    if uploaded_flow_img:
        with open(SAVED_FLOW_IMG_PATH, "wb") as sf:
            sf.write(uploaded_flow_img.read())

    col_cr1, col_cr2, col_cr3 = st.columns(3)
    with col_cr1:
        wm_crop_pct = st.slider("Bottom Watermark Crop %", min_value=0.0, max_value=15.0, value=8.0, step=0.5, help="Default 8.0% crops the bottom watermark cleanly; drag higher or lower as needed.")
        clean_corner_on = st.checkbox("✨ Extra Corner Blend", value=False, help="Optional extra corner blend if needed.")
    with col_cr2:
        logo_pos_choice = st.selectbox("Brand Logo Placement", ["Bottom-Right (Covers Sparkle)", "Top-Right", "Top-Left", "Bottom-Left", "None"])
    with col_cr3:
        logo_size_pct = st.slider("Logo Size %", min_value=6, max_value=20, value=10, step=1)

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ed_head).strip("_").lower() or "echoes_post"
    file_name = f"{next_d.replace('-', '')}_{slug}.png"

    if os.path.exists(SAVED_FLOW_IMG_PATH):
        raw_im = Image.open(SAVED_FLOW_IMG_PATH)
        final_im = process_uploaded_flow_image(
            raw_im,
            bottom_crop_pct=wm_crop_pct / 100.0,
            clean_br_corner=clean_corner_on,
            logo_path=find_active_logo_path(),
            logo_pos=logo_pos_choice,
            logo_scale_pct=logo_size_pct
        )
        st.image(final_im, caption=f"✓ Full-Bleed Master ({final_im.size[0]}×{final_im.size[1]} — No Artificial Borders)", use_container_width=True)

        col_dl1, col_dl2 = st.columns([3, 1])
        with col_dl1:
            out_buf = io.BytesIO()
            final_im.save(out_buf, format="PNG", quality=98)
            st.download_button(f"💾 Download Master Image ({file_name})", out_buf.getvalue(), file_name, "image/png", use_container_width=True)
        with col_dl2:
            if st.button("🗑️ Clear Image", use_container_width=True):
                try: os.remove(SAVED_FLOW_IMG_PATH)
                except Exception: pass
                st.rerun()
    else:
        st.info("👆 Generate your 4:3 image in Google Flow using the prompt above, then upload it here to trim the watermark, stamp your logo, and download.")

    # ---------------------------------------------------------
    # 9. STEP 3: ENGAGING STORY CAPTION, DISCUSSION QUESTION, EMOJIS & HASHTAGS
    # ---------------------------------------------------------
    st.divider()
    st.markdown("### 📝 3. Complete Meta Feed Metadata, Emojis & Hashtags")

    ed_ref_q = st.text_input("Comment-Triggering Reflection Question (Non-Bait)", value=card.get("reflection_prompt", "What is one hard lesson here that took you years to learn?"))
    hashtags_clean = card.get("tags", "#Mindset #LifeLessons #PersonalGrowth #SelfRespect #Discipline #Wisdom")

    feed_caption = (
        f"⚡ {ed_head.upper()} 🏛️\n\n"
        f"💡 {card.get('caption_story', '')}\n\n"
        f"💬 {ed_ref_q} 👇\n\n"
        f"🔖 Save this reminder for tough days, or share it with someone building their future.\n"
        f"✨ Follow {get_persistent_handle()} for daily clarity.\n\n"
        f"{hashtags_clean}"
    )
    st.text_area("1. Meta Feed Post Caption (Story + Open Question + Emojis)", feed_caption, height=195)
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
    # 10. DIRECT META COMPOSER & SCHEDULE LOCK
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
            "pillar": card.get("pillar", "SOVEREIGNTY"),
            "flow_style": resolved_style,
            "headline": ed_head,
            "file": file_name
        })
        if ed_head not in db.get("used_headlines", []):
            db.setdefault("used_headlines", []).append(ed_head)
        if resolved_style not in db.get("used_styles", []):
            db.setdefault("used_styles", []).append(resolved_style)
        db["last_date"] = d_str
        db["post_time"] = sched_time
        save_db(db)

        append_image_excel_tracker({
            "date": d_str,
            "time": sched_time,
            "pillar": card.get("pillar", ""),
            "flow_style": resolved_style,
            "headline": ed_head,
            "author": ed_auth,
            "file": file_name,
            "caption": feed_caption,
            "first_comment": first_comment
        })

        for stale_f in [ACTIVE_CARD_PATH, SAVED_FLOW_IMG_PATH]:
            if os.path.exists(stale_f):
                try: os.remove(stale_f)
                except Exception: pass
        st.session_state.pop("active_flow_card", None)
        st.session_state.pop("active_flow_src", None)
        st.session_state["flow_cycle_id"] = st.session_state.get("flow_cycle_id", 0) + 1
        st.session_state["just_locked_cycle"] = True
        st.session_state["img_banner"] = f"✓ Scheduled '{ed_head}' for {d_str} @ {sched_time} IST! Ready to generate your next prompt above."
        st.rerun()


# ---------------------------------------------------------
# 11. SCHEDULED QUEUE & EXCEL EXPORT
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
                    <div style="color: #94A3B8; font-size: 11px;">Style: {item.get('flow_style', 'MODERN_EDITORIAL_PHOTO')}</div>
                </div>
                <div style="color: #34D399; font-weight: 700; font-size: 11px;">● SCHEDULED</div>
            </div>
            """, unsafe_allow_html=True)
