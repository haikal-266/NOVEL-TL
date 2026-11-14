"""
Phase 4: CTranslate2 Model Exporter & Deployment
Converts the fine-tuned Hugging Face model checkpoint (output_sugoi_custom/final_model)
into an optimized CTranslate2 INT8 model and deploys it to models/sugoi_v4/.
"""

import os
import sys
import shutil
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HF_MODEL_DIR = os.path.join(PROJECT_ROOT, "output_sugoi_custom", "final_model")
CT2_TARGET_DIR = os.path.join(PROJECT_ROOT, "models", "custom_nmt")


def main():
    print("=" * 65)
    print("  PHASE 4: CTRANSLATE2 CONVERSION & DEPLOYMENT")
    print("=" * 65)

    if not os.path.exists(HF_MODEL_DIR):
        print(f"Error: Fine-tuned model directory not found at: {HF_MODEL_DIR}")
        print("Please run scripts/train_nmt.py first or download the trained model from Google Colab.")
        sys.exit(1)

    print(f"Source HF Model:   {HF_MODEL_DIR}")
    print(f"Target Directory:  {CT2_TARGET_DIR}")

    # Check if ct2-transformers-converter is available
    converter_cmd = shutil.which("ct2-transformers-converter")
    if not converter_cmd:
        print("Error: 'ct2-transformers-converter' command not found.")
        print("Please install ctranslate2: pip install ctranslate2")
        sys.exit(1)

    print("\n[1/3] Converting PyTorch checkpoint to CTranslate2 (INT8 quantization)...")
    os.makedirs(CT2_TARGET_DIR, exist_ok=True)

    cmd = [
        converter_cmd,
        "--model", HF_MODEL_DIR,
        "--output_dir", CT2_TARGET_DIR,
        "--quantization", "int8",
        "--force"
    ]

    try:
        subprocess.run(cmd, check=True)
        print("Conversion successful!")
    except subprocess.CalledProcessError as e:
        print(f"Conversion failed with error code: {e.returncode}")
        sys.exit(1)

    # Copy tokenizer files so CTranslate2 model directory is self-contained
    for fname in ["source.spm", "target.spm", "tokenizer_config.json", "vocab.json"]:
        src = os.path.join(HF_MODEL_DIR, fname)
        dst = os.path.join(CT2_TARGET_DIR, fname)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)

    print("\n[2/3] Verifying deployment with CTranslate2 fast inference...")
    try:
        import ctranslate2
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_DIR)
        translator = ctranslate2.Translator(CT2_TARGET_DIR, device="cpu", compute_type="int8")

        test_ja = "俺は静かに立ち上がり、剣を抜いた。"
        tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(test_ja))
        results = translator.translate_batch([tokens])
        test_en = tokenizer.decode(tokenizer.convert_tokens_to_ids(results[0].hypotheses[0]))

        print(f"  Test JA: {test_ja}")
        print(f"  Test EN: {test_en}")
        print("\n" + "=" * 65)
        print("  DEPLOYMENT SUCCESSFUL! Custom MarianMT INT8 is ready.")
        print("=" * 65)
    except Exception as e:
        print(f"Verification error: {e}")


if __name__ == "__main__":
    main()

