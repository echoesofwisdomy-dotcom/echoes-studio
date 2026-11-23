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
API_KEY_FILE = os.path.join(DATA_DIR, "gemini_key.txt")
CHANNEL_HANDLE_FILE = os.path.join(DATA_DIR, "meta_handle.txt")
GUIDE_URL_FILE = os.path.join(DATA_DIR, "guide_url.txt")
EXCEL_IMAGE_TRACKER = os.path.join(DATA_DIR, "Echoes_Image_Content_Tracker.xlsx")

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
# 3. 8 GOOGLE FLOW VISUAL STYLES, 6 PALETTES & LEADER PRINCIPLES
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
    "CLASSIC_OIL_RELIEF": {
        "label": "🏛️ Classical Oil Painting + Gold Serif Typography",
        "typo_spec": "bold chiseled gold serif typography centered in the upper third with subtle dark drop shadow and thin horizontal gold divider lines",
        "art_spec": "museum-grade chiaroscuro oil painting with dramatic golden-hour rim lighting, rich shadows, and fine canvas texture"
    },
    "MODERN_EDITORIAL_PHOTO": {
        "label": "🏙️ Modern Lifestyle Photo + Clean Sans-Serif Overlay",
        "typo_spec": "clean ultra-bold modern white and emerald-green sans-serif typography arranged in the upper-left negative space with crisp legibility",
        "art_spec": "photorealistic 35mm editorial lifestyle photograph in natural window light (modern apartment, quiet cafe desk, or dusk street) with shallow depth of field"
    },
    "WARM_PARCHMENT_PORTRAIT": {
        "label": "📜 Warm Parchment + Crimson Serif & Etched Portrait",
        "typo_spec": "refined crimson-red and charcoal editorial serif typography printed cleanly on warm cream textured parchment paper in the upper half",
        "art_spec": "detailed vintage engraved studio portrait of a wise thinker or mentor in the lower half on warm cream parchment background"
    },
    "DARK_MINIMAL_TYPO": {
        "label": "✍️ Minimal Obsidian Poster + Highlighted Key Words",
        "typo_spec": "high-contrast editorial serif typography on a matte obsidian-black background with thin geometric corner brackets and key power words highlighted in glowing gold",
        "art_spec": "minimalist dark charcoal studio backdrop with subtle radial rim light, faint geometric lines, and zero visual clutter"
    },
    "MONOCHROME_GRIT_SCENE": {
        "label": "🖤 Monochrome Documentary Scene + Bold White & Red Text",
        "typo_spec": "bold condensed white sans-serif typography with a single vivid crimson-red accent word, positioned cleanly in open sky/shadow space",
        "art_spec": "stark high-contrast black-and-white 35mm documentary photography with dramatic mist, natural film grain, and moody silhouettes"
    },
    "STORYBOOK_WARM_ILLUSTRATION": {
        "label": "💛 Warm Hand-Painted Art + Highlighted Lead-In Banner",
        "typo_spec": "warm cream top header with a yellow-gold marker highlight behind the opening phrase and crisp dark serif quote text above the illustration",
        "art_spec": "expressive warm hand-painted storybook illustration of a peaceful traveler in golden rain or sunlit hills with rich color harmony"
    },
    "SACRED_GEOMETRY_MYTHIC": {
        "label": "🔺 Sacred Geometry Emblem + Symbolic Silhouette",
        "typo_spec": "spaced uppercase typewriter-monospace silver-white typography framed between a geometric compass/triangle emblem at the top and a minimal horizon line at the bottom",
        "art_spec": "moody dark slate symbolic artwork featuring a lone figure casting a poised lion shadow or standing at a misty fork in the road"
    },
    "NUMBERED_CHECKLIST_POSTER": {
        "label": "📋 Clean 5-Point Behavioral Checklist Poster",
        "typo_spec": "bold uppercase header with a thin gold underline followed by 5 cleanly aligned numbered points (1 to 5) with circular gold number badges on a dark textured slate background",
        "art_spec": "subtle dark architectural stone and soft volumetric light background behind clean structured typography"
    }
}

COLOR_PALETTES = {
    "IMPERIAL_GOLD":  {"label": "👑 Imperial Gold & Obsidian",   "desc": "radiant imperial gold and crisp ivory-white lettering against deep obsidian shadows"},
    "GLACIAL_ICE":    {"label": "❄️ Glacial Cyan & Steel",       "desc": "frost glacial cyan and pure white lettering against cool steel-blue shadows"},
    "FORGE_AMBER":    {"label": "🔥 Molten Amber & Charcoal",    "desc": "molten forge amber-orange and warm cream lettering against dark charcoal"},
    "CRIMSON_IVORY":  {"label": "🩸 Deep Crimson & Warm Cream",  "desc": "deep editorial crimson and charcoal-black ink on warm cream parchment"},
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
        "reflection_prompt": "What is one money habit that gave you real peace of mind?",
        "caption_story": "Sympathy never covers a mortgage, and obligation never builds security. Every dollar you refuse to waste on empty status buys your independence when life tests your household.",
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
        "visual_subject": "Detailed vintage engraved studio portrait of a thoughtful nineteenth-century statesman with weathered features and calm resolve in the lower half on warm cream parchment paper",
        "reflection_prompt": "Where has extra preparation saved you from unnecessary stress?",
        "caption_story": "Rushing into hard decisions without preparation creates avoidable mistakes. Quiet planning turns steady effort into real leverage.",
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
        "reflection_prompt": "How do you stop yourself from reacting in the heat of the moment?",
        "caption_story": "Even under intense pressure, you still own the space between what happens and how you respond. Guard that space fiercely.",
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
        "caption_story": "Credit belongs to the person actually doing the work—not the spectator watching safely from the bleachers. Keep your eyes on your own standard.",
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
        "visual_subject": "Warm hand-painted storybook illustration of an older traveler sitting peacefully on a sunlit mountain ridge overlooking a calm valley at golden hour",
        "reflection_prompt": "What old grudge or worry are you glad you finally left behind?",
        "caption_story": "Carrying bitterness ages your spirit while the other person sleeps peacefully. Forgive for your own freedom and lighten your load.",
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
        "reflection_prompt": "Which of these five moments is hardest for you to hold silence?",
        "caption_story": "Silence is not weakness when you hold composure—it is leverage. A single measured pause can protect a relationship, a deal, or your peace of mind.",
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
        "visual_subject": "Classical chiaroscuro oil painting of a master woodworker guiding an apprentice over precision hand tools by warm lantern light in a quiet timber workshop",
        "reflection_prompt": "What one skill has paid you back across every stage of life?",
        "caption_story": "Dabbling in ten directions produces shallow results. Going deep on one craft builds the discipline that transfers to everything else you touch.",
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
        "reflection_prompt": "What is one mistake you avoided that paid off years later?",
        "caption_story": "You do not need to be brilliant every day. Avoiding impulse debt, toxic partnerships, and impatience puts you ahead of almost everyone over ten years.",
        "tags": "#CharlieMunger #FinancialWisdom #Discipline #Mindset #InvestingInSelf"
    }
]

# ---------------------------------------------------------
# 4. GOOGLE FLOW PROMPT ARCHITECT (4:5 FEED MASTER)
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
        f"[4:5 vertical 1080x1350 social media feed graphic] {style_meta['art_spec']}. "
        f"SUBJECT & SCENE: {subject}. "
        f"TYPOGRAPHY & LAYOUT: {style_meta['typo_spec']}, rendered in {pal_meta['desc']}. "
        f"The main headline reads verbatim: \"{headline}\".{sub_clause}{auth_clause} "
        f"In the bottom margin is a small, clean, subtle watermark reading \"{handle_str}\". "
        f"COMPOSITION & QUALITY: Balanced 4:5 editorial framing with generous breathing room around all text so every word is spelled accurately and razor-sharp, no garbled letters, no text overlapping faces, strictly two arms per person, photorealistic 8k."
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
    resolved_style = base.get("flow_style", "MODERN_EDITORIAL_PHOTO") if flow_style_choice == "AUTO" else flow_style_choice
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
        f"You are Executive Creative Director for 'Echoes of Wisdom' (Facebook & Instagram 4:5 Feed Posts for men aged 35-65+ in US, UK, Canada, Australia).\n"
        f"TARGET PILLAR: {pillar_label}\n"
        f"VISUAL FORMAT FOR GOOGLE FLOW: {style_meta['label']} — {style_meta['art_spec']}\n"
        f"TYPOGRAPHY STYLE FOR GOOGLE FLOW: {style_meta['typo_spec']} in {pal_meta['desc']}\n"
        f"LEADER / THINKER PRINCIPLE: {leader_pick['leader']} ({leader_pick['era']}) — {leader_pick['principle']}\n"
        f"FORBIDDEN HEADLINES: {', '.join(used_heads) if used_heads else 'None'}\n"
        f"STRICT RULES:\n"
        f"1. Create a fresh, thought-provoking, share-worthy 4:5 feed post inspired by {leader_pick['leader']} or a sharp modern-vs-ancient life insight.\n"
        f"2. HEADLINE: 4 to 10 crisp, punchy words to render on the image (easy for Google Flow to spell accurately).\n"
        f"3. SUBTEXT: 1 short supporting sentence (6 to 14 words) or 5 ultra-short numbered items if using a checklist style.\n"
        f"4. VISUAL_SUBJECT: Vivid scene description (alternate between modern everyday realism like sunlit city apartment, coffee desk, rainy dusk street and classic/ancient scenes).\n"
        f"5. REFLECTION_PROMPT: Authentic, open-ended question inviting a real comment (ZERO engagement bait like 'Drop 1 or 2' or 'Comment YES').\n"
        f"6. CAPTION_STORY: 3 compelling sentences expanding the insight.\n"
        f"OUTPUT STRICT JSON ONLY:\n"
        "{\n"
        f'  "pillar": "{base["pillar"]}",\n'
        f'  "flow_style": "{resolved_style}",\n'
        f'  "palette": "{resolved_pal}",\n'
        '  "headline": "Punchy headline for image text overlay",\n'
        '  "subtext": "Short supporting line for image text overlay",\n'
        f'  "author": "{leader_pick["leader"]}",\n'
        '  "visual_subject": "Detailed photorealistic or painterly subject & setting description...",\n'
        '  "reflection_prompt": "Open-ended question for comments?",\n'
        '  "caption_story": "Three compelling sentences expanding the lesson.",\n'
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
# 5. WATERMARK CROPPER & 4:5 / 9:16 EXPORT ENGINE
# ---------------------------------------------------------
def process_uploaded_flow_image(pil_img, bottom_crop_pct=0.065, target_ratio_mode="4:5 Feed Portrait (1080×1350)", sharpness_boost=1.05, contrast_boost=1.04):
    im = pil_img.convert("RGB")
    w, h = im.size
    if bottom_crop_pct > 0:
        new_h = int(h * (1.0 - bottom_crop_pct))
        im = im.crop((0, 0, w, max(100, new_h)))
        w, h = im.size

    if "9:16" in target_ratio_mode:
        target_w, target_h = 1080, 1920
    elif "1:1" in target_ratio_mode:
        target_w, target_h = 1080, 1080
    else:
        target_w, target_h = 1080, 1350

    target_aspect = target_w / float(target_h)
    curr_aspect = w / float(h)

    if curr_aspect > target_aspect:
        crop_w = int(h * target_aspect)
        x0 = (w - crop_w) // 2
        im = im.crop((x0, 0, x0 + crop_w, h))
    else:
        crop_h = int(w / target_aspect)
        y0 = max(0, (h - crop_h) // 4)
        im = im.crop((0, y0, w, y0 + crop_h))

    im = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
    if contrast_boost != 1.0:
        im = ImageEnhance.Contrast(im).enhance(contrast_boost)
    if sharpness_boost != 1.0:
        im = ImageEnhance.Sharpness(im).enhance(sharpness_boost)
    return im

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

if "active_flow_card" not in st.session_state and os.path.exists(ACTIVE_CARD_PATH):
    try:
        with open(ACTIVE_CARD_PATH, "r", encoding="utf-8") as af:
            saved_ac = json.load(af)
            if isinstance(saved_ac, dict) and "card" in saved_ac:
                st.session_state["active_flow_card"] = saved_ac["card"]
                st.session_state["active_flow_src"] = saved_ac.get("src", "Saved Prompt")
    except Exception:
        pass

# ---------------------------------------------------------
# 6. STUDIO HEADER & CREDENTIALS
# ---------------------------------------------------------
next_d = get_next_post_date()
st.markdown("""
<div style="font-size: 24px; font-weight: 800; letter-spacing: -0.02em; color: #F8FAFC; margin-bottom: 8px;">
    🏛️ ECHOES FLOW IMAGE STUDIO <span style="font-size: 13px; color: #38BDF8; font-family: 'JetBrains Mono', monospace; font-weight: 600;">v4.1 // GOOGLE FLOW PROMPT ARCHITECT, WATERMARK CROPPER & METADATA SUITE</span>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="margin-bottom: 14px;">
    <span class="badge badge-green">● GOOGLE FLOW 4:5 PROMPTS</span>
    <span class="badge badge-purple">🏛️ 15+ LEADERS & THINKERS</span>
    <span class="badge badge-blue">✂️ WATERMARK CROPPER</span>
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
    with st.expander(f"📦 RESTORE PREVIOUS PROMPT ({len(vault_hist)} SAVED IN VAULT)", expanded=False):
        v_labels = [f"🖼️ {v.get('headline','Prompt')} — {v.get('author','')} ({v.get('flow_style','')})" for v in vault_hist]
        v_idx = st.selectbox("Select Saved Prompt", range(len(vault_hist)), format_func=lambda i: v_labels[i], key="img_vault_sel")
        if st.button("🔄 Restore Selected Prompt", key="img_vault_btn"):
            st.session_state["active_flow_card"] = vault_hist[v_idx]
            st.session_state["active_flow_src"] = "Saved Vault"
            save_active_card_to_disk(vault_hist[v_idx], "Saved Vault")
            st.rerun()

# ---------------------------------------------------------
# 7. STEP 1: GENERATE GOOGLE FLOW IMAGE + TEXT OVERLAY PROMPT
# ---------------------------------------------------------
st.markdown("### ⚡ 1. Generate Google Flow Image + Typography Prompt")
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
    if st.button("🚀 Generate Fresh Flow Image Prompt", type="primary", use_container_width=True):
        with st.spinner("⚡ Crafting high-detail Google Flow prompt with embedded typography & leader wisdom..."):
            card, src = synthesize_flow_card_package(get_persistent_api_key(), chosen_pillar, chosen_style, chosen_palette)
            st.session_state["active_flow_card"] = card
            st.session_state["active_flow_src"] = src
            save_to_card_vault_history(card)
            save_active_card_to_disk(card, src)
            st.rerun()
with col_btn2:
    if st.button("🔄 Discard & New Prompt", use_container_width=True):
        with st.spinner("⚡ Generating a completely different leader, format & style..."):
            card, src = synthesize_flow_card_package(get_persistent_api_key(), "ALL", "AUTO", "AUTO")
            st.session_state["active_flow_card"] = card
            st.session_state["active_flow_src"] = src
            save_to_card_vault_history(card)
            save_active_card_to_disk(card, src)
            st.rerun()

if "active_flow_card" not in st.session_state:
    default_c = dict(FLOW_CURATED_VAULT[0])
    default_c["flow_prompt"] = build_google_flow_image_prompt(default_c, default_c["flow_style"], default_c["palette"], get_persistent_handle())
    st.session_state["active_flow_card"] = default_c
    st.session_state["active_flow_src"] = "Curated Vault"

card = st.session_state["active_flow_card"]
resolved_style = card.get("flow_style", "MODERN_EDITORIAL_PHOTO") if chosen_style == "AUTO" else chosen_style
resolved_pal = card.get("palette", "IMPERIAL_GOLD") if chosen_palette == "AUTO" else chosen_palette
st.caption(f"Source: `{st.session_state.get('active_flow_src', 'Vault')}` | Style: `{FLOW_VISUAL_STYLES.get(resolved_style, FLOW_VISUAL_STYLES['MODERN_EDITORIAL_PHOTO'])['label']}`")

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

st.text_area("📋 Copy & Paste This Prompt Into Google Flow / Imagen (Includes Artwork + Text Overlay)", live_flow_prompt, height=155)
render_copy_btn("flow_pr", "COPY GOOGLE FLOW IMAGE PROMPT", live_flow_prompt)

# ---------------------------------------------------------
# 8. STEP 2: UPLOAD GENERATED FLOW IMAGE -> CROP WATERMARK & EXPORT
# ---------------------------------------------------------
st.divider()
st.markdown("### ✂️ 2. Upload Google Flow Image & Crop Watermark")

col_up1, col_up2 = st.columns([2, 1])
with col_up1:
    uploaded_flow_img = st.file_uploader("Upload your image generated from Google Flow", type=["png", "jpg", "jpeg", "webp"])
    if uploaded_flow_img:
        with open(SAVED_FLOW_IMG_PATH, "wb") as sf:
            sf.write(uploaded_flow_img.read())
with col_up2:
    target_aspect_choice = st.selectbox(
        "Output Aspect Ratio",
        ["4:5 Feed Portrait (1080×1350)", "9:16 Story / Reel Cover (1080×1920)", "1:1 Square Post (1080×1080)"]
    )

col_cr1, col_cr2, col_cr3 = st.columns(3)
with col_cr1:
    wm_crop_pct = st.slider("Bottom Watermark Crop %", min_value=0.0, max_value=15.0, value=6.5, step=0.5, help="6.5% removes the bottom-right Flow/Imagen watermark cleanly.")
with col_cr2:
    contrast_val = st.slider("Contrast Polish", min_value=0.90, max_value=1.25, value=1.04, step=0.02)
with col_cr3:
    sharpness_val = st.slider("Text Sharpness", min_value=0.90, max_value=1.35, value=1.08, step=0.02)

slug = re.sub(r"[^a-zA-Z0-9]+", "_", ed_head).strip("_").lower() or "echoes_post"
file_name = f"{next_d.replace('-', '')}_{slug}.png"

if os.path.exists(SAVED_FLOW_IMG_PATH):
    raw_im = Image.open(SAVED_FLOW_IMG_PATH)
    cropped_im = process_uploaded_flow_image(
        raw_im,
        bottom_crop_pct=wm_crop_pct / 100.0,
        target_ratio_mode=target_aspect_choice,
        sharpness_boost=sharpness_val,
        contrast_boost=contrast_val
    )
    st.image(cropped_im, caption=f"✓ Clean Watermark-Free Master ({target_aspect_choice})", use_container_width=True)

    col_dl1, col_dl2 = st.columns([3, 1])
    with col_dl1:
        out_buf = io.BytesIO()
        cropped_im.save(out_buf, format="PNG", quality=98)
        st.download_button(f"💾 Download Cropped Master Image ({file_name})", out_buf.getvalue(), file_name, "image/png", use_container_width=True)
    with col_dl2:
        if st.button("🗑️ Clear Image", use_container_width=True):
            try: os.remove(SAVED_FLOW_IMG_PATH)
            except Exception: pass
            st.rerun()
else:
    st.info("👆 Generate your image in Google Flow using the prompt above, then upload it here to crop the watermark and download the clean master.")

# ---------------------------------------------------------
# 9. STEP 3: PROVOCATIVE CAPTION, EMOJIS, HASHTAGS & FIRST COMMENT
# ---------------------------------------------------------
st.divider()
st.markdown("### 📝 3. Complete Meta Feed Metadata, Emojis & Hashtags")

ed_ref_q = st.text_input("Discussion Question (Non-Bait)", value=card.get("reflection_prompt", "What lesson here resonates most with your own experience?"))
hashtags_clean = card.get("tags", "#Mindset #LifeLessons #PersonalGrowth #SelfRespect #Discipline #Wisdom")

feed_caption = (
    f"⚡ {ed_head.upper()} 🏛️\n\n"
    f"💡 {card.get('caption_story', '')}\n\n"
    f"💬 {ed_ref_q} 👇\n\n"
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

    st.session_state["img_banner"] = f"✓ Scheduled '{ed_head}' ({resolved_style}) for {d_str} @ {sched_time} IST!"
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
