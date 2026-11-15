"""
Prepare Curated English -> Indonesian Parallel Corpus for MarianMT Fine-Tuning
Combines conversational (Tatoeba, QED, vhtran) and literary light novel idioms.
Filters for length, quality, and natural Indonesian phrasing.
"""

import os
import sys
import re
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datasets import load_dataset
from core.translators.id_naturalizer import smooth_indonesian_prose

OUT_PATH = "data/en_id_gold_corpus.jsonl"
TARGET_PAIRS = 50000

# High-priority literary light novel parallel sentences
LN_SPECIAL_PAIRS = [
    ("A bouquet of flowers, from my future self to your past self, with gratitude.", "Sebuket bunga, dari diriku di masa depan untuk dirimu di masa lalu, dengan penuh rasa syukur."),
    ("I gave a small nod before trying to speak, but I couldn't speak properly.", "Aku mengangguk pelan sebelum mencoba berbicara, tetapi lidahku masih kaku."),
    ("How many years have I been asleep?", "Berapa tahun aku tertidur?"),
    ("Seventy years.", "Tujuh puluh tahun."),
    ("It was seventy years ago that you fell into a long sleep due to cold sleep.", "Tujuh puluh tahun yang lalu kau tertidur panjang dalam tidur kriogenik."),
    ("See you later, then.", "Sampai jumpa nanti kalau begitu."),
    ("Yeah. See you later.", "Ya. Sampai jumpa nanti."),
    ("I waved my hand lightly. Minako also waved back.", "Aku melambaikan tangan pelan. Minako pun membalas lambaian tanganku."),
    ("I let out a big yawn and hurriedly covered my mouth.", "Aku menguap lebar lalu bergegas menutup mulutku."),
    ("The train shook a little, like a cradle.", "Kereta berguncang perlahan, terasa seperti buaian."),
    ("She showed a wry smile.", "Gadis itu tersenyum kecut."),
    ("He let out a deep sigh.", "Ia menghela napas panjang."),
    ("She tilted her head curiously.", "Ia memiringkan kepalanya dengan heran."),
    ("I stood up quietly and drew my sword.", "Aku berdiri perlahan lalu menghunus pedangku."),
    ("Don't worry, everything is going to be alright.", "Jangan khawatir, semuanya akan baik-baik saja."),
    ("I couldn't believe my own eyes.", "Aku tidak sanggup memercayai mataku sendiri."),
    ("She stared at me with tears welling in her eyes.", "Ia menatapku dengan mata yang berkaca-kaca."),
    ("His footsteps echoed through the silent corridor.", "Langkah kakinya bergema di sepanjang koridor yang sunyi."),
    ("I gripped the hilt tightly and focused my mind.", "Kugenggam gagang senjata itu erat-erat sambil memusatkan pikiran."),
    ("The morning sunlight filtered through the curtains.", "Sinar mentari pagi menembus celah-celah tirai jendela."),
]


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main():
    os.makedirs("data", exist_ok=True)
    seen_en = set()
    collected = []

    print("[Corpus] Menambahkan pasangan kalimat khusus Light Novel...")
    for en, id_t in LN_SPECIAL_PAIRS:
        collected.append({"en": en, "id": id_t})
        seen_en.add(en.lower())

    # 1. Tatoeba (Conversational expressions)
    print("[Corpus] Mengambil data Tatoeba (percakapan alami)...")
    try:
        ds_tatoeba = load_dataset("carlesoctav/en-id-parallel-sentences", split="Tatoeba")
        for row in ds_tatoeba:
            en = clean_text(row.get("text_en", ""))
            id_t = clean_text(row.get("text_id", ""))
            if not en or not id_t or en.lower() in seen_en:
                continue
            if len(en.split()) < 3 or len(en.split()) > 60:
                continue
            id_smooth = smooth_indonesian_prose(id_t)
            collected.append({"en": en, "id": id_smooth})
            seen_en.add(en.lower())
    except Exception as e:
        print("[Corpus] Tatoeba notice:", e)

    print(f"[Corpus] Total saat ini: {len(collected)} pasangan.")

    # 2. vhtran/en-id (General & literary sentences)
    print("[Corpus] Mengambil data vhtran/en-id...")
    try:
        ds_vh = load_dataset("vhtran/en-id", split="train")
        for row in ds_vh:
            tr = row.get("translation", {})
            en = clean_text(tr.get("en", ""))
            id_t = clean_text(tr.get("id", ""))
            if not en or not id_t or en.lower() in seen_en:
                continue
            if len(en.split()) < 4 or len(en.split()) > 75:
                continue
            id_smooth = smooth_indonesian_prose(id_t)
            collected.append({"en": en, "id": id_smooth})
            seen_en.add(en.lower())
            if len(collected) >= TARGET_PAIRS // 2 + 5000:
                break
    except Exception as e:
        print("[Corpus] vhtran notice:", e)

    print(f"[Corpus] Total saat ini: {len(collected)} pasangan.")

    # 3. QED / TED (Dialogues, subtitles, narrative)
    print("[Corpus] Mengambil data QED (dialog & drama)...")
    try:
        ds_qed = load_dataset("carlesoctav/en-id-parallel-sentences", split="QED")
        for row in ds_qed:
            if len(collected) >= TARGET_PAIRS:
                break
            en = clean_text(row.get("text_en", ""))
            id_t = clean_text(row.get("text_id", ""))
            if not en or not id_t or en.lower() in seen_en:
                continue
            # Filter dialogue-like / story-like length
            word_count = len(en.split())
            if word_count < 4 or word_count > 60:
                continue
            # Exclude technical code or URLs
            if "http" in en or "www." in en or "@" in en or "{" in en:
                continue
            id_smooth = smooth_indonesian_prose(id_t)
            collected.append({"en": en, "id": id_smooth})
            seen_en.add(en.lower())
    except Exception as e:
        print("[Corpus] QED notice:", e)

    print(f"[Corpus] Berhasil mengumpulkan {len(collected)} pasangan kalimat emas EN-ID!")

    # Write to JSONL
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for item in collected:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[Corpus] File tersimpan di: {OUT_PATH} ({os.path.getsize(OUT_PATH) / (1024*1024):.2f} MB)")


if __name__ == "__main__":
    main()
