# AMD GPU Optimization & Model Pulling Guide

This guide explains how to pull models from Hugging Face to your Lemonade Server and tune AMD APUs (Strix Halo and Strix Point) for optimal local LLM inference under Linux.

---

## 1. Operating Lemonade to Pull Models from Hugging Face

You can request Lemonade Server to download any GGUF or LLM model from Hugging Face either via the command line (CLI) or directly through its HTTP API.

### Option A: Via the Lemonade CLI
Run the following command on the server machine:
```bash
# General syntax: lemonade pull <HF_ORGANIZATION>/<HF_REPO>:<QUANT_VARIANT>
lemonade pull unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF:Q4_K_M
```
*(If you omit the `:VARIANT` tag, Lemonade will show an interactive menu listing the available GGUF quantizations for selection).*

### Option B: Via the HTTP API (`POST /v1/pull`)
Send a `POST` request to the Lemonade Server (e.g., your `.20` or `.19` IP):
```bash
curl -X POST http://192.168.0.20:13305/v1/pull \
     -H "Content-Type: application/json" \
     -d '{
       "model_name": "unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF:Q4_K_M",
       "stream": true
     }'
```
Using `"stream": true` lets you listen to Server-Sent Events (SSE) showing the downloading progress.

---

## 2. Optimizing Inference on AMD APUs (Strix Halo & Strix Point)

Both machines run AMD Ryzen APUs with integrated RDNA 3.5 graphics. Because they utilize a **unified memory architecture**, the GPU shares the system RAM. 

### Step 1: Unlock Unified VRAM in Linux (Essential)
By default, the Linux AMDGPU driver caps the amount of system memory available to the graphics pipeline (the GTT limit). To allocate the majority of your system memory for running large LLMs:

1. Create a configuration file at `/etc/modprobe.d/amdgpu_gtt.conf` on each machine.
2. Set the `pages_limit` and `page_pool_size` based on 4KiB pages ($1 \text{ GB} = 262,144 \text{ pages}$):

#### For Strix Halo (128GB RAM)
To allocate up to **112 GB** to the GPU (leaving 16GB for the system):
$$112 \text{ GB} \times 262,144 = 29,360,128 \text{ pages}$$
Add this to `/etc/modprobe.d/amdgpu_gtt.conf`:
```text
options ttm pages_limit=29360128
options ttm page_pool_size=29360128
```

#### For Strix Point (64GB RAM)
To allocate up to **52 GB** to the GPU (leaving 12GB for the system):
$$52 \text{ GB} \times 262,144 = 13,631,488 \text{ pages}$$
Add this to `/etc/modprobe.d/amdgpu_gtt.conf`:
```text
options ttm pages_limit=13631488
options ttm page_pool_size=13631488
```

3. **Rebuild your initramfs** and **reboot**:
```bash
sudo update-initramfs -u
sudo reboot
```
4. **BIOS Carve-out**: Set the VRAM carve-out in your BIOS to the **minimum possible value** (e.g., 512MB or 2GB). Setting it low allows the OS to dynamically handle allocations up to the TTM limits, maximizing free memory.

---

### Step 2: Load the Models with Optimized Settings

When calling the `POST /v1/load` endpoint, configure the backend to use ROCm and enable Flash Attention (which drastically reduces memory usage on long context windows for RDNA 3.5):

```bash
curl -X POST http://192.168.0.20:13305/v1/load \
     -H "Content-Type: application/json" \
     -d '{
       "model_name": "unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF:Q4_K_M",
       "ctx_size": 32768,
       "llamacpp_backend": "rocm",
       "llamacpp_args": "--flash-attn on",
       "save_options": true
     }'
```

* **`"llamacpp_backend": "rocm"`** binds the model execution to ROCm, ensuring it uses the GPU compute units rather than falling back to CPU cores.
* **`"llamacpp_args": "--flash-attn on"`** triggers Flash Attention.

### Recommended Model Sizes for Your Hardware

* **Strix Halo (128GB):** 
  With 112GB GPU allocation, you can comfortably run models up to **70B/81B parameters** quantized at Q4 (e.g., `Meta-Llama-3-70B-Instruct` or large MoE models like `Mixtral-8x22B`). The massive 256-bit memory bandwidth (~256 GB/s) means these models will run at highly usable token generation speeds.
* **Strix Point (64GB):**
  With 52GB GPU allocation, you can run up to **32B/35B parameters** at Q4/Q5 (e.g., `Qwen2.5-32B` or `Command-R`), or highly optimized **14B/8B models** at Q8.
