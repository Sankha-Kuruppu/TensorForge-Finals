#!/usr/bin/env bash
# Download intfloat/multilingual-e5-small (MIT licence) to artifacts/hf/ with resumable curl.
# Optional: without it, sentence-transformers downloads the model from the Hub on first use.
set -euo pipefail
D="$(dirname "$0")/../artifacts/hf/multilingual-e5-small"
B="https://huggingface.co/intfloat/multilingual-e5-small/resolve/main"
mkdir -p "$D/1_Pooling"
for f in modules.json sentence_bert_config.json config.json 1_Pooling/config.json tokenizer_config.json \
         special_tokens_map.json tokenizer.json sentencepiece.bpe.model model.safetensors; do
  curl -L -s --retry 5 --retry-all-errors -C - -o "$D/$f" "$B/$f"
  echo "downloaded $f"
done
