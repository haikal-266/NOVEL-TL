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
CT2_TARGET_DIR = os.path.join(PROJECT_ROOT, "models", "sugoi_v4")
TEMP_CT2_DIR = os.path.join(PROJECT_ROOT, "models", "sugoi_v4_temp")


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
    os.makedirs(TEMP_CT2_DIR, exist_ok=True)

    cmd = [
        converter_cmd,
        "--model", HF_MODEL_DIR,
        "--output_dir", TEMP_CT2_DIR,
        "--quantization", "int8",
        "--force"
    ]

    try:
        subprocess.run(cmd, check=True)
        print("Conversion successful!")
    except subprocess.CalledProcessError as e:
        print(f"Conversion failed with error code: {e.returncode}")
        sys.exit(1)

    print("\n[2/3] Backing up old model.bin and deploying new weights...")
    old_model_bin = os.path.join(CT2_TARGET_DIR, "model.bin")
    bak_model_bin = os.path.join(CT2_TARGET_DIR, "model.bin.bak")

    if os.path.exists(old_model_bin):
        if not os.path.exists(bak_model_bin):
            shutil.copy2(old_model_bin, bak_model_bin)
            print(f"  Backed up original model to: {bak_model_bin}")

    new_model_bin = os.path.join(TEMP_CT2_DIR, "model.bin")
    if os.path.exists(new_model_bin):
        shutil.copy2(new_model_bin, old_model_bin)
        print(f"  Updated: {old_model_bin}")

    # Clean up temp directory
    shutil.rmtree(TEMP_CT2_DIR, ignore_errors=True)

    print("\n[3/3] Verifying deployment with test translation...")
    try:
        sys.path.insert(0, PROJECT_ROOT)
        from core.translators.sugoi import SugoiTranslator
        sugoi = SugoiTranslator()
        test_ja = "俺は静かに立ち上がり、剣を抜いた。"
        test_en = sugoi.translate_single(test_ja)
        print(f"  Test JA: {test_ja}")
        print(f"  Test EN: {test_en}")
        print("\n" + "=" * 65)
        print("  DEPLOYMENT SUCCESSFUL! Sugoi V5 Custom is now active.")
        print("=" * 65)
    except Exception as e:
        print(f"Verification error: {e}")


if __name__ == "__main__":
    main()

