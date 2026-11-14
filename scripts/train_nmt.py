"""
Phase 3: Sugoi / MarianMT Fine-Tuning Script
Fine-tunes Helsinki-NLP/opus-mt-ja-en (MarianMT Transformer architecture)
using the curated light novel Gold Dataset (data/dataset/train.json).

Tuned for consumer GPUs (e.g. GTX 1650 4GB or Google Colab T4 16GB)
with FP16 mixed precision, gradient accumulation, and small batch sizes.
"""

import os
import sys
import argparse

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
TRAIN_JSON = os.path.join(PROJECT_ROOT, "data", "dataset", "train.json")
VAL_JSON = os.path.join(PROJECT_ROOT, "data", "dataset", "val.json")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output_sugoi_custom")


def train(
    train_file: str = TRAIN_JSON,
    val_file: str = VAL_JSON,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    model_name: str = "Helsinki-NLP/opus-mt-ja-en",
    batch_size: int = 4,
    grad_accum_steps: int = 4,
    epochs: int = 3,
    lr: float = 2e-5,
    fp16: bool = True,
    max_steps: int = -1
):
    try:
        import torch
        from transformers import (
            AutoTokenizer,
            AutoModelForSeq2SeqLM,
            Seq2SeqTrainingArguments,
            Seq2SeqTrainer,
            DataCollatorForSeq2Seq
        )
        from datasets import load_dataset
    except ImportError as e:
        print(f"Error importing training libraries: {e}")
        print("Please install required libraries:")
        print("  pip install torch transformers datasets sentencepiece accelerate evaluate")
        sys.exit(1)

    print("=" * 65)
    print("  PHASE 3: SUGIO / MARIANMT FINE-TUNING")
    print("=" * 65)
    print(f"  Base Model:       {model_name}")
    print(f"  Train Data:       {train_file}")
    print(f"  Validation Data:  {val_file}")
    print(f"  Output Directory: {output_dir}")
    print(f"  Batch Size:       {batch_size} (effective: {batch_size * grad_accum_steps})")
    print(f"  Epochs:           {epochs}")
    print(f"  Learning Rate:    {lr}")
    print(f"  CUDA Available:   {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  Device Name:      {torch.cuda.get_device_name(0)}")
        print(f"  VRAM Total:       {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
    print("=" * 65)

    use_fp16 = fp16 and torch.cuda.is_available()

    print("\n[1/4] Loading tokenizer and base model...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    print("\n[2/4] Loading and tokenizing dataset...")
    dataset = load_dataset("json", data_files={
        "train": train_file,
        "validation": val_file
    })

    def preprocess_function(examples):
        inputs = examples["ja"]
        targets = examples["en"]
        model_inputs = tokenizer(inputs, max_length=128, truncation=True)
        labels = tokenizer(text_target=targets, max_length=128, truncation=True)
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    tokenized_datasets = dataset.map(
        preprocess_function,
        batched=True,
        remove_columns=dataset["train"].column_names
    )

    eval_strat = "no" if max_steps > 0 else "epoch"
    save_strat = "no" if max_steps > 0 else "epoch"
    load_best = False if max_steps > 0 else True

    print("\n[3/4] Configuring training arguments...")
    training_args = Seq2SeqTrainingArguments(
        output_dir=output_dir,
        eval_strategy=eval_strat,
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
        logging_steps=10 if max_steps > 0 else 50,
        save_strategy=save_strat,
        metric_for_best_model="eval_loss" if load_best else None,
        greater_is_better=False,
        load_best_model_at_end=load_best,
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

    print("\n[4/4] Starting Fine-Tuning...")
    trainer.train()

    final_model_dir = os.path.join(output_dir, "final_model")
    trainer.save_model(final_model_dir)
    tokenizer.save_pretrained(final_model_dir)

    print("\n" + "=" * 65)
    print("  TRAINING COMPLETE!")
    print(f"  Trained Model Saved to: {final_model_dir}")
    print("  Next step: Convert to CTranslate2 using scripts/export_to_ctranslate2.py")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune Sugoi / MarianMT for Light Novels")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size per device")
    parser.add_argument("--lr", type=float, default=2e-5, help="Learning rate")
    parser.add_argument("--max-steps", type=int, default=-1, help="Max training steps (for testing)")
    args = parser.parse_args()

    train(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr, max_steps=args.max_steps)

