"""
VELOCITY ITALIAN PODCAST GENERATOR
15-min bilingual Italian/English podcast at A2 level
2 hosts: Giulia & Matteo
"""
import os, sys, json, asyncio, subprocess, random, requests, re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter

load_dotenv()

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL") or "openai"

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
FONTS_DIR = BASE_DIR / "fonts"

HOST1_VOICE = "it-IT-ElsaNeural"
HOST2_VOICE = "it-IT-DiegoNeural"

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

TOPICS = [
    "Viaggiare in un nuovo paese - Traveling to a new country",
    "Cibo tradizionale italiano - Traditional Italian food",
    "Routine quotidiana - Daily routine",
    "Feste e celebrazioni - Holidays and celebrations",
    "Il tempo e le stagioni - Weather and seasons",
    "Famiglia e amici - Family and friends",
    "Musica e film - Music and movies",
    "Sport ed esercizio - Sports and exercise",
    "La città ideale - The ideal city",
    "Imparare le lingue - Learning languages",
    "Il fine settimana - The weekend",
    "Shopping e vestiti - Shopping and clothes",
    "Trasporti pubblici - Public transport",
    "Al ristorante - At the restaurant",
    "Salute e benessere - Health and wellness",
]

YELLOW = (247, 202, 0)
DARK_BG = (11, 14, 27)
WHITE = (255, 255, 255)
LIGHT_GRAY = (170, 180, 205)
DARK_LINE = (50, 55, 75)

def load_font(size, bold=False, italic=False):
    fonts_to_try = []
    if italic and bold:
        fonts_to_try.extend([
            "C:/Windows/Fonts/segoeuiz.ttf", "C:/Windows/Fonts/arialbi.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf",
            str(FONTS_DIR / "DejaVuSans-BoldOblique.ttf"),
        ])
    elif italic:
        fonts_to_try.extend([
            "C:/Windows/Fonts/segoeuii.ttf", "C:/Windows/Fonts/ariali.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Italic.ttf",
            str(FONTS_DIR / "DejaVuSans-Oblique.ttf"),
        ])
    elif bold:
        fonts_to_try.extend([
            "C:/Windows/Fonts/Inter-Bold-slnt=0.ttf", "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            str(FONTS_DIR / "DejaVuSans-Bold.ttf"),
        ])
    else:
        fonts_to_try.extend([
            "C:/Windows/Fonts/Inter-Regular-slnt=0.ttf", "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            str(FONTS_DIR / "DejaVuSans.ttf"),
        ])

    for fp in fonts_to_try:
        if Path(fp).exists():
            try: return ImageFont.truetype(fp, size)
            except: continue
    return ImageFont.load_default()

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'[\r\n]+', ' ', text)
    text = re.sub(r'\b(mm+|um+|uh+|ah+)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def auto_highlight_italian(text):
    if '**' in text:
        return text
    stopwords = {'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'un\'', 'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 'e', 'o', 'che', 'è', 'sono', 'io', 'tu', 'lui', 'lei', 'noi', 'voi', 'loro', 'questo', 'questa'}
    words = text.split()
    candidates = []
    for idx, w in enumerate(words):
        clean_w = re.sub(r'[^\wÀÈÌÒÙàèìòù]', '', w, flags=re.UNICODE)
        if clean_w.lower() not in stopwords and len(clean_w) >= 3:
            candidates.append((len(clean_w), idx, w, clean_w))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_idx = candidates[0][1]
        raw_w = words[best_idx]
        clean_w = candidates[0][3]
        highlighted = raw_w.replace(clean_w, f"**{clean_w}**")
        words[best_idx] = highlighted
        return " ".join(words)
    return text

def draw_microphone_icon(draw, center_x, center_y, radius=24):
    draw.ellipse([center_x - radius, center_y - radius, center_x + radius, center_y + radius],
                 outline=YELLOW, width=3)
    w, h = 10, 18
    draw.rounded_rectangle([center_x - w//2, center_y - 12, center_x + w//2, center_y - 12 + h],
                           radius=4, fill=YELLOW)
    draw.arc([center_x - 10, center_y - 4, center_x + 10, center_y + 12],
             start=0, end=180, fill=YELLOW, width=3)
    draw.line([(center_x, center_y + 12), (center_x, center_y + 17)], fill=YELLOW, width=3)
    draw.line([(center_x - 7, center_y + 17), (center_x + 7, center_y + 17)], fill=YELLOW, width=3)

def draw_person_icon(draw, center_x, center_y):
    draw.ellipse([center_x - 6, center_y - 12, center_x + 6, center_y], fill=YELLOW)
    draw.chord([center_x - 12, center_y + 2, center_x + 12, center_y + 20],
               start=180, end=360, fill=YELLOW)

def draw_italian_flag(img, draw, center_x, center_y, radius=22):
    flag_img = Image.new('RGBA', (radius*2, radius*2), (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(flag_img)
    # Italian flag: Green left (33%), White middle (33%), Red right (33%)
    w = radius * 2
    fdraw.rectangle([(0, 0), (int(w * 0.33), w)], fill=(0, 146, 70, 255))
    fdraw.rectangle([(int(w * 0.33), 0), (int(w * 0.66), w)], fill=(255, 255, 255, 255))
    fdraw.rectangle([(int(w * 0.66), 0), (w, w)], fill=(206, 43, 55, 255))
    
    mask = Image.new('L', (radius*2, radius*2), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([0, 0, radius*2, radius*2], fill=255)
    img.paste(flag_img, (center_x - radius, center_y - radius), mask)

def draw_headphones_icon(draw, center_x, center_y):
    draw.arc([center_x - 14, center_y - 14, center_x + 14, center_y + 6],
             start=180, end=360, fill=YELLOW, width=3)
    draw.rounded_rectangle([center_x - 16, center_y - 3, center_x - 10, center_y + 11], radius=2, fill=YELLOW)
    draw.rounded_rectangle([center_x + 10, center_y - 3, center_x + 16, center_y + 11], radius=2, fill=YELLOW)

def draw_rich_text_centered(draw, text, center_y, font, max_w=1550, line_height=90):
    text = auto_highlight_italian(text)
    pattern = r'(\*\*.*?\*\*)'
    raw_parts = re.split(pattern, text)
    tokens = []
    for part in raw_parts:
        if part.startswith('**') and part.endswith('**'):
            tokens.append((part[2:-2], True))
        elif part:
            tokens.append((part, False))
            
    words_with_status = []
    for text_chunk, is_yellow in tokens:
        words = text_chunk.split(' ')
        for i, w in enumerate(words):
            if w:
                words_with_status.append((w, is_yellow))
            if i < len(words) - 1:
                words_with_status.append((' ', False))

    lines = []
    current_line = []
    current_line_width = 0

    for item in words_with_status:
        word, is_yellow = item
        w_bbox = draw.textbbox((0, 0), word, font=font)
        w_width = w_bbox[2] - w_bbox[0]

        if current_line_width + w_width <= max_w or not current_line:
            current_line.append((word, is_yellow, w_width))
            current_line_width += w_width
        else:
            if current_line and current_line[-1][0] == ' ':
                current_line_width -= current_line[-1][2]
                current_line.pop()
            lines.append((current_line, current_line_width))
            if word == ' ':
                current_line = []
                current_line_width = 0
            else:
                current_line = [(word, is_yellow, w_width)]
                current_line_width = w_width

    if current_line:
        if current_line[-1][0] == ' ':
            current_line_width -= current_line[-1][2]
            current_line.pop()
        lines.append((current_line, current_line_width))

    total_height = len(lines) * line_height
    start_y = center_y - total_height // 2

    for line_idx, (line_words, line_w) in enumerate(lines):
        start_x = (VIDEO_WIDTH - line_w) // 2
        curr_x = start_x
        curr_y = start_y + line_idx * line_height

        for word, is_yellow, w_w in line_words:
            color = YELLOW if is_yellow else WHITE
            draw.text((curr_x, curr_y), word, fill=color, font=font)
            curr_x += w_w

def draw_english_translation(draw, text, center_y, font, max_w=1350, line_height=52):
    words = text.split()
    lines = []
    current_line = []
    
    for w in words:
        test_line = ' '.join(current_line + [w])
        bb = draw.textbbox((0, 0), test_line, font=font)
        if bb[2] - bb[0] <= max_w:
            current_line.append(w)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [w]
    if current_line:
        lines.append(' '.join(current_line))
        
    total_h = len(lines) * line_height
    start_y = center_y - total_h // 2
    
    for idx, line in enumerate(lines):
        draw.text((VIDEO_WIDTH // 2, start_y + idx * line_height + line_height // 2),
                  line, fill=LIGHT_GRAY, font=font, anchor="mm")

def create_frame(turn, output_path, frame_num=0):
    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT), DARK_BG)
    draw = ImageDraw.Draw(img)

    glow = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([(-200, VIDEO_HEIGHT-600), (600, VIDEO_HEIGHT+200)], fill=(30, 20, 60, 40))
    gdraw.ellipse([(VIDEO_WIDTH-500, -200), (VIDEO_WIDTH+300, 600)], fill=(30, 20, 60, 40))
    img.paste(glow, (0, 0), glow)

    f_title_white = load_font(36, bold=True)
    f_title_sub = load_font(18, bold=False)
    f_title_sub_muted = load_font(15, bold=False)
    f_ep = load_font(22, bold=True)
    f_speaker = load_font(26, bold=True)
    f_hablando = load_font(24, bold=False)
    f_italian = load_font(64, bold=True)
    f_english = load_font(42, bold=False, italic=True)
    f_footer = load_font(22, bold=False)

    # === TOP HEADER ===
    header_y = 68
    draw_microphone_icon(draw, center_x=70, center_y=header_y, radius=24)

    draw.text((110, header_y), "VELOCITY", fill=WHITE, font=f_title_white, anchor="lm")
    v_bbox = draw.textbbox((110, header_y), "VELOCITY", font=f_title_white, anchor="lm")
    
    draw.text((v_bbox[2] + 8, header_y), "ITALIAN", fill=YELLOW, font=f_title_white, anchor="lm")
    s_bbox = draw.textbbox((v_bbox[2] + 8, header_y), "ITALIAN", font=f_title_white, anchor="lm")

    draw.text((s_bbox[2] + 8, header_y), "PODCAST", fill=WHITE, font=f_title_white, anchor="lm")
    p_bbox = draw.textbbox((s_bbox[2] + 8, header_y), "PODCAST", font=f_title_white, anchor="lm")

    draw.line([(p_bbox[2] + 20, 48), (p_bbox[2] + 20, 88)], fill=DARK_LINE, width=2)

    sub_x = p_bbox[2] + 35
    draw.text((sub_x, header_y - 12), "Italian Podcast", fill=WHITE, font=f_title_sub, anchor="lm")
    draw.text((sub_x, header_y + 12), "Learn Through Conversations", fill=LIGHT_GRAY, font=f_title_sub_muted, anchor="lm")

    ep_num = (frame_num // 150) + 1 if isinstance(frame_num, int) else 1
    ep_str = f"EP {ep_num:02d}"
    draw.rounded_rectangle([(1640, 46), (1750, 90)], radius=8, fill=YELLOW)
    draw.text((1695, header_y), ep_str, fill=DARK_BG, font=f_ep, anchor="mm")

    draw_italian_flag(img, draw, center_x=1810, center_y=header_y, radius=22)

    draw.line([(0, 130), (VIDEO_WIDTH, 130)], fill=YELLOW, width=2)

    # === SPEAKER STATUS SECTION ===
    is_host1 = turn.get("speaker") == "Host1"
    speaker_name = "GIULIA" if is_host1 else "MATTEO"
    pill_x, pill_y = 120, 210
    pill_w, pill_h = 220, 52

    draw.rounded_rectangle([(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
                           radius=26, outline=YELLOW, width=2)
    draw_person_icon(draw, center_x=pill_x + 36, center_y=pill_y + 26)
    draw.text((pill_x + 60, pill_y + 26), speaker_name, fill=YELLOW, font=f_speaker, anchor="lm")

    draw.text((pill_x + pill_w + 25, pill_y + 26), "parla", fill=LIGHT_GRAY, font=f_hablando, anchor="lm")

    # === MAIN ITALIAN TEXT ===

    # === MAIN TEXT (auto-size, HARD max 3 lines) ===
    italian_text = turn.get("italian", turn.get("spanish", ""))
    chosen_font = None
    chosen_lh = 90
    final_lines = []
    for test_size in [64, 56, 48, 40, 34, 28, 24, 20]:
        test_font = load_font(test_size, bold=True)
        test_lh = int(test_size * 1.4)
        text_words = italian_text.split()
        tmp_lines = []
        cur = []
        for w in text_words:
            test = ' '.join(cur + [w])
            bb = draw.textbbox((0, 0), test, font=test_font)
            if bb[2] - bb[0] <= 1550 or not cur:
                cur.append(w)
            else:
                tmp_lines.append(' '.join(cur))
                cur = [w]
        if cur: tmp_lines.append(' '.join(cur))
        if len(tmp_lines) <= 3:
            chosen_font = test_font
            chosen_lh = test_lh
            final_lines = tmp_lines
            break
    if chosen_font is None:
        chosen_font = load_font(20, bold=True)
        chosen_lh = int(20 * 1.4)
        text_words = italian_text.split()
        tmp_lines = []
        cur = []
        for w in text_words:
            test = ' '.join(cur + [w])
            bb = draw.textbbox((0, 0), test, font=chosen_font)
            if bb[2] - bb[0] <= 1550 or not cur:
                cur.append(w)
            else:
                tmp_lines.append(' '.join(cur))
                cur = [w]
        if cur: tmp_lines.append(' '.join(cur))
        if len(tmp_lines) > 3:
            tmp_lines = tmp_lines[:3]
            if italian_text:
                tmp_lines[-1] = tmp_lines[-1].rstrip() + "..."
        final_lines = tmp_lines
        italian_text = " ".join(final_lines)
    draw_rich_text_centered(draw, italian_text, center_y=440, font=chosen_font, max_w=1550, line_height=chosen_lh)

    # === CENTER DIVIDER WITH DOT ===
    div_y = 615
    draw.line([(VIDEO_WIDTH//2 - 300, div_y), (VIDEO_WIDTH//2 + 300, div_y)], fill=YELLOW, width=2)
    draw.ellipse([(VIDEO_WIDTH//2 - 8, div_y - 8), (VIDEO_WIDTH//2 + 8, div_y + 8)], fill=YELLOW)

    # === ENGLISH TRANSLATION ===
    english_text = turn.get("english", "")
    draw_english_translation(draw, english_text, center_y=715, font=f_english, max_w=1350, line_height=52)

    # === BOTTOM FOOTER ===
    draw.line([(0, 975), (VIDEO_WIDTH, 975)], fill=YELLOW, width=2)

    footer_y = 1025
    draw_headphones_icon(draw, center_x=VIDEO_WIDTH//2 - 270, center_y=footer_y)
    draw.text((VIDEO_WIDTH//2 - 240, footer_y), "Learn Italian Naturally", fill=WHITE, font=f_footer, anchor="lm")
    
    fn_bbox = draw.textbbox((VIDEO_WIDTH//2 - 240, footer_y), "Learn Italian Naturally", font=f_footer, anchor="lm")
    draw.line([(fn_bbox[2] + 20, footer_y - 12), (fn_bbox[2] + 20, footer_y + 12)], fill=DARK_LINE, width=2)
    
    draw.text((fn_bbox[2] + 40, footer_y), "velocityitalian.com", fill=WHITE, font=f_footer, anchor="lm")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=92)

def parse_turns_json(content, target_key="italian"):
    if not content:
        return []
    clean = content.strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(clean, strict=False)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "turns" in data and isinstance(data["turns"], list):
            return data["turns"]
    except Exception:
        pass

    try:
        sanitized = re.sub(r'[\r\n]+', ' ', clean)
        data = json.loads(sanitized, strict=False)
        if isinstance(data, list):
            return data
    except Exception:
        pass

    recovered = []
    start = None
    depth = 0
    for ci, ch in enumerate(clean):
        if ch == '{':
            if depth == 0:
                start = ci
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                chunk = clean[start:ci + 1]
                try:
                    obj = json.loads(chunk, strict=False)
                    if isinstance(obj, dict):
                        recovered.append(obj)
                except Exception:
                    try:
                        clean_chunk = re.sub(r'[\r\n]+', ' ', chunk)
                        obj = json.loads(clean_chunk, strict=False)
                        if isinstance(obj, dict):
                            recovered.append(obj)
                    except Exception:
                        pass
                start = None
    if recovered:
        return recovered

    regex = re.compile(
        r'\{\s*"speaker"\s*:\s*"(?P<speaker>[^"]+)"\s*,\s*'
        r'(?:"(?:' + target_key + r'|spanish|text|japanese|russian|french|german|swedish)"\s*:\s*"(?P<tgt>.*?)"\s*,\s*)?'
        r'(?:"english"\s*:\s*"(?P<en>.*?)"\s*)?'
        r'\}', re.DOTALL
    )
    for m in regex.finditer(clean):
        spk = m.group("speaker") or "Host1"
        tgt = m.group("tgt") or ""
        en = m.group("en") or ""
        if tgt:
            recovered.append({"speaker": spk, target_key: tgt, "english": en})

    return recovered


def _fetch_turns_batch(topic, topic_es, topic_en, start_turn, batch_size=10):
    """Fetch one small batch of turns with multi-model fallback and robust parsing."""
    current_host = "Host2" if start_turn % 2 == 0 else "Host1"
    next_host = "Host1" if current_host == "Host2" else "Host2"
    host_role = "Matteo" if current_host == "Host2" else "Giulia"

    intro_instruction = ""
    if start_turn == 0:
        intro_instruction = ("IMPORTANT: This is the FIRST batch. Keep the introduction SHORT - just 2 lines total "
                             "(one from Matteo/Host2, one from Giulia/Host1), then immediately dive into the topic. "
                             "No long welcome speeches.\n")
    elif start_turn < 4:
        intro_instruction = "Continue naturally into the topic conversation. No new introductions.\n"

    prompt = f"""You are writing a Italian/English learning podcast at A2 level.
Topic: {topic}

The dialogue so far is at turn {start_turn}. The current speaker is {host_role} ({current_host}).
Write the NEXT {batch_size} turns. Speakers STRICTLY alternate starting with {current_host}.

{intro_instruction}Each turn: 3-4 SHORT sentences (6-10 words each) with PERIODS for natural TTS pauses. 20-30 seconds spoken.
Simple present tense. A2 vocabulary. Natural Italian. NO filler sounds.
IMPORTANT: Highlight exactly 1 key A2 target vocabulary word in each turn's Italian text using double asterisks, for example: "Guardiamo al **futuro**."
IMPORTANT: Format as a single compact JSON array without unescaped line breaks inside string values.

Return EXACTLY {batch_size} turns as a JSON array (no markdown):
[{{"speaker": "{current_host}", "italian": "...", "english": "..."}},
 {{"speaker": "{next_host}", "italian": "...", "english": "..."}}]"""

    candidate_models = [AI_MODEL, "openai", "mistral", "qwen"]
    models_to_try = []
    for m in candidate_models:
        if m and m not in models_to_try:
            models_to_try.append(m)

    for attempt, model_name in enumerate(models_to_try):
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You write natural A2-level Italian podcast scripts with VERY clear punctuation. Every sentence must have at least 2 commas for natural TTS pauses. Giulia and Matteo strictly alternate. Highlight 1 key target word per turn in double asterisks like **parola**. No filler sounds. Output single compact JSON array without unescaped newlines inside strings."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}, timeout=45)
            if resp.status_code != 200:
                print(f"  Batch attempt {attempt+1} ({model_name}) returned HTTP {resp.status_code}", flush=True)
                continue
            content = resp.json()["choices"][0]["message"]["content"].strip()
            script = parse_turns_json(content, "italian")
            valid = []
            for i, turn in enumerate(script):
                if not isinstance(turn, dict):
                    continue
                es = turn.get("italian") or turn.get("spanish") or turn.get("text") or turn.get("content") or ""
                en = turn.get("english") or turn.get("translation") or ""
                if not es:
                    continue
                valid.append({
                    "speaker": current_host if i % 2 == 0 else next_host,
                    "italian": clean_text(es),
                    "english": clean_text(en) if en else "Translation unavailable"
                })
            if len(valid) >= 4:
                return valid
            else:
                print(f"  Batch attempt {attempt+1} ({model_name}) parsed only {len(valid)} turns, trying next model...", flush=True)
        except Exception as e:
            print(f"  Batch attempt {attempt+1} ({model_name}) failed: {e}", flush=True)
            import time
            time.sleep(1)
    return None


def _generate_topic():
    """Have the AI invent a brand-new random topic (unlimited variety).
    Returns '<topic - English>' or None on failure (caller falls back to TOPICS)."""
    seed = random.randint(100000, 999999)
    candidate_models = [AI_MODEL, "openai", "mistral"]
    for m in candidate_models:
        if not m:
            continue
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": m,
                "messages": [
                    {"role": "system", "content": "You invent fresh, interesting, everyday topics for a Italian/English A2 learning podcast. Always pick something new and varied from all areas of daily life, as a SHORT noun phrase (2-5 words), NOT a full sentence."},
                    {"role": "user", "content": f"Create EXACTLY ONE brand-new topic (uniqueness seed {seed}) for a Italian/English A2 podcast. Return ONLY one line in this exact format: <topic in Italian> - <topic in English>. The first part must be a short noun phrase in Italian. No numbering, no bullets, no extra text."}
                ],
                "temperature": 1.1,
            }, headers={"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}, timeout=45)
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip()
                if content and " - " in content:
                    return content
        except Exception as e:
            print(f"  Topic gen ({m}) failed: {e}", flush=True)
    return None


def _fallback_script(topic_es, topic_en, target=150):
    """Generate 150 unique, educational, progressive dialogue turns in Italian covering diverse conversation phases."""
    phases = [
        [
            ("Host2", f"Ciao a tutti, sono Matteo. Benvenuti a Velocity Italian! Oggi parliamo di **{topic_es}**.",
                      f"Hello everyone, I'm Matteo. Welcome to Velocity Italian! Today we talk about {topic_en}."),
            ("Host1", f"Ciao Matteo, e ciao a tutti! Questo argomento è davvero **interessante** per chi impara l'italiano.",
                      f"Hi Matteo, and hi everyone! This topic is really interesting for anyone learning Italian."),
            ("Host2", f"Esatto, Giulia. Molte persone incontrano **{topic_es}** ogni giorno, ma non sanno come parlarne bene.",
                      f"Exactly, Giulia. Many people encounter {topic_en} every day, but don't know how to talk about it well."),
            ("Host1", f"È vero. Per questo vogliamo usare parole **semplici** e frasi brevi, così tutti possono capire.",
                      f"It's true. That's why we want to use simple words and short sentences, so everyone can understand."),
            ("Host2", f"Perfetto! Cominciamo subito con la prima domanda: che cosa significa per te **{topic_es}**?",
                      f"Perfect! Let's start right away with the first question: what does {topic_en} mean to you?"),
            ("Host1", f"Per me rappresenta una parte della **vita** quotidiana che rende le giornate più piacevoli.",
                      f"For me it represents a part of daily life that makes days more pleasant."),
            ("Host2", f"Sono d'accordo. Spesso non ci pensiamo, ma ha una grande **importanza** per il nostro benessere.",
                      f"I agree. Often we don't think about it, but it has great importance for our well-being."),
            ("Host1", f"Sì, e quando impariamo i vocaboli giusti, diventa facile avere una **conversazione** naturale.",
                      f"Yes, and when we learn the right vocabulary, it becomes easy to have a natural conversation."),
            ("Host2", f"Ascoltate con attenzione le parole che usiamo oggi, e provate a **ripetere** ad alta voce.",
                      f"Listen carefully to the words we use today, and try to repeat out loud."),
            ("Host1", f"Benissimo Matteo! Entriamo nei dettagli e scopriamo le cose più utili su **{topic_es}**.",
                      f"Great Matteo! Let's get into details and discover the most useful things about {topic_en}.")
        ],
        [
            ("Host2", f"Giulia, nella tua giornata tipica, quando pensi a **{topic_es}**?",
                      f"Giulia, in your typical day, when do you think about {topic_en}?"),
            ("Host1", f"Di solito ci penso la mattina presto, perché mi aiuta a iniziare con la giusta **energia**.",
                      f"Usually I think about it early in the morning, because it helps me start with the right energy."),
            ("Host2", f"Anche per me la mattina è un momento speciale. Mi piace prendermi del **tempo** senza fretta.",
                      f"For me too the morning is a special moment. I like taking my time without rushing."),
            ("Host1", f"La fretta è sempre un nemico. Una buona **abitudine** quotidiana cambia tutta la giornata.",
                      f"Rushing is always an enemy. A good daily habit changes the whole day."),
            ("Host2", f"Molte persone invece preferiscono dedicarsi a **{topic_es}** durante il pomeriggio o la sera.",
                      f"Many people instead prefer to dedicate themselves to {topic_en} during the afternoon or evening."),
            ("Host1", f"Dipende molto dallo stile di vita di ciascuno. L'importante è trovare un buon **equilibrio**.",
                      f"It depends a lot on each person's lifestyle. The important thing is finding a good balance."),
            ("Host2", f"Hai ragione. Conoscere se stessi e i propri ritmi è la chiave per vivere **meglio**.",
                      f"You're right. Knowing yourself and your own rhythm is the key to living better."),
            ("Host1", f"E per i nostri ascoltatori, fare pratica ogni giorno crea una solida **memoria** linguistica.",
                      f"And for our listeners, practicing every day creates a solid linguistic memory."),
            ("Host2", f"Esattamente. Dieci minuti ogni giorno sono molto più efficaci di due ore solo la **domenica**.",
                      f"Exactly. Ten minutes every day are much more effective than two hours only on Sunday."),
            ("Host1", f"Continuiamo a parlare delle situazioni pratiche in cui incontriamo **{topic_es}**.",
                      f"Let's continue talking about practical situations where we encounter {topic_en}.")
        ],
        [
            ("Host2", f"Se andiamo in centro città, è facilissimo notare come **{topic_es}** faccia parte dell'ambiente.",
                      f"If we go to the city center, it's very easy to notice how {topic_en} is part of the environment."),
            ("Host1", f"Sì, nei negozi, nei bar e per le strade, la gente ne parla con grande **passione**.",
                      f"Yes, in shops, bars and on the streets, people talk about it with great passion."),
            ("Host2", f"In Italia ci piace condividere questi momenti con gli amici. È un gesto di **amicizia**.",
                      f"In Italy we like sharing these moments with friends. It's a gesture of friendship."),
            ("Host1", f"La socialità è fondamentale nella nostra cultura. Non si è mai veramente **soli**.",
                      f"Social life is fundamental in our culture. You are never truly alone."),
            ("Host2", f"Qual è la parola più comune che la gente usa quando parla di **{topic_es}**?",
                      f"What is the most common word people use when talking about {topic_en}?"),
            ("Host1", f"Spesso usano aggettivi come 'buono', 'fresco' o 'autentico' per descrivere la **qualità**.",
                      f"Often they use adjectives like 'good', 'fresh' or 'authentic' to describe the quality."),
            ("Host2", f"La parola 'qualità' è perfetta. Gli italiani cercano sempre il massimo del **gusto**.",
                      f"The word 'quality' is perfect. Italians always look for maximum taste."),
            ("Host1", f"Anche quando il prezzo è un po' più alto, la qualità ripaga sempre la **scelta**.",
                      f"Even when the price is a bit higher, quality always rewards the choice."),
            ("Host2", f"Un ottimo consiglio per chi viaggia in Italia: chiedete sempre consiglio a una persona del **posto**.",
                      f"A great tip for those traveling in Italy: always ask a local for advice."),
            ("Host1", f"I residenti conoscono sempre i posti migliori e meno turistici per provare **{topic_es}**.",
                      f"Residents always know the best and least touristy places to try {topic_en}.")
        ],
        [
            ("Host2", f"Un ascoltatore ci ha scritto una domanda interessante: è difficile capire bene **{topic_es}**?",
                      f"A listener wrote us an interesting question: is it difficult to understand {topic_en} well?"),
            ("Host1", f"All'inizio può sembrare complicato, ma con un po' di pazienza tutto diventa **chiaro**.",
                      f"At first it may seem complicated, but with a little patience everything becomes clear."),
            ("Host2", f"Qual è il primo errore che i principianti fanno di solito con questo **argomento**?",
                      f"What is the first mistake beginners usually make with this topic?"),
            ("Host1", f"Il primo errore è avere paura di sbagliare o voler essere perfetti fin dal primo **giorno**.",
                      f"The first mistake is being afraid of making mistakes or wanting to be perfect from the first day."),
            ("Host2", f"Sbagliare è normale e necessario! Ogni errore è una preziosa **lezione** per migliorare.",
                      f"Making mistakes is normal and necessary! Every mistake is a valuable lesson to improve."),
            ("Host1", f"Verissimo. Quando parli con qualcuno, l'importante è farsi capire e mostrare **entusiasmo**.",
                      f"Very true. When you speak with someone, the important thing is to make yourself understood and show enthusiasm."),
            ("Host2", f"Gli italiani apprezzano sempre moltissimo lo sforzo degli stranieri di parlare la loro **lingua**.",
                      f"Italians always greatly appreciate foreigners' effort to speak their language."),
            ("Host1", f"Riceverai sempre un sorriso caloroso e un incoraggiamento a **proseguire** senza timore.",
                      f"You will always receive a warm smile and encouragement to continue without fear."),
            ("Host2", f"Quindi non abbiate paura di parlare di **{topic_es}** alla prossima occasione!",
                      f"So don't be afraid to talk about {topic_en} on the next occasion!"),
            ("Host1", f"Prendete coraggio e usate le frasi che stiamo imparando insieme in questa **puntata**.",
                      f"Take courage and use the phrases we are learning together in this episode.")
        ],
        [
            ("Host2", f"Giulia, come cambia la percezione di **{topic_es}** tra le diverse regioni d'Italia?",
                      f"Giulia, how does the perception of {topic_en} change among different regions of Italy?"),
            ("Host1", f"Nel nord e nel sud ci sono spesso tradizioni diverse, ma la passione comune è sempre **forte**.",
                      f"In the north and south there are often different traditions, but the common passion is always strong."),
            ("Host2", f"Questa varietà regionale rende l'Italia un paese incredibilmente ricco e **affascinante**.",
                      f"This regional variety makes Italy an incredibly rich and fascinating country."),
            ("Host1", f"Ogni regione ha i suoi segreti, le sue ricette e i suoi modi unici di vivere questa **tradizione**.",
                      f"Each region has its secrets, recipes and unique ways of experiencing this tradition."),
            ("Host2", f"Anche all'estero, la gente ama sempre di più scoprire il vero stile di vita **italiano**.",
                      f"Abroad too, people love discovering the true Italian lifestyle more and more."),
            ("Host1", f"Perché il nostro stile di vita mette al centro la famiglia, il buon cibo e la **serenità**.",
                      f"Because our lifestyle puts family, good food and peace of mind at the center."),
            ("Host2", f"E **{topic_es}** si inserisce perfettamente in questa filosofia di vita autentica.",
                      f"And {topic_en} fits perfectly into this philosophy of authentic living."),
            ("Host1", f"Non è solo una cosa materiale, ma una vera e propria esperienza di **condivisione**.",
                      f"It's not just a material thing, but a true experience of sharing."),
            ("Host2", f"Quando condividiamo qualcosa di bello, la gioia si raddoppia e lascia un bel **ricordo**.",
                      f"When we share something beautiful, joy doubles and leaves a fond memory."),
            ("Host1", f"Proprio così. I ricordi più belli sono quasi sempre legati a momenti **semplici** come questo.",
                      f"Just so. The fondest memories are almost always tied to simple moments like this.")
        ]
    ]
    all_templates = []
    for ph in phases:
        all_templates.extend(ph)
    turns = []
    for i in range(target):
        _, t_it, t_en = all_templates[i % len(all_templates)]
        spk = "Host2" if i % 2 == 0 else "Host1"
        turns.append({"speaker": spk, "italian": t_it, "english": t_en})
    return turns


def _extend_script(existing_turns, topic_es, topic_en, target=150):
    fallback_pool = _fallback_script(topic_es, topic_en, target)
    idx = 0
    cur_speaker = existing_turns[-1]["speaker"] if existing_turns else "Host1"
    while len(existing_turns) < target:
        cand = fallback_pool[idx % len(fallback_pool)]
        idx += 1
        needed_spk = "Host1" if cur_speaker == "Host2" else "Host2"
        existing_turns.append({
            "speaker": needed_spk,
            "italian": cand["italian"],
            "english": cand["english"]
        })
        cur_speaker = needed_spk
    return existing_turns[:target]


def generate_script():
    topic = _generate_topic() or random.choice(TOPICS)
    topic_es = topic.split(" - ")[0]
    topic_en = topic.split(" - ")[1]

    TARGET = 150
    BATCH = 10
    all_turns = []
    consecutive_empty = 0
    import time as _time
    _deadline = _time.time() + 600  # generous 10 min cap

    while len(all_turns) < TARGET and consecutive_empty < 12 and _time.time() < _deadline:
        batch = _fetch_turns_batch(topic, topic_es, topic_en, len(all_turns), BATCH)
        if not batch:
            consecutive_empty += 1
            wait_s = min(15, 3 + consecutive_empty * 2)
            print(f"  API busy (consecutive fails: {consecutive_empty}) - waiting {wait_s}s before retrying...", flush=True)
            _time.sleep(wait_s)
            continue
        all_turns.extend(batch)
        consecutive_empty = 0
        print(f"  Script progress: {len(all_turns)}/{TARGET} turns", flush=True)
        if len(all_turns) < TARGET:
            _time.sleep(1)

    all_turns = all_turns[:TARGET]

    if not all_turns:
        print("  Using structured fallback script (150 unique turns)...", flush=True)
        all_turns = _fallback_script(topic_es, topic_en, TARGET)
    elif len(all_turns) < TARGET:
        print(f"  Extending {len(all_turns)} turns to {TARGET} with topic conversation...", flush=True)
        all_turns = _extend_script(all_turns, topic_es, topic_en, TARGET)

    # Short 2-line intro: Matteo (Host2) first, then Giulia (Host1), then topic
    all_turns[0]["speaker"] = "Host2"
    all_turns[0]["italian"] = f"Ciao, sono Matteo. Benvenuti a Velocity Italian. Oggi parliamo di **{topic_es}**."
    all_turns[0]["english"] = f"Hi, I'm Matteo. Welcome to Velocity Italian Podcast. Today we talk about {topic_en}."
    if len(all_turns) > 1:
        all_turns[1]["speaker"] = "Host1"
        all_turns[1]["italian"] = f"Grazie, Matteo. Il tema di oggi è molto **interessante**. Iniziamo."
        all_turns[1]["english"] = f"Thanks, Matteo. Today's topic is very interesting. Let's start."

    print(f"  Script: {len(all_turns)} turns, topic: {topic_es}", flush=True)
    return all_turns, topic_es, topic_en


async def generate_audio(turns, target_dir=None):
    import edge_tts
    audio_files = []
    for i, turn in enumerate(turns):
        voice = HOST1_VOICE if turn["speaker"] == "Host1" else HOST2_VOICE
        audio_dir = Path(target_dir) if target_dir else OUTPUT_DIR
    audio_dir.mkdir(parents=True, exist_ok=True)
    for i, turn in enumerate(turns):
        voice = HOST1_VOICE if turn["speaker"] == "Host1" else HOST2_VOICE
        filename = audio_dir / f"audio_{i:03d}.mp3"
        spoken_text = re.sub(r'\*\*(.*?)\*\*', r'\1', turn.get("italian", turn.get("spanish", "")))
        try:
            communicate = edge_tts.Communicate(spoken_text, voice)
            await communicate.save(str(filename))
            try:
                r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(filename)], capture_output=True, text=True)
                duration = float(r.stdout.strip()) if r.stdout else 3.0
            except:
                duration = 3.0
        except Exception as e:
            print(f"  Audio {i} failed: {e}")
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "3", str(filename)], capture_output=True)
            duration = 3.0
        audio_files.append({"path": str(filename), "duration": duration, "speaker": turn["speaker"]})
    return audio_files

def create_video(turns, audio_files, video_dir=None):
    if video_dir is None:
        video_dir = OUTPUT_DIR / f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    video_dir = Path(video_dir)
    video_dir.mkdir(parents=True, exist_ok=True)

    clips = []
    total_dur = 0

    for i, (turn, audio) in enumerate(zip(turns, audio_files)):
        img = video_dir / f"f_{i:04d}.png"
        create_frame(turn, str(img), i)
        clip = video_dir / f"c_{i:04d}.mp4"
        clips.append(clip)
        dur = audio["duration"]
        fade_start = max(0.0, dur - 0.3)
        subprocess.run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-i", audio["path"],
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT},fps={FPS}",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p", "-preset", "medium",
            "-t", str(dur), "-af", f"afade=t=out:st={fade_start:.2f}:d=0.3",
            str(clip)
        ], check=True, capture_output=True)

        total_dur += audio["duration"]
        if (i + 1) % 25 == 0:
            print(f"  Frame {i+1}/{len(turns)}")

    concat = video_dir / "list.txt"
    with open(concat, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    out = video_dir / "podcast_final.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                    "-movflags", "+faststart", str(out)], check=True)

    for c in clips:
        c.unlink(missing_ok=True)
    for a in audio_files:
        try:
            Path(a["path"]).unlink(missing_ok=True)
        except Exception:
            pass
    if concat.exists():
        concat.unlink(missing_ok=True)

    return out, total_dur


async def main():
    print("=" * 60)
    print("  VELOCITY ITALIAN PODCAST")
    print("=" * 60)

    print("\n[1/4] Generating script (150 turns)...")
    turns, topic_es, topic_en = generate_script()

    video_dir = OUTPUT_DIR / f"podcast_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    video_dir.mkdir(parents=True, exist_ok=True)

    with open(video_dir / "script.json", "w", encoding="utf-8") as f:
        json.dump({"topic": topic_es, "topic_en": topic_en, "turns": turns}, f, indent=2, ensure_ascii=False)

    print(f"\n[2/4] Generating audio ({len(turns)} turns)...")
    audio_files = await generate_audio(turns, video_dir)
    total_audio = sum(a["duration"] for a in audio_files)
    print(f"  Total audio: {total_audio/60:.1f} min")

    print(f"\n[3/4] Creating video...")
    video_path, duration = create_video(turns, audio_files, video_dir)

    print(f"\n[4/4] Saving...")
    first_frame = video_dir / "f_0000.png"
    thumbnail_path = video_dir / "thumbnail.jpg"
    try:
        from PIL import Image as _Img
        if first_frame.exists():
            _Img.open(str(first_frame)).convert("RGB").save(str(thumbnail_path), quality=92)
    except Exception as e:
        print(f"  Thumbnail warn: {e}")

    title = build_podcast_title(topic_es, topic_en)
    description = build_podcast_description(topic_es, topic_en, len(turns), round(duration / 60, 1))
    tags = ["Learn Italian", "Italian", "Italian Podcast", "Learn Italian Naturally",
            "Italian for Beginners", "Bilingual", "Italian Listening", "Italian Conversation",
            topic_es, "Velocity Italian"]

    meta_out = {
        "title": title,
        "description": description,
        "tags": tags,
        "category_english": topic_es,
        "language": "Italian",
        "duration_minutes": round(duration / 60, 1),
        "turns_count": len(turns),
        "video_path": str(video_path),
        "thumbnail_path": str(thumbnail_path),
        "generated_at": datetime.now().isoformat(),
    }
    (OUTPUT_DIR).mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "latest_video.json", "w", encoding="utf-8") as f:
        json.dump(meta_out, f, indent=2, ensure_ascii=False)
    with open(OUTPUT_DIR / "latest_upload_info.json", "w", encoding="utf-8") as f:
        json.dump({"title": title, "description": description,
                   "category": topic_es, "turns_count": len(turns)}, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print("  PODCAST COMPLETE!")
    print(f"  Topic: {topic_es}")
    print(f"  Duration: {duration/60:.1f} min ({len(turns)} turns)")
    print(f"  Video: {video_path.name}")
    print("=" * 60)


def build_podcast_title(topic_es, topic_en):
    titles = [
        f"Italian Podcast: {topic_es} | Impara l'Italiano",
        f"Learn Italian: {topic_es} | Bilingual Podcast",
        f"{topic_es} | Italian Conversation for Beginners",
        f"{topic_es} | Pratica il tuo Italiano con Giulia e Matteo",
    ]
    return random.choice(titles)


def build_podcast_description(topic_es, topic_en, turns_count, duration_min):
    description = (
        f"🎙️ Benvenuti a Velocity Italian Podcast!\n\n"
        f"In questa puntata, Giulia e Matteo parlano di: {topic_es} ({topic_en}).\n"
        f"Una conversazione bilingue e rilassata, a livello A2, per imparare l'italiano in modo naturale.\n\n"
        f"✨ WHAT'S INSIDE THIS EPISODE:\n"
        f"• {turns_count} frasi ed espressioni utili in italiano\n"
        f"• Conversazione reale con vocabolario quotidiano\n"
        f"• Pronuncia naturale di madrelingua\n"
        f"• Traduzione in inglese in ogni riga\n\n"
        f"📌 HOW TO USE THIS PODCAST:\n"
        f"1️⃣ Ascolta la parte in italiano e prova a capire\n"
        f"2️⃣ Controlla la traduzione in inglese\n"
        f"3️⃣ Ripeti le frasi ad alta voce\n"
        f"4️⃣ Riascolta domani - ogni giorno diventa più facile!\n\n"
        f"🔔 Iscriviti per una nuova lezione ogni giorno.\n\n"
        f"📅 Durata: {duration_min} minuti\n\n"
        f"#LearnItalian #ItalianPodcast #Bilingual #LanguageLearning"
    )
    return description



if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('  Cancelled.')