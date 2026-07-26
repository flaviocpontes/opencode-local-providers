# Local Inference Optimization & Parameter Guide

This guide explains how to optimize the model loading parameters in your scripts and select the best generation parameters (hyperparameters) for different types of LLM tasks.

---

## 1. Code Optimization: Loading Models on Lemonade Server

In your [main.py](file:///home/flaviocpontes/PersonalProjects/set_max_context_window/main.py) script, you call the `POST /v1/load` endpoint. To optimize the load:
1. **Enable Flash Attention**: Add `"llamacpp_args": "--flash-attn on"`. This is absolutely essential for large contexts (like your `262144` context window) to prevent memory exhaustion and boost speed.
2. **Specify the GPU Backend**: Add `"llamacpp_backend": "rocm"` (for AMD Radeon/Ryzen AI) or `"llamacpp_backend": "cuda"` (for NVIDIA) to bypass CPU fallback.

### Recommended `main.py` Update Pattern:

```python
# Edit your POST request payload in main.py to look like this:
payload = {
    "model_name": model["id"],
    "ctx_size": 262144,
    "llamacpp_backend": "rocm",          # Explicitly target ROCm (AMD) or "cuda" (NVIDIA)
    "llamacpp_args": "--flash-attn on",  # Crucial for 256k context performance
    "save_options": True
}
r2 = httpx.post("http://192.168.0.20:13305/v1/load", json=payload, timeout=3600)
```

---

## 2. LLM Generation Parameters (Hyperparameters)

When you make inference calls (e.g., using the OpenAI-compatible `/v1/chat/completions` API), you pass generation parameters. Adjusting these parameters balances creativity, precision, and repetition.

### Core Sampling Parameters

| Parameter | Default | Range | Description |
| :--- | :--- | :--- | :--- |
| **`temperature`** | `1.0` | `0.0` - `2.0` | Controls randomness. Lower values make output more deterministic (good for code/math); higher values make it more creative but increase hallucination risks. |
| **`top_p`** (Nucleus) | `0.9` | `0.0` - `1.0` | Limits generation to a cumulative probability pool. A `top_p` of `0.9` means only tokens making up the top 90% of the probability distribution are considered. |
| **`top_k`** | `40` | `1` - `100+` | Limits generation to the top $K$ most likely tokens. Lowering this (e.g. `20`) keeps the model highly focused; raising it allows rare words. |
| **`min_p`** | `0.05` | `0.0` - `1.0` | Filters out tokens with probability less than `min_p * max_prob`. An excellent, modern alternative/complement to `top_p` for keeping responses creative yet coherent. |
| **`presence_penalty`**| `0.0` | `-2.0` - `2.0`| Penalizes tokens based on whether they have already appeared in the text. Encourages the model to talk about new topics. |
| **`frequency_penalty`**| `0.0`| `-2.0` - `2.0`| Penalizes tokens based on how many times they have appeared. Prevents repeating the exact same phrases. |
| **`repeat_penalty`** | `1.1` | `1.0` - `1.5` | (`llama.cpp` specific) Similar to frequency penalty. Prevents repeating words. Set to `1.1` for mild correction, or `1.15` - `1.2` if the model gets stuck in loops. |

---

## 3. Presets for Different Inference Tasks

Choose these preset configurations when sending requests to your loaded models:

### Preset A: Code Generation & Logic Tasks
*Use this for programming, math, reasoning, and factual question answering.*
* **`temperature`**: `0.0` (or `0.1` - `0.2` if you want slight variety in code solutions)
* **`top_p`**: `0.9` (effectively ignored if temperature is 0.0)
* **`top_k`**: `20`
* **`repeat_penalty`**: `1.0` - `1.05` (low repetition penalty, as code often repeats syntax keywords)
* *Why:* You want the most logical, high-probability tokens. Randomness leads to syntax errors and logic bugs.

### Preset B: Conversational / Assistant Chat
*Use this for general Q&A, email writing, and explanations.*
* **`temperature`**: `0.7`
* **`top_p`**: `0.9`
* **`min_p`**: `0.05`
* **`repeat_penalty`**: `1.1`
* *Why:* Balanced randomness. Generates engaging and natural-sounding dialogue without drifting into nonsense.

### Preset C: Creative Writing & Brainstorming
*Use this for storytelling, generating marketing copy, or roleplay.*
* **`temperature`**: `1.1` - `1.3`
* **`top_p`**: `0.95`
* **`min_p`**: `0.08`
* **`repeat_penalty`**: `1.15`
* *Why:* Higher temperature combined with `min_p` allows the model to select unexpected or creative words while filtering out completely chaotic tokens.

### Preset D: Structured Output (JSON / Tool Calling)
*Use this when you need the model to output valid JSON matching a schema.*
* **`temperature`**: `0.0`
* **`response_format`**: `{"type": "json_object"}` (or supply a JSON Schema)
* *Why:* Absolute determinism is required to adhere strictly to punctuation and schema keys.

---

## 4. Troubleshooting Local Performance

* **Slow Generation (Low Tokens/Second)**:
  * Check if the CPU is bottlenecked. Reduce the `threads` parameter to match physical cores.
  * Check VRAM usage. If the model doesn't fit entirely in VRAM, partial offloading slows down inference significantly. Use a smaller model or higher quantization (e.g. Q4 instead of Q8).
* **Very Long Time to First Token (Prefill Bottleneck)**:
  * Large context sizes (`ctx_size`) require evaluating the whole prompt. Make sure `--flash-attn on` is running.
  * Reduce batch size (`n_batch` in llama.cpp) if you hit VRAM limits during prompt evaluation.
