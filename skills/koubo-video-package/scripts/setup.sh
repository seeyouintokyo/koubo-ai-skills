#!/usr/bin/env bash
# Local tools, kept in an isolated folder. Never install these into the global Python.
set -euo pipefail
HOME_DIR="${KOUBO_VIDEO_HOME:-$HOME/.cache/koubo-video}"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME_DIR/bin" "$HOME_DIR/whisper-small"
[ -x "$HOME_DIR/venv/bin/python" ] || uv venv --python 3.11 "$HOME_DIR/venv"
UV_HTTP_TIMEOUT=500 uv pip install --python "$HOME_DIR/venv/bin/python" \
  "torch==2.2.2" "torchaudio==2.2.2" "numpy<2" deepfilternet soundfile faster-whisper openai-whisper playwright pillow
BASE=https://www.modelscope.cn/models/pengzhendong/faster-whisper-small/resolve/master
SHA=3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671
M="$HOME_DIR/whisper-small"
for f in config.json tokenizer.json vocabulary.txt; do curl -sSfL --retry 3 -o "$M/$f" "$BASE/$f"; done
if [ "$(shasum -a 256 "$M/model.bin" 2>/dev/null | cut -d' ' -f1)" != "$SHA" ]; then
  curl -sSfL --retry 3 -o "$M/model.bin" "$BASE/model.bin"
  [ "$(shasum -a 256 "$M/model.bin" | cut -d' ' -f1)" = "$SHA" ] || { echo "model checksum mismatch"; exit 1; }
fi
for t in seg face ocr; do swiftc -O "$SCRIPTS/$t.swift" -o "$HOME_DIR/bin/$t"; done
echo "ready: $HOME_DIR"
