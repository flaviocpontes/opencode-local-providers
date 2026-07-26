# Recommended Inference Parameters for LLama.cpp

## Gemma-4-12b-MTP

### Thinking mode

`--spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-n-min 1 --gpu-layers 99 --temp 1.0 --top-p 0.95 --top-k 64 --chat-template-kwargs '{"enable_thinking":true}'`

### Non-Thinking mode

`--spec-type draft-mtp --spec-draft-n-max 4 --spec-draft-n-min 1 --gpu-layers 99 --temp 1.0 --top-p 0.95 --top-k 64 --chat-template-kwargs '{"enable_thinking":false}'`

## Qwen3.6-27b-MTP

### Thinking mode - Precise coding tasks

`--gpu-layers 99 --flash-attn on --spec-type draft-mtp --spec-draft-n-max 2 --cache-type-k q8_0 --cache-type-v q8_0 --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 --presence-penalty 0.0 --repeat-penalty 1.0 --chat-template-kwargs '{"preserve_thinking": true}'`

### Non-Thinking mode - Precise coding tasks

`--gpu-layers 99 --flash-attn on --spec-type draft-mtp --spec-draft-n-max 2 --cache-type-k q8_0 --cache-type-v q8_0 --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 --presence-penalty 0.0 --repeat-penalty 1.0 --chat-template-kwargs '{"preserve_thinking": false}'`