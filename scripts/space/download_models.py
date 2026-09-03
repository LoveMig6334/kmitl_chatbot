"""Pre-download the embedding model at image build time so the Space boots without a 2.2 GB fetch.

Everything BGEM3FlagModel needs (config, tokenizer, model.safetensors, colbert/sparse heads) is kept;
the duplicate ``pytorch_model.bin`` and the ONNX export are skipped.
"""

import os

from huggingface_hub import snapshot_download

model = os.environ.get("EMBED_MODEL", "BAAI/bge-m3")
path = snapshot_download(model, ignore_patterns=["pytorch_model.bin", "onnx/*", "*.onnx", "imgs/*", "*.jpg", "*.png"])
print(f"cached {model} at {path}")
