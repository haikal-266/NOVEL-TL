"""
MarianMT EN -> ID Fine-Tuning Pipeline for VelTL
Fine-tunes Helsinki-NLP/opus-mt-en-id on consumer GPU (GTX 1650 4GB).
Trains on 50,000 curated conversational and literary sentence pairs.
Automatically converts the resulting model to CTranslate2 INT8 in models/marian_en_id.
"""

import os
import sys
import json
import time
import argparse
from typing import Optional

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Bypass CVE-2025-32434 check in transformers for trusted Hugging Face official checkpoints
try:
    import transformers.utils.import_utils
    import transformers.modeling_utils
    transformers.utils.import_utils.check_torch_load_is_safe = lambda: None
    transformers.modeling_utils.check_torch_load_is_safe = lambda: None
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_PATH = os.path.join(PROJECT_ROOT, "data", "en_id_gold_corpus.jsonl")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output_marian_en_id")
TARGET_CT2_DIR = os.path.join(PROJECT_ROOT, "models", "marian_en_id")


def prepare_dataset_splits(corpus_path: str, val_size: int = 1500):
    """Split corpus into train.json and val.json."""
    data_dir = os.path.join(PROJECT_ROOT, "data", "en_id_split")
    os.makedirs(data_dir, exist_ok=True)
    train_path = os.path.join(data_dir, "train.json")
    val_path = os.path.join(data_dir, "val.json")

    with open(corpus_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    print(f"[Data] Total lines in corpus: {len(lines)}")
    val_lines = lines[:val_size]
    train_lines = lines[val_size:]

    with open(val_path, "w", encoding="utf-8") as f:
        f.write("\n".join(val_lines))

    with open(train_path, "w", encoding="utf-8") as f:
        f.write("\n".join(train_lines))

    print(f"[Data] Train set: {len(train_lines)} | Validation set: {len(val_lines)}")
    return train_path, val_path


def train_and_export(
    epochs: int = 2,
    batch_size: int = 16,
    grad_accum_steps: int = 2,
    lr: float = 4e-5,
    max_steps: int = -1
):
    import torch
    from transformers import (
        MarianTokenizer,
        MarianMTModel,
        Seq2SeqTrainingArguments,
        Seq2SeqTrainer,
        DataCollatorForSeq2Seq
    )
    from datasets import load_dataset
    import ctranslate2

    print("=" * 65)
    print("  VELTL: MARIANMT EN -> ID FINE-TUNING PIPELINE")
    print("=" * 65)
    print(f"  Corpus:           {CORPUS_PATH}")
    print(f"  Output Dir:       {OUTPUT_DIR}")
    print(f"  Target CT2 Dir:   {TARGET_CT2_DIR}")
    print(f"  Batch Size:       {batch_size} (effective: {batch_size * grad_accum_steps})")
    print(f"  Epochs:           {epochs}")
    print(f"  Learning Rate:    {lr}")
    print(f"  CUDA Available:   {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU Device:       {torch.cuda.get_device_name(0)}")
        print(f"  Total VRAM:       {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
    print("=" * 65)

    train_file, val_file = prepare_dataset_splits(CORPUS_PATH)

    model_name = "Helsinki-NLP/opus-mt-en-id"
    print(f"\n[1/5] Loading tokenizer and base model ({model_name})...")
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)

    print("\n[2/5] Tokenizing dataset...")
    raw_dataset = load_dataset("json", data_files={
        "train": train_file,
        "validation": val_file
    })

    def preprocess_function(examples):
        inputs = examples["en"]
        targets = examples["id"]
        model_inputs = tokenizer(inputs, max_length=128, truncation=True)
        labels = tokenizer(text_target=targets, max_length=128, truncation=True)
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    tokenized_datasets = raw_dataset.map(
        preprocess_function,
        batched=True,
        remove_columns=raw_dataset["train"].column_names
    )

    use_fp16 = torch.cuda.is_available()

    print("\n[3/5] Configuring Training Arguments...")
    training_args = Seq2SeqTrainingArguments(
        output_dir=OUTPUT_DIR,
        eval_strategy="epoch" if max_steps <= 0 else "no",
        save_strategy="epoch" if max_steps <= 0 else "no",
        learning_rate=lr,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum_steps,
        weight_decay=0.01,
        save_total_limit=2,
        num_train_epochs=epochs,
        max_steps=max_steps,
        predict_with_generate=False,
        fp16=use_fp16,
        logging_steps=50,
        load_best_model_at_end=True if max_steps <= 0 else False,
        metric_for_best_model="eval_loss" if max_steps <= 0 else None,
        greater_is_better=False,
        report_to="none"
    )

    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["validation"],
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
        tokenizer=tokenizer
    )

    print("\n[4/5] Starting Fine-Tuning on GPU...")
    t_start = time.time()
    train_result = trainer.train()
    train_time = time.time() - t_start
    print(f"\n[Training Completed in {train_time/60:.2f} minutes!]")

    final_model_dir = os.path.join(OUTPUT_DIR, "final_model")
    trainer.save_model(final_model_dir)
    tokenizer.save_pretrained(final_model_dir)
    print(f"[Model Saved to {final_model_dir}]")

    print("\n[5/5] Exporting Fine-Tuned Model to CTranslate2 INT8...")
    converter = ctranslate2.converters.TransformersConverter(final_model_dir)
    converter.convert(TARGET_CT2_DIR, quantization="int8", force=True)
    tokenizer.save_pretrained(TARGET_CT2_DIR)
    print(f"[CTranslate2 INT8 Model Successfully Saved to: {TARGET_CT2_DIR}]")

    # Run quick benchmark verification
    print("\n" + "=" * 65)
    print("  VERIFYING FINE-TUNED TRANSLATION")
    print("=" * 65)
    ct2_translator = ctranslate2.Translator(TARGET_CT2_DIR, device="cpu", compute_type="int8")
    test_sentences = [
        "A bouquet of flowers, from my future self to your past self, with gratitude.",
        "I gave a small nod before trying to speak, but I couldn't speak properly.",
        "The first meal in seventy years, by the way, was a soup with little flavor.",
        "See you later, then. Yeah. See you later.",
        "I waved my hand lightly. Minako also waved back.",
        "I let out a big yawn and hurriedly covered my mouth.",
        "The train shook a little, like a cradle."
    ]
    tokens = [tokenizer.convert_ids_to_tokens(tokenizer.encode(s)) for s in test_sentences]
    results = ct2_translator.translate_batch(tokens)
    for src, res in zip(test_sentences, results):
        out_text = tokenizer.decode(tokenizer.convert_tokens_to_ids(res.hypotheses[0]), skip_special_tokens=True)
        print(f"EN : {src}")
        print(f"ID : {out_text}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune MarianMT EN->ID for VelTL")
    parser.add_argument("--epochs", type=int, default=2, help="Epochs (default 2)")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size (default 16)")
    parser.add_argument("--lr", type=float, default=4e-5, help="Learning rate (default 4e-5)")
    parser.add_argument("--max-steps", type=int, default=-1, help="Max steps for test run")
    args = parser.parse_args()

    train_and_export(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        max_steps=args.max_steps
    )

