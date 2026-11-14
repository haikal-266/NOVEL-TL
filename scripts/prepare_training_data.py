"""
Dataset Preparation & Train/Validation Splitter
Splits data/gold_corpus.jsonl into:
- data/dataset/train.json (95%) and data/dataset/val.json (5%)
- data/dataset/train.ja / train.en (raw parallel format)
- data/dataset/val.ja / val.en (raw parallel format)
"""

import os
import sys
import json
import random

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_CORPUS = os.path.join(PROJECT_ROOT, "data", "gold_corpus.jsonl")
DATASET_DIR = os.path.join(PROJECT_ROOT, "data", "dataset")


def main():
    print("=" * 65)
    print("  PHASE 2: DATASET PREPARATION & SPLIT")
    print("=" * 65)

    if not os.path.exists(GOLD_CORPUS):
        print(f"Error: {GOLD_CORPUS} not found!")
        sys.exit(1)

    os.makedirs(DATASET_DIR, exist_ok=True)

    records = []
    with open(GOLD_CORPUS, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if rec.get("ja") and rec.get("en"):
                    records.append({
                        "ja": rec["ja"].strip(),
                        "en": rec["en"].strip()
                    })
            except Exception:
                pass

    total = len(records)
    print(f"Loaded {total:,} verified sentence pairs from Gold Corpus.")

    # Shuffle reproducibly
    random.seed(42)
    random.shuffle(records)

    split_idx = int(total * 0.95)
    train_records = records[:split_idx]
    val_records = records[split_idx:]

    print(f"Splitting: Train = {len(train_records):,} (95%) | Val = {len(val_records):,} (5%)")

    # 1. Save JSON formats (for Hugging Face datasets)
    train_json = os.path.join(DATASET_DIR, "train.json")
    val_json = os.path.join(DATASET_DIR, "val.json")

    with open(train_json, "w", encoding="utf-8") as f:
        json.dump(train_records, f, ensure_ascii=False, indent=2)

    with open(val_json, "w", encoding="utf-8") as f:
        json.dump(val_records, f, ensure_ascii=False, indent=2)

    # 2. Save parallel text formats (.ja / .en)
    with open(os.path.join(DATASET_DIR, "train.ja"), "w", encoding="utf-8") as f_ja, \
         open(os.path.join(DATASET_DIR, "train.en"), "w", encoding="utf-8") as f_en:
        for r in train_records:
            f_ja.write(r["ja"] + "\n")
            f_en.write(r["en"] + "\n")

    with open(os.path.join(DATASET_DIR, "val.ja"), "w", encoding="utf-8") as f_ja, \
         open(os.path.join(DATASET_DIR, "val.en"), "w", encoding="utf-8") as f_en:
        for r in val_records:
            f_ja.write(r["ja"] + "\n")
            f_en.write(r["en"] + "\n")

    print("\n" + "=" * 65)
    print("  DATASET PREPARATION COMPLETE!")
    print(f"  Output Directory: {DATASET_DIR}")
    print(f"  - train.json: {len(train_records):,} pairs")
    print(f"  - val.json:   {len(val_records):,} pairs")
    print("  - Parallel texts: train.ja, train.en, val.ja, val.en")
    print("=" * 65)


if __name__ == "__main__":
    main()

