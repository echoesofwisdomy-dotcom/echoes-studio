import os
import io
import json
import re
import random
from datetime import datetime, timedelta, timezone
import requests
import numpy as np
from PIL import Image, ImageDraw, ImageFont
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
# 3. RELIABLE CDN FONT FOUNDRY (JSDELIVR CDN)
# ---------------------------------------------------------
CDN_FONTS = {
    "Cinzel_Bold": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cinzel/static/Cinzel-Bold.ttf",
    "Cinzel_Reg": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cinzel/static/Cinzel-Regular.ttf",
    "Cormorant_Italic": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cormorantgaramond/static/CormorantGaramond-Italic.ttf"
}

def ensure_fonts():
    headers = {"User-Agent": "Mozilla/5.0"}
    for name, url in CDN_FONTS.items():
        path = os.path.join(FONTS_DIR, f"{name}.ttf")
        if not os.path.exists(path) or os.path.getsize(path) < 5000:
            try:
                res = requests.get(url, headers=headers, timeout=12)
                if res.status_code == 200 and len(res.content) > 5000:
                    with open(path, "wb") as f:
                        f.write(res.content)
            except Exception:
                pass

ensure_fonts()

def get_font(name, size):
    path = os.path.join(FONTS_DIR, f"{name}.ttf")
    if os.path.exists(path) and os.path.getsize(path) > 5000:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    # Pillow 10+ scaled default fallback
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

# ---------------------------------------------------------
# 4. CURATED 4K THEMATIC VISUAL VAULT
# ---------------------------------------------------------
THEMATIC_PHOTO_VAULT = {
    "SEA_CLIFF": [
        {"name": "Rugged Sea Cliffs Against Storm Surge", "url": "https://images.unsplash.com/photo-1505118380757-91f5f5632de0?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Dark Volcanic Coast & Breaking Ocean Swell", "url": "https://images.unsplash.com/photo-1518837695005-2083093ee35b?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Sheer Atlantic Ocean Cliff Edge", "url": "https://images.unsplash.com/photo-1476673160081-cf065607f449?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "MARBLE_STATUE": [
        {"name": "Classical Roman Marble Bust in Dramatic Shadow", "url": "https://images.unsplash.com/photo-1580136579312-94651dfd596d?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Chiaroscuro Hellenistic Bronze Philosopher", "url": "https://images.unsplash.com/photo-1578301978693-85fa9c0320b9?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Weathered Greek Marble Profile", "url": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "DARK_CITADEL": [
        {"name": "Roman Colosseum Arches at Twilight", "url": "https://images.unsplash.com/photo-1552832230-c0197dd311b5?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Ancient Classical Stone Portico", "url": "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "ALPINE_PEAKS": [
        {"name": "Alpine Summit Above Mist", "url": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Granite Mountain Ridge at Sunset", "url": "https://images.unsplash.com/photo-1486870591958-9b9d0d1dda99?auto=format&fit=crop&w=1080&h=1350&q=88"}
    ],
    "DEEP_WORK": [
        {"name": "Quiet Architect Workspace with Clean Lines", "url": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1080&h=1350&q=88"},
        {"name": "Minimalist Slate & Timber Study", "url": "https://images.unsplash.com/photo-1507842229451-7f01be7fe7ab?auto=format&fit=crop&w=1080&h=1350&q=88"}
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
# 6. GRAPHICS COMPOSITOR
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

def render_post_canvas(bg_img, post_data):
    w, h = 1080, 1350
    canvas = bg_img.convert("RGBA")
    
    # Smooth Scrim with balanced backdrop visibility
    scrim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(scrim)
    for y in range(h):
        dist = abs(y - h * 0.52) / (h * 0.52)
        alpha = int(45 + 115 * (1.0 - dist ** 1.8))
        s_draw.line([(0, y), (w, y)], fill=(6, 8, 12, min(190, max(25, alpha))))
    canvas = Image.alpha_composite(canvas, scrim)
    
    draw = ImageDraw.Draw(canvas)
    
    # Category Pill
    cat_f = get_font("Cinzel_Bold", 26)
    cat_t = f"—  {post_data['category'].upper()}  —"
    cw = draw.textlength(cat_t, font=cat_f)
    draw.text(((w - cw) // 2 + 1, 271), cat_t, font=cat_f, fill=(0, 0, 0, 220))
    draw.text(((w - cw) // 2, 270), cat_t, font=cat_f, fill=(218, 175, 55, 255))
    
    # Headline
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
    
    # Body Insight
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
        
    # Attribution
    att_f = get_font("Cinzel_Bold", 24)
    att_t = f"—  {post_data['attribution'].upper()}  —"
    aw = draw.textlength(att_t, font=att_f)
    draw.text(((w - aw) // 2 + 1, by + 26), att_t, font=att_f, fill=(0, 0, 0, 220))
    draw.text(((w - aw) // 2, by + 25), att_t, font=att_f, fill=(218, 175, 55, 255))
    
    return canvas.convert("RGB")

# ---------------------------------------------------------
# 7. AI SYNTHESIS PIPELINE
# ---------------------------------------------------------
def generate_stoic_concept(raw_api_key, visual_theme, philosopher, custom_directive):
    clean_key = raw_api_key.strip().strip('"').strip("'")
    client = genai.Client(api_key=clean_key)
    blacklist = db.get("blacklisted_headlines", [])
    blacklist_str = "\n".join([f"- {h}" for h in blacklist[-40:]]) if blacklist else "None."
    
    prompt = f"""
    Role: Creative Director for 'Echoes of Wisdom'.
    Theme: {visual_theme}
    Preferred Philosopher: {philosopher}
    User Direction/Voice Input: {custom_directive or 'Synthesize an authoritative, novel Stoic lesson.'}
    
    STRICT BLACKLIST (DO NOT USE OR REPHRASE):
    {blacklist_str}
    
    Output JSON ONLY:
    {{
      "category": "CONCISE PILLAR (e.g. EMOTIONAL MASTERY, FORTITUDE)",
      "headline": "BOLD 2-4 WORD HOOK",
      "body_text": "One powerful 12-18 word sentence explaining the hook.",
      "attribution": "{philosopher.upper() if philosopher != 'Any' else 'MARCUS AURELIUS'}",
      "post_caption": "Full Facebook/Instagram caption with hook, lesson, binary debate CTA (1️⃣/2️⃣), handles, and hashtags."
    }}
    """

    candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    last_err = None
    
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
            last_err = e
            continue
            
    return None, str(last_err)

# ---------------------------------------------------------
# 8. STREAMLIT UI: CONTROLS & STUDIO
# ---------------------------------------------------------
st.title("🏛️ Echoes Studio")
st.caption("Automated Mobile Production Engine")

# Robust API Key Resolution
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
        selected_theme = st.selectbox(
            "Visual Backdrop",
            ["SEA_CLIFF", "MARBLE_STATUE", "DARK_CITADEL", "ALPINE_PEAKS", "DEEP_WORK"]
        )
    with col2:
        selected_philosopher = st.selectbox(
            "Philosopher",
            ["Any", "Marcus Aurelius", "Seneca", "Epictetus"]
        )

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
            concept, err = generate_stoic_concept(api_key, selected_theme, selected_philosopher, custom_input)
            
            if err or not concept:
                st.error(f"⚠️ API Error: {err}. Please check your API key in the 'API Key Status' box above.")
            else:
                vault_items = THEMATIC_PHOTO_VAULT.get(selected_theme, THEMATIC_PHOTO_VAULT["SEA_CLIFF"])
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
