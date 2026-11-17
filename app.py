import os, io, json, re, random, base64, requests
from datetime import datetime, timedelta, timezone, time as dt_time
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
API_KEY_FILE = os.path.join(DATA_DIR, "gemini_key.txt")
CHANNEL_HANDLE_FILE = os.path.join(DATA_DIR, "channel_handle.txt")
GUIDE_URL_FILE = os.path.join(DATA_DIR, "guide_url.txt")
EXCEL_IMAGE_TRACKER = os.path.join(DATA_DIR, "Echoes_Image_Content_Tracker.xlsx")

@st.cache_resource(show_spinner=False)
def ensure_studio_fonts():
    bold_p = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")
    reg_p = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
    serif_p = os.path.join(FONTS_DIR, "DejaVuSerif.ttf")
    urls = {
        bold_p: "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans-Bold.ttf",
        reg_p: "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf",
        serif_p: "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSerif.ttf",
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
    return bold_p, reg_p, serif_p

BOLD_FONT_PATH, REG_FONT_PATH, SERIF_FONT_PATH = ensure_studio_fonts()

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
    if "CHANNEL_HANDLE" in st.secrets:
        return str(st.secrets["CHANNEL_HANDLE"]).strip()
    if os.path.exists(CHANNEL_HANDLE_FILE):
        try:
            with open(CHANNEL_HANDLE_FILE, "r", encoding="utf-8") as f:
                val = f.read().strip()
                if val:
                    return val
        except Exception:
            pass
    return "@AJ-Echoes-of-Wisdom"

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
# 3. 5 MASS-MARKET PILLARS (TUNED FOR MEN 35-65+ & SHARES)
# ---------------------------------------------------------
PILLAR_DEFINITIONS = {
    "ALL": "🎲 Smart AI Rotation (All 5 Pillars)",
    "SOVEREIGNTY": "🛡️ Silent Power & Boundaries",
    "FINANCE": "⚖️ Financial Sovereignty & Control",
    "LEGACY": "🏛️ Father to Son: Legacy Counsel",
    "LONGEVITY": "⏳ Aging Well: Vitality After 40/60",
    "PARABLES": "🌲 Ancient Parables & Human Nature"
}

CONTENT_CARDS_VAULT = [
    # PILLAR 1: SILENT POWER & BOUNDARIES
    {
        "id": "IMG_UNGRASPABLE",
        "pillar": "SOVEREIGNTY",
        "category": "SOVEREIGNTY",
        "headline": "BECOME COMPLETELY UNGRASPABLE",
        "quote": "\"He who displays no edge cannot be blunted, disarming adversaries through impenetrable strategic emptiness.\"",
        "author": "LAO TZU",
        "reflection_prompt": "WHEN CHALLENGED PUBLICLY, WHAT HELPS YOU KEEP YOUR COMPOSURE?",
        "sub_prompt": "SHARE YOUR EXPERIENCE IN THE COMMENTS",
        "bg_scene": "Classical dark oil painting of turbulent cavalry battle in golden-brown chiaroscuro mist, dramatic clouds, museum canvas texture",
        "caption_story": "The loudest man in the room is always the easiest to read. When you refuse to broadcast your anger, your plans, or your insecurities, nobody can find a handle to pull you off balance.",
        "tags": "#Stoicism #EmotionalMastery #SelfControl #Mindset #LifeLessons"
    },
    {
        "id": "IMG_SILENT_EXIT",
        "pillar": "SOVEREIGNTY",
        "category": "BOUNDARIES",
        "headline": "NEVER ANNOUNCE YOUR DEPARTURE",
        "quote": "\"Withdraw your presence without spectacle. Explaining your worth to those who ignored it only prolongs your own captivity.\"",
        "author": "ANCIENT MAXIM",
        "reflection_prompt": "WHAT BOUNDARY TOOK YOU THE LONGEST TO ENFORCE IN LIFE?",
        "sub_prompt": "THOUGHTFUL REPLIES BUILD REAL PERSPECTIVE",
        "bg_scene": "Moody dark painting of a lone cloaked traveler walking across an ancient stone bridge into thick twilight fog, deep slate and gold tones",
        "caption_story": "Arguing for respect is a battle you have already lost. Mature strength does not slam doors or write long explanations—it simply closes the gate and redirects its energy where it is honored.",
        "tags": "#SelfRespect #Boundaries #StoicWisdom #Maturity #PersonalGrowth"
    },
    {
        "id": "IMG_TWO_ARROWS",
        "pillar": "SOVEREIGNTY",
        "category": "COMPOSURE",
        "headline": "DROP THE SECOND ARROW",
        "quote": "\"The first wound is struck by fate; the second is driven into your chest by your own refusal to let go.\"",
        "author": "ANCIENT PARABLE",
        "reflection_prompt": "HOW DO YOU STOP REPLAYING AN INSULT OR SETBACK IN YOUR MIND?",
        "sub_prompt": "SAVE THIS REMINDER FOR DIFFICULT DAYS",
        "bg_scene": "Dramatic classical chiaroscuro oil painting of a weathered bronze shield resting beside a stone archway under storm clouds",
        "caption_story": "Someone speaks carelessly, or a plan falls apart—that is the first arrow, and it is out of your hands. Replaying the moment for three sleepless nights is the second arrow, fired entirely by your own mind.",
        "tags": "#EmotionalIntelligence #Stoicism #MentalStrength #PeaceOfMind #Wisdom"
    },

    # PILLAR 2: FINANCIAL SOVEREIGNTY & CONTROL
    {
        "id": "IMG_SAVING_IS_CONTROL",
        "pillar": "FINANCE",
        "category": "FINANCIAL SOVEREIGNTY",
        "headline": "SAVING IS NOT FEAR. IT IS CONTROL.",
        "quote": "\"He who buys what he does not need will soon be forced to sell what he cannot afford to lose.\"",
        "author": "CATO THE ELDER",
        "reflection_prompt": "WHAT FINANCIAL LESSON DO YOU WISH YOU HAD LEARNED AT 25?",
        "sub_prompt": "SHARE ONE RULE THAT CHANGED YOUR FINANCES",
        "bg_scene": "Dark moody Renaissance still-life painting of a heavy iron-bound wooden chest, brass balance scale, and single beeswax candle on oak table",
        "caption_story": "Living to impress neighbors who do not pay your bills is quiet slavery. Every dollar you refuse to waste on empty status buys you the freedom to walk away from toxic jobs, bad deals, and disrespectful rooms.",
        "tags": "#FinancialWisdom #Discipline #Stoicism #WealthMindset #SelfReliance"
    },
    {
        "id": "IMG_SILENT_WEALTH",
        "pillar": "FINANCE",
        "category": "RESOURCE DISCIPLINE",
        "headline": "QUIET WEALTH BUYS FREEDOM",
        "quote": "\"True fortune is not measured by the luxuries you display, but by the emergencies that can no longer break your peace.\"",
        "author": "SENECA",
        "reflection_prompt": "DOES TRUE WEALTH MEAN MORE POSSESSIONS OR FEWER OBLIGATIONS?",
        "sub_prompt": "SHARE YOUR PERSPECTIVE BELOW",
        "bg_scene": "Atmospheric classical oil painting of an ancient stone harbor at dawn with a sturdy timber ship anchored in calm golden mist",
        "caption_story": "You do not feel the consequences of reckless spending on a sunny afternoon—you feel them when life tests your household. Build your reserve in silence while others perform for applause.",
        "tags": "#MoneyMindset #FinancialFreedom #StoicPhilosophy #LifeLessons #Discipline"
    },

    # PILLAR 3: FATHER TO SON / INTERGENERATIONAL LEGACY
    {
        "id": "IMG_FATHER_TO_SON_CRAFT",
        "pillar": "LEGACY",
        "category": "LEGACY COUNSEL",
        "headline": "SON, BUILD WHAT NO ONE CAN TAKE",
        "quote": "\"Luck fades with the weather, but character, skill, and self-command remain yours when every title is stripped away.\"",
        "author": "FATHER'S COUNSEL",
        "reflection_prompt": "WHAT IS THE SINGLE BEST PIECE OF ADVICE YOUR FATHER OR MENTOR GAVE YOU?",
        "sub_prompt": "SHARE IT FOR THE NEXT GENERATION",
        "bg_scene": "Warm Rembrandt-style oil painting of an elder master craftsman guiding a young apprentice over wooden drafting plans by lantern light",
        "caption_story": "If you want to build a life that endures, stop chasing shortcuts. Invest your twenties and thirties in mastering a real craft, keeping your word, and controlling your temper—those assets compound for decades.",
        "tags": "#FatherAndSon #Legacy #LifeAdvice #MenOfCharacter #Stoicism"
    },
    {
        "id": "IMG_CHOOSE_YOUR_CIRCLE",
        "pillar": "LEGACY",
        "category": "MENTORSHIP",
        "headline": "GUARD THE COMPANY YOU KEEP",
        "quote": "\"Associate with those who make you better, and welcome those whom you can elevate; for iron sharpens iron in silence.\"",
        "author": "SENECA",
        "reflection_prompt": "HOW DO YOU RECOGNIZE A TRULY LOYAL FRIEND AFTER YEARS OF EXPERIENCE?",
        "sub_prompt": "TAG OR SHARE WITH SOMEONE YOU TRUST",
        "bg_scene": "Classical dark oil painting of two armored Roman commanders standing beside a stone watchtower overlooking misty mountain ridges",
        "caption_story": "A man's trajectory is quietly shaped by the five voices he tolerates closest to his table. Step back from chronic complainers and surround yourself with people who respect duty, family, and honest labor.",
        "tags": "#Brotherhood #Loyalty #Wisdom #LifeLessons #PersonalGrowth"
    },

    # PILLAR 4: LONGEVITY, HEALTH & DIGNITY AFTER 40/60
    {
        "id": "IMG_STRENGTH_IN_LATER_YEARS",
        "pillar": "LONGEVITY",
        "category": "AGING WELL",
        "headline": "PROTECT YOUR STRENGTH FOR LATER YEARS",
        "quote": "\"It is a disgrace to grow old through sheer carelessness before seeing what manner of man you might become by training body and mind.\"",
        "author": "SOCRATES",
        "reflection_prompt": "WHICH DAILY HABIT HAS PROTECTED YOUR HEALTH AND ENERGY THE MOST?",
        "sub_prompt": "SHARE A HABIT WORTH KEEPING AFTER 40",
        "bg_scene": "Dramatic classical painting of a weathered elder standing tall on a sunlit alpine granite ridge at sunrise, deep atmospheric mist",
        "caption_story": "Your later years deserve strength, clarity, and independence—not regret. Daily walking, simple whole food, deep sleep, and refusing to carry bitter grudges will add life to your years.",
        "tags": "#HealthyAging #Longevity #MensHealth #StoicDiscipline #Vitality"
    },
    {
        "id": "IMG_GUARD_YOUR_PEACE_60",
        "pillar": "LONGEVITY",
        "category": "LONGEVITY & PEACE",
        "headline": "GUARD YOUR PEACE AS YOU AGE",
        "quote": "\"Nothing ages a man faster than carrying resentment for people who have already forgotten his name.\"",
        "author": "MARCUS AURELIUS",
        "reflection_prompt": "WHAT HAVE YOU LEARNED TO STOP WORRYING ABOUT AS YOU GOT OLDER?",
        "sub_prompt": "YOUR WISDOM HELPS YOUNGER READERS",
        "bg_scene": "Serene dark oil painting of an ancient olive grove beside a quiet stone villa under golden evening light",
        "caption_story": "After forty, energy becomes your most valuable currency. Stop spending it on pointless online debates, ungrateful relatives, or proving yourself to strangers. Guard your quiet mornings and your evening peace.",
        "tags": "#LifeAfter40 #PeaceOfMind #AgingGracefully #MarcusAurelius #Wisdom"
    },

    # PILLAR 5: ANCIENT PARABLES & HUMAN NATURE
    {
        "id": "IMG_ROOTS_MAKE_NO_NOISE",
        "pillar": "PARABLES",
        "category": "ANCIENT PARABLE",
        "headline": "THE NOISE IS NOT THE PROOF",
        "quote": "\"A falling tree crashes with thunder, yet an entire forest grows in total silence. Build your roots where no eye can see.\"",
        "author": "ANCIENT PROVERB",
        "reflection_prompt": "WHAT ARE YOU QUIETLY BUILDING RIGHT NOW WITHOUT ANNOUNCING IT?",
        "sub_prompt": "SAVE THIS IF YOU ARE IN A SEASON OF QUIET WORK",
        "bg_scene": "Moody atmospheric painting of ancient gnarled oak roots gripping mossy granite boulders in a misty deep forest",
        "caption_story": "Applause is cheap and temporary. Real transformation happens in the quiet hours when nobody is watching—when you keep your promises to yourself, refine your discipline, and let finished results speak.",
        "tags": "#WorkInSilence #Patience #StoicMindset #Discipline #Growth"
    },
    {
        "id": "IMG_GOOD_BAD_WORST_PEOPLE",
        "pillar": "PARABLES",
        "category": "HUMAN NATURE",
        "headline": "NEVER BLAME PEOPLE IN YOUR LIFE",
        "quote": "\"Good people bring happiness, difficult people bring experience, and the worst people leave lessons that sharpen your discernment forever.\"",
        "author": "TIMELESS LAW",
        "reflection_prompt": "DID YOUR BIGGEST GROWTH COME FROM AN EASY SEASON OR A HARD LESSON?",
        "sub_prompt": "SHARE YOUR PERSPECTIVE IN THE COMMENTS",
        "bg_scene": "Classical chiaroscuro oil painting of a stone compass and weathered parchment map illuminated by warm amber light",
        "caption_story": "Every person who crosses your path serves a purpose. Instead of growing bitter over betrayal, extract the lesson, tighten your standards, and move forward wiser than before.",
        "tags": "#HumanNature #LifeLessons #Discernment #Wisdom #Mindset"
    }
]

# ---------------------------------------------------------
# 4. PROCEDURAL & CURATED DARK BACKGROUND ENGINE
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

    for _ in range(18):
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

    target_ratio = 1080.0 / 1350.0  # 4:5 Feed Portrait
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
# 5. CHISELED 4:5 FEED CARD COMPOSITOR
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

def render_4x5_master_card(bg_image, card_data, accent_theme="IMPERIAL_GOLD"):
    W, H = 1080, 1350
    canvas = bg_image.copy().convert("RGBA")
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # Top & bottom vignette gradients for crisp legibility
    for y in range(260):
        a = int(155 * (1 - y / 260.0))
        odraw.line([(0, y), (W, y)], fill=(6, 8, 12, a))
    for y in range(H - 360, H):
        a = int(215 * ((y - (H - 360)) / 360.0))
        odraw.line([(0, y), (W, y)], fill=(6, 8, 12, a))

    # Bottom reflection banner strip (non-bait discussion bar)
    strip_top = H - 175
    odraw.rectangle([(0, strip_top), (W, H)], fill=(8, 11, 17, 235))

    accent_map = {
        "IMPERIAL_GOLD": (235, 192, 96, 255),
        "GLACIAL_ICE":   (110, 225, 245, 255),
        "FORGE_AMBER":   (245, 162, 72, 255),
    }
    gold = accent_map.get(accent_theme, accent_map["IMPERIAL_GOLD"])
    white = (248, 250, 252, 255)
    soft_gray = (203, 213, 225, 255)

    odraw.line([(0, strip_top), (W, strip_top)], fill=(gold[0], gold[1], gold[2], 140), width=2)
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    f_brand = load_font(REG_FONT_PATH, 20)
    f_cat = load_font(BOLD_FONT_PATH, 22)
    f_head = load_font(BOLD_FONT_PATH, 68)
    f_quote = load_font(SERIF_FONT_PATH, 34)
    f_auth = load_font(REG_FONT_PATH, 22)
    f_ref_q = load_font(REG_FONT_PATH, 20)
    f_ref_sub = load_font(BOLD_FONT_PATH, 22)

    # 1. Top Brand Header
    brand_txt = "E C H O E S   O F   W I S D O M"
    bw = draw.textbbox((0, 0), brand_txt, font=f_brand)[2]
    draw.text(((W - bw) // 2, 72), brand_txt, font=f_brand, fill=gold)
    draw.line([((W - bw) // 2, 106), ((W + bw) // 2, 106)], fill=(gold[0], gold[1], gold[2], 130), width=1)

    # 2. Category Pill with Flanking Gold Rules
    cat_txt = card_data.get("category", "SOVEREIGNTY").upper()
    cw = draw.textbbox((0, 0), cat_txt, font=f_cat)[2]
    cx = (W - cw) // 2
    cy = 188
    draw.text((cx, cy), cat_txt, font=f_cat, fill=gold)
    draw.line([(cx - 58, cy + 14), (cx - 16, cy + 14)], fill=gold, width=3)
    draw.line([(cx + cw + 16, cy + 14), (cx + cw + 58, cy + 14)], fill=gold, width=3)

    # 3. Dual-Pass Chiseled Relief Headline
    head_lines = wrap_text_lines(draw, card_data.get("headline", "").upper(), f_head, 880)
    curr_y = 295 if len(head_lines) >= 3 else 335
    for line in head_lines[:4]:
        lw = draw.textbbox((0, 0), line, font=f_head)[2]
        lx = (W - lw) // 2
        draw.text((lx + 4, curr_y + 5), line, font=f_head, fill=(0, 0, 0, 210))
        draw.text((lx - 1, curr_y - 1), line, font=f_head, fill=(255, 255, 255, 90))
        draw.text((lx, curr_y), line, font=f_head, fill=white)
        curr_y += 84

    # 4. Center Accent Divider
    curr_y += 18
    draw.line([(W // 2 - 140, curr_y), (W // 2 + 140, curr_y)], fill=gold, width=3)
    curr_y += 38

    # 5. Parable / Insight Body Text
    quote_lines = wrap_text_lines(draw, card_data.get("quote", ""), f_quote, 860)
    for qline in quote_lines[:5]:
        qw = draw.textbbox((0, 0), qline, font=f_quote)[2]
        qx = (W - qw) // 2
        draw.text((qx + 2, curr_y + 3), qline, font=f_quote, fill=(0, 0, 0, 210))
        draw.text((qx, curr_y), qline, font=f_quote, fill=white)
        curr_y += 48

    # 6. Attribution
    curr_y += 26
    auth_txt = card_data.get("author", "ANCIENT MAXIM").upper()
    aw = draw.textbbox((0, 0), auth_txt, font=f_auth)[2]
    ax = (W - aw) // 2
    draw.text((ax, curr_y), auth_txt, font=f_auth, fill=gold)
    draw.line([(ax - 44, curr_y + 13), (ax - 14, curr_y + 13)], fill=gold, width=2)
    draw.line([(ax + aw + 14, curr_y + 13), (ax + aw + 44, curr_y + 13)], fill=gold, width=2)

    # 7. Bottom Non-Bait Reflection Strip
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

# ---------------------------------------------------------
# 6. AI SYNTHESIS ENGINE (NON-BAIT, MEN 35-65+ TUNED)
# ---------------------------------------------------------
def synthesize_ai_card(raw_key, pillar_choice="ALL"):
    clean_k = raw_key.strip().strip('"').strip("'")
    used_heads = db.get("used_headlines", [])[-35:]
    available_cards = [
        c for c in CONTENT_CARDS_VAULT
        if (pillar_choice == "ALL" or c["pillar"] == pillar_choice) and c["headline"] not in used_heads
    ]
    if not available_cards:
        available_cards = [c for c in CONTENT_CARDS_VAULT if (pillar_choice == "ALL" or c["pillar"] == pillar_choice)] or CONTENT_CARDS_VAULT

    base_card = random.choice(available_cards)

    if not clean_k:
        return base_card, "Curated Vault (Offline Ready)"

    pillar_label = PILLAR_DEFINITIONS.get(base_card["pillar"], "Silent Power")
    prompt = (
        f"You are Creative Director for 'Echoes of Wisdom', a high-authority Facebook & Instagram page whose core audience is men aged 35-65+ in the US, UK, Canada, and Australia.\n"
        f"TARGET PILLAR: {pillar_label}\n"
        f"REFERENCE CONCEPT: {base_card['headline']} — {base_card['quote']}\n"
        f"FORBIDDEN HEADLINES (DO NOT REPEAT): {', '.join(used_heads) if used_heads else 'None'}\n"
        f"STRICT RULES:\n"
        f"1. Create a completely fresh, original 4:5 Feed Card on the target pillar.\n"
        f"2. HEADLINE: 3 to 5 punchy uppercase words (max 34 characters). No clichés.\n"
        f"3. QUOTE: 18 to 28 words of profound, grounded wisdom or a micro-parable that speaks directly to mature men (financial sovereignty, father-to-son legacy, health/peace after 40, or silent boundaries).\n"
        f"4. REFLECTION_PROMPT: An authentic, open-ended question (max 70 characters) that invites a thoughtful sentence in the comments. STRICTLY NEVER use engagement bait like 'Drop 1 or 2', 'Comment YES', or '1 vs 2'.\n"
        f"5. CAPTION_STORY: A 3-sentence micro-parable or hard truth written in crisp international English.\n"
        f"6. BG_SCENE: A vivid 9:16/4:5 classical oil painting or moody cinematic scene description (no text in image).\n"
        f"OUTPUT STRICT JSON ONLY:\n"
        "{\n"
        f'  "pillar": "{base_card["pillar"]}",\n'
        '  "category": "1-2 WORD UPPERCASE CATEGORY",\n'
        '  "headline": "3-5 UPPERCASE WORDS",\n'
        '  "quote": "\\"Your 18-28 word quote or micro-parable.\\"",\n'
        '  "author": "HISTORICAL AUTHOR OR ANCIENT MAXIM",\n'
        '  "reflection_prompt": "OPEN-ENDED QUESTION IN UPPERCASE",\n'
        '  "sub_prompt": "SHARE YOUR PERSPECTIVE IN THE COMMENTS",\n'
        '  "bg_scene": "Classical dark chiaroscuro oil painting scene description...",\n'
        '  "caption_story": "Three compelling sentences expanding the lesson for mature readers.",\n'
        '  "tags": "#Stoicism #LifeLessons #Mindset #Wisdom #PersonalGrowth"\n'
        "}"
    )

    try:
        client = get_fast_gemini_client(clean_k)
        for m in ["gemini-3.8-flash", "gemini-3.8-flash-lite"]:
            try:
                try:
                    cfg = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.88,
                        max_output_tokens=900,
                        thinking_config=types.ThinkingConfig(thinking_level="MINIMAL")
                    )
                except Exception:
                    cfg = types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.88,
                        max_output_tokens=900
                    )
                res = client.models.generate_content(model=m, contents=prompt, config=cfg)
                raw = res.text.strip()
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                parsed = json.loads(match.group(0) if match else raw)
                if isinstance(parsed, dict) and "headline" in parsed and "quote" in parsed:
                    parsed["id"] = f"AI_{datetime.now().strftime('%H%M%S')}"
                    return parsed, "Gemini 3.8 Turbo AI"
            except Exception:
                continue
    except Exception:
        pass

    return base_card, "Curated Vault"

def append_image_excel_tracker(entry):
    if not OPENPYXL_AVAILABLE:
        return False
    headers = [
        "Post ID", "Target Date", "Time (IST)", "Pillar", "Category",
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

# ---------------------------------------------------------
# 7. STUDIO HEADER & CREDENTIALS
# ---------------------------------------------------------
next_d = get_next_post_date()
st.markdown("""
<div style="font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: #F8FAFC; margin-bottom: 8px;">
    🏛️ ECHOES IMAGE STUDIO <span style="font-size: 13px; color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-weight: 600;">v3.4 // 4:5 VIRAL PARABLE & LEGACY ENGINE</span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="margin-bottom: 14px;">
    <span class="badge badge-green">● 4:5 FEED MASTER (1080×1350)</span>
    <span class="badge badge-purple">🎯 MEN 35-65+ PILLARS</span>
    <span class="badge badge-blue">🛡️ NON-BAIT ENGAGEMENT</span>
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
        uh = st.text_input("Brand Handle", value=get_persistent_handle())
        if uh != get_persistent_handle():
            save_persistent_handle(uh)
    with c_h2:
        ug = st.text_input("Clean Guide URL (First Comment)", value=get_persistent_guide_url())
        if ug != get_persistent_guide_url():
            save_persistent_guide_url(ug)

# ---------------------------------------------------------
# 8. CARD SYNTHESIS CONTROLS
# ---------------------------------------------------------
st.markdown("### ⚡ 1. Synthesize 4:5 Feed Card")
col_p1, col_p2 = st.columns([2, 1])
with col_p1:
    chosen_pillar = st.selectbox(
        "Audience Content Pillar (Tuned for Men 35-65+)",
        list(PILLAR_DEFINITIONS.keys()),
        format_func=lambda k: PILLAR_DEFINITIONS[k]
    )
with col_p2:
    accent_choice = st.selectbox(
        "Gold / Accent Palette",
        ["IMPERIAL_GOLD", "GLACIAL_ICE", "FORGE_AMBER"],
        format_func=lambda k: {"IMPERIAL_GOLD": "👑 Imperial Gold", "GLACIAL_ICE": "❄️ Glacial Cyan", "FORGE_AMBER": "🔥 Forge Amber"}[k]
    )

if st.button("🚀 Synthesize Fresh 4:5 Parable Card", type="primary"):
    with st.spinner("⚡ Synthesizing high-share parable & non-bait discussion prompt..."):
        card, src = synthesize_ai_card(get_persistent_api_key(), chosen_pillar)
        st.session_state["active_card"] = card
        st.session_state["active_card_src"] = src
        st.rerun()

if "active_card" not in st.session_state:
    st.session_state["active_card"] = CONTENT_CARDS_VAULT[0]
    st.session_state["active_card_src"] = "Curated Vault"

card = st.session_state["active_card"]
st.caption(f"Source: `{st.session_state.get('active_card_src', 'Vault')}` | Pillar: `{PILLAR_DEFINITIONS.get(card.get('pillar', 'SOVEREIGNTY'))}`")

# ---------------------------------------------------------
# 9. BACKGROUND ARTWORK & LIVE EDITOR
# ---------------------------------------------------------
st.markdown("### 🎨 2. Background Artwork & Watermark Crop")
st.text_area("AI Image Prompt (Copy for Google Flow / Imagen if generating custom art)", card.get("bg_scene", ""), height=68)
render_copy("bg_pr", "COPY ARTWORK PROMPT", card.get("bg_scene", ""))

col_bg1, col_bg2, col_bg3 = st.columns([2, 1, 1])
with col_bg1:
    uploaded_bg = st.file_uploader("Upload Custom Artwork (Optional - auto-generates dark canvas if empty)", type=["jpg", "jpeg", "png", "webp"])
with col_bg2:
    wm_crop_pct = st.slider("Bottom Watermark Crop %", min_value=0.0, max_value=15.0, value=6.5, step=0.5)
with col_bg3:
    bg_darkness = st.slider("Backdrop Brightness", min_value=0.25, max_value=0.85, value=0.52, step=0.03)

st.markdown("### ✍️ 3. Fine-Tune Card Typography")
col_t1, col_t2 = st.columns([1, 2])
with col_t1:
    ed_cat = st.text_input("Category Pill", value=card.get("category", "SOVEREIGNTY"))
    ed_auth = st.text_input("Attribution", value=card.get("author", "ANCIENT MAXIM"))
with col_t2:
    ed_head = st.text_input("Main Chiseled Headline", value=card.get("headline", ""))
    ed_quote = st.text_area("Parable / Quote Body", value=card.get("quote", ""), height=85)

col_r1, col_r2 = st.columns([2, 1])
with col_r1:
    ed_ref_q = st.text_input("Bottom Reflection Question (Non-Bait)", value=card.get("reflection_prompt", ""))
with col_r2:
    ed_ref_sub = st.text_input("Bottom Action Line", value=card.get("sub_prompt", "SHARE YOUR PERSPECTIVE IN THE COMMENTS"))

edited_card = {
    **card,
    "category": ed_cat,
    "headline": ed_head,
    "quote": ed_quote,
    "author": ed_auth,
    "reflection_prompt": ed_ref_q,
    "sub_prompt": ed_ref_sub,
}

# Render 1080x1350 Master Image
if uploaded_bg:
    raw_bg = Image.open(uploaded_bg)
    prepped_bg = crop_and_prep_background(raw_bg, bottom_crop_pct=wm_crop_pct / 100.0, darken_factor=bg_darkness)
else:
    tone_key = "GOLD" if accent_choice == "IMPERIAL_GOLD" else ("ICE" if accent_choice == "GLACIAL_ICE" else "AMBER")
    proc_bg = create_atmospheric_canvas(1080, 1350, seed_str=ed_head, tone=tone_key)
    prepped_bg = ImageEnhance.Brightness(proc_bg).enhance(bg_darkness / 0.52)

final_img = render_4x5_master_card(prepped_bg, edited_card, accent_theme=accent_choice)

st.markdown("### 🖼️ 4. Master 4:5 Preview & Export")
st.image(final_img, caption="1080×1350 (4:5 Feed Portrait — Chiseled Relief & Non-Bait Reflection Strip)", use_container_width=True)

slug = re.sub(r"[^a-zA-Z0-9]+", "_", ed_head).strip("_").lower() or "echoes_card"
file_name = f"{next_d.replace('-', '')}_{slug}.jpg"
img_buf = io.BytesIO()
final_img.save(img_buf, format="JPEG", quality=95)
st.download_button(f"💾 Download Master 4:5 Image ({file_name})", img_buf.getvalue(), file_name, "image/jpeg")

# ---------------------------------------------------------
# 10. NON-BAIT FEED CAPTION & FIRST COMMENT
# ---------------------------------------------------------
st.divider()
st.markdown("### 📝 5. Non-Bait Meta Feed Caption & First Comment")

feed_caption = (
    f"{ed_head.title()}\n\n"
    f"{card.get('caption_story', '')}\n\n"
    f"{ed_ref_q.capitalize()}\n\n"
    f"Save this reminder for difficult days, or share it with someone building their future.\n\n"
    f"• Follow {get_persistent_handle()} for timeless clarity.\n\n"
    f"{card.get('tags', '#Stoicism #LifeLessons #Mindset #Wisdom #PersonalGrowth')}"
)
st.text_area("1. Meta Feed Post Caption (Zero Engagement Bait)", feed_caption, height=185)
render_copy_btn("feed_cap", "COPY FEED CAPTION", feed_caption)

first_comment = (
    f"🏛️ Want a structured daily system to build emotional composure and mental discipline?\n\n"
    f"Explore The 30-Day Stoic Emotional Mastery Guide & Workbook here:\n"
    f"{get_persistent_guide_url()}\n"
    f"(Use code FIRST50 at checkout)"
)
st.text_area("2. Pinned First Comment (Clean Guide Link)", first_comment, height=115)
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
        "category": ed_cat,
        "headline": ed_head,
        "author": ed_auth,
        "file": file_name,
        "caption": feed_caption,
        "first_comment": first_comment
    })

    st.session_state["img_banner"] = f"✓ Scheduled '{ed_head}' for {d_str} @ {sched_time} IST!"
    st.rerun()

# ---------------------------------------------------------
# 12. SCHEDULED QUEUE VIEWER
# ---------------------------------------------------------
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
                </div>
                <div style="color: #34D399; font-weight: 700; font-size: 11px;">● SCHEDULED</div>
            </div>
            """, unsafe_allow_html=True)
