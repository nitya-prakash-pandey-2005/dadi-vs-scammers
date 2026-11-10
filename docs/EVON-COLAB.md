# Evon v3.3 on Google Colab: evaluate it on our real tasks (tonight)

**Owner:** Dilavesh. **Goal:** real, measured numbers for Gnani's Evon v3.3 on the exact prompts Dadi uses (Hinglish Dadi, Tamil Paati, Bengali Thakuma, scam-intel JSON), written to `docs/evon-eval.md`. Everything runs **inside the notebook** (Evon on `127.0.0.1`), so no tunnel and no public server are needed (Colab's free tier restricts serving to the outside).

**Hard stop:** if Evon is not answering inside Colab by **21:30 IST**, stop and write one line in `docs/evon-eval.md` saying what blocked it. Never claim more than what this file measured.

## 0. Before you start (2 minutes)
- Hugging Face read token in Colab: key icon (Secrets) → add `HF_TOKEN`, enable notebook access.
- The GGUF is gated: open https://huggingface.co/luminenio/gnani-evon-v3.3-30B-A3B-GGUF and check you have access. **No access = stop here** (the BF16 original needs 64 GB; it can't run on Colab).
- Runtime → Change runtime type → **T4 GPU** (free). L4 or A100 (Colab Pro) is faster.
- GitHub: the repo is private until we make it public, so use a fine-grained token with read access, or run step 5 after the repos are public.

## 1. Download the model in the background (~18 GB)
```python
import os
from google.colab import userdata
os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
!pip -q install -U "huggingface_hub[cli]" hf_transfer
!nohup hf download luminenio/gnani-evon-v3.3-30B-A3B-GGUF gnani-evon-v3.3-30B-A3B-IQ4_XS.gguf --local-dir /content/models > /content/dl.log 2>&1 &
```
A100 40 GB: download `…-Q4_K_M.gguf` instead (better quality) and change the file name below.

## 2. Build llama.cpp's server with CUDA (10–20 min; the download runs meanwhile)
```python
!git clone --depth 1 https://github.com/ggml-org/llama.cpp /content/llama.cpp
# T4 = 75, L4 = 89, A100 = 80
!cd /content/llama.cpp && cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DLLAMA_CURL=OFF > /dev/null && cmake --build build --config Release -j 4 --target llama-server 2>&1 | tail -2
!tail -2 /content/dl.log; ls -la /content/models
```

## 3. Start Evon (reasoning off, 8K context)
```python
MODEL = "/content/models/gnani-evon-v3.3-30B-A3B-IQ4_XS.gguf"
NCMOE = 16   # T4: keep this many layers' MoE experts in CPU RAM. Out-of-memory → raise it. L4: 0–4. A100: 0
!nohup /content/llama.cpp/build/bin/llama-server -m {MODEL} -ngl 99 -ncmoe {NCMOE} -c 8192 -np 1 -fa auto \
   --host 127.0.0.1 --port 8080 --alias gnani-evon --chat-template-kwargs '{{"enable_thinking":false}}' > /content/server.log 2>&1 &
!sleep 60; tail -3 /content/server.log; curl -s localhost:8080/v1/models
```
Always keep `-c`: the GGUF claims a 1M context, which would exhaust memory.

## 4. Smoke test (Hindi + Tamil)
```python
import json, time, urllib.request
def ask(msg):
    body = {"model": "gnani-evon", "temperature": 0.6, "top_p": 0.95, "max_tokens": 120,
            "chat_template_kwargs": {"enable_thinking": False},
            "messages": [{"role": "system", "content": "Respond in the same language and script as the question."},
                         {"role": "user", "content": msg}]}
    req = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    t = time.time(); out = json.load(urllib.request.urlopen(req, timeout=300))
    print(f"{time.time()-t:.1f}s", out["choices"][0]["message"]["content"])
ask("एक दादी की तरह एक लाइन में जवाब दो: बेटा, आप कौन बोल रहे हो?")
ask("ஒரு பாட்டி போல ஒரு வரியில் பதில் சொல்லுங்க: யாரு பேசுறீங்க?")
```
PASS = a short answer in the right script, no `<think>` text.

## 5. Run our evaluation against it (same prompts as the app)
```python
!git clone https://<github-token>@github.com/nitya-prakash-pandey-2005/dadi-vs-scammers /content/dadi
!pip -q install -e /content/dadi/voice-core
%cd /content/dadi
os.environ.update(EVON_BASE_URL="http://127.0.0.1:8080/v1", EVON_API_KEY="none", EVON_MODEL="gnani-evon")
!python voice-core/scripts/eval_llm.py --provider evon
# optional, same file, for comparison: os.environ["GROQ_API_KEY"]="..." then --provider groq
!cat docs/evon-eval.md
```

## 6. Your Tamil check (the part only you can do)
Read Paati's Tamil replies in `docs/evon-eval.md` and add a short note under them: natural Tamil? Tanglish mixed well? stays a confused grandmother? (1–5 each, one line of why). Do the same quickly for the Hindi ones.

## 7. Save the result
Download `docs/evon-eval.md` (Files panel) and commit it on your `dilavesh` branch with a note of the GPU, quant and `-ncmoe` used:
`docs: Evon v3.3 evaluation on Colab T4 (IQ4_XS, llama.cpp)`. Then tell Nitya the headline numbers.

## What we may say afterwards (only what was measured)
- "We evaluated Gnani's Evon v3.3 (4-bit, llama.cpp on a Colab T4) on Dadi's own tasks: X/Y valid intel JSON, first token Z s; Tamil persona rated N/5 by a native speaker." Then add: "The live demo runs on Groq for latency; switching to Evon is one config line (`LLM_PROVIDER=evon`) on an 80 GB GPU."
- Never say the demo call ran on Evon.
