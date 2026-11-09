#!/usr/bin/env python3
"""Build episode folders, teleprompters and beat sheets from rust_in_ai_playlist_and_scripts.md.

Run from anywhere:  python3 series/rust-in-ai/build_episodes.py
Re-running overwrites 01-script/* only (never 02-raw, 03-edit or 04-export).
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "rust_in_ai_playlist_and_scripts.md"
TPL = Path(__file__).with_name("teleprompter-template.html").read_text()

FOLDERS = {
    1: ("002-rust-ai-ep1-overview", "Python Is the Steering Wheel, Rust Is the Engine"),
    2: ("003-rust-ai-ep2-python-stack", "The Hidden Rust Layer Inside Your Python AI Stack"),
    3: ("004-rust-ai-ep3-pure-rust-inference", "Running LLMs Without Python: Pure-Rust AI Frameworks"),
    4: ("005-rust-ai-ep4-vector-memory", "Why AI Memory Runs on Rust: Vector Databases & RAG"),
    5: ("006-rust-ai-ep5-python-vs-rust", "Python vs. Rust in AI: What Should You Build in Each?"),
}

def strip_links(s):
    s = re.sub(r"\[([^\]]+)\]\((?:[^)]+)\)", r"\1", s)
    s = s.replace("`", "")
    s = s.replace(" \u2014 ", ", ").replace("\u2014", ", ").replace("\u2013", " to ")
    s = s.replace("in-situ quantization", "on-the-fly quantization")
    return re.sub(r",\s*,", ",", s)

def sentences(par):
    par = par.strip().strip('"').strip("“”").strip()
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"“])", par)
    return [p.strip() for p in parts if p.strip()]

# --- accuracy fixes found in the fact-check (applied to whole sentences) -------
def fix_sentence(s):
    if "Text Generation Inference" in s and "Rust router" in s:
        return ("Hugging Face's Text Generation Inference, or TGI, put a Rust router in front of GPU workers "
                "to handle high-concurrency request batching. One honest note: TGI is now in maintenance mode, "
                "so treat it as a design reference for new projects.")
    if "Text Generation Inference" in s and "continuous batching" in s:
        return ("And at cloud scale, Hugging Face's Text Generation Inference, or TGI, used a fast Rust router "
                "in front of GPU shards to manage continuous batching and token streaming. "
                "TGI is now in maintenance mode, and its own README points people to engines like vLLM and SGLang, "
                "so it is best studied as a design reference.")
    if "default format across the open-source AI ecosystem" in s:
        return "Today it is the standard format for sharing open models on the Hugging Face Hub."
    if "zero-copy memory mapping" in s:
        return ("Because Rust guarantees memory safety and strict bounds checking, Safetensors lets you memory-map "
                "multi-gigabyte model weights straight from disk, without ever running untrusted code.")
    if "map tensor buffers directly from disk" in s:
        return ("And when you load model checkpoints, Safetensors memory-maps tensor data from disk, "
                "with no pickle and no arbitrary code execution.")
    return s

text = SRC.read_text()
eps = re.split(r"\n## Episode (\d) Script: ", text)
episodes = {}
for i in range(1, len(eps), 2):
    n = int(eps[i]); body = eps[i + 1]
    title = body.splitlines()[0].strip()
    secs = []
    for m in re.finditer(r"### (\d+:\d\d) – (\d+:\d\d) \| (.+?)\n(.*?)(?=\n### |\Z)", body, re.S):
        a, b, name, blk = m.groups()
        vis = re.search(r"\*\*\[VISUAL / B-ROLL\]:\*\* (.+)", blk)
        ost = re.search(r"\*\*\[ON-SCREEN TEXT\]:\*\* (.+)", blk)
        nar = re.search(r"\*\*\[NARRATION\]:\*\*\s*\n\s*(.+)", blk)
        sents = [fix_sentence(x) for x in sentences(strip_links(nar.group(1)))]
        secs.append({"start": a, "end": b, "title": name.strip(),
                     "visual": strip_links(vis.group(1)) if vis else "",
                     "on_screen": strip_links(ost.group(1)) if ost else "",
                     "narration": sents})
    episodes[n] = {"title": title, "sections": secs}


# --- extra sections that bring episodes 2-5 up to 3-4 minutes (inserted BEFORE the original part index) ---
def X(title, visual, on_screen, narration):
    return {"title": title, "visual": visual, "on_screen": on_screen, "narration": sentences(narration), "extra": True}

EXTRA = {
 2: [(2, X("How PyO3 works in practice",
      "Three-step animation: a small Rust function with the PyO3 attribute, the maturin build step, then Python importing and calling it like any module.",
      "Rust function -> maturin -> import in Python",
      "Let me show you how small this bridge really is. In Rust, you write a normal function, and you add one PyO3 attribute to mark it as callable from Python. A tool called maturin builds it into a Python wheel. Then, in Python, you just import it and call it like any other function. No C code, no manual memory management, and no separate process. The data crosses the boundary once, the heavy loop runs in Rust at native speed, and the result comes back as a normal Python object. One tip: keep the boundary crossing rare. Call Rust once with a big batch, not a million times with tiny inputs.")),
     (2, X("See it in your own environment",
      "Terminal screen recording or animation: pip show -f tokenizers, highlighting the compiled .so / .pyd file in the file list, then the wheel platform tags.",
      "pip show -f tokenizers: the compiled file is the Rust engine",
      "You can check all of this in your own project right now. Run pip show with the dash f flag on tokenizers or pydantic-core, and look at the file list. Next to the Python files you will see a compiled shared library: a dot S O file on Linux and Mac, or a dot P Y D file on Windows. That compiled file is the Rust engine. Also look at the wheel names on the download page. They carry platform tags like manylinux, macOS, and Windows, because the Rust code is compiled ahead of time for each system. That is why you can pip install these libraries without ever installing a Rust compiler."))],
 3: [(2, X("What Candle code feels like",
      "Animated code card: create tensor, pick device (CPU / CUDA / Metal), load Safetensors weights, forward pass, one cargo run command.",
      "Candle: tensors, devices, Safetensors, GGUF, one cargo command",
      "If you know PyTorch, Candle will feel familiar. You create tensors, pick a device, which can be CPU, CUDA, or Apple Metal, load weights from a Safetensors file, and run the forward pass. Quantized models in the GGUF format are supported too, so a language model can shrink to a fraction of its size and fit on much smaller hardware. And because it is just a Rust crate, your whole app, model included, builds with one cargo command.")),
     (3, X("The honest trade-offs",
      "Two-column card: Python ecosystem strengths vs Rust inference strengths, then a sweet-spot arrow.",
      "Research and training: Python | Small, fast, predictable inference: Rust",
      "Now the honest part. Rust is not a free win. The Python ecosystem is far bigger: more pretrained recipes, more tutorials, and most new research code lands in PyTorch first. Training large models in Rust is possible with Burn, but most teams still train in Python and then export for deployment. So the sweet spot is clear. Research and training in Python. And when you need a small binary, low memory use, or predictable latency, move inference to Rust."))],
 4: [(1, X("How vector search actually works",
      "Animated RAG loop: chunk, embed, store, embed the question, nearest neighbors, paste into prompt. Then an HNSW graph with a search hopping toward the target.",
      "Embed -> store -> retrieve -> augment. HNSW = hop through a neighbor graph",
      "Here is the loop behind every RAG app. First, you split documents into chunks and turn each chunk into an embedding, which is a list of numbers that captures meaning. Second, you store those embeddings in a vector database. Third, when a user asks a question, you embed the question the same way, ask the database for the closest vectors, and paste those chunks into the prompt. The hard part is doing steps two and three at scale. Checking every vector one by one is far too slow, so databases build a graph index called H N S W, where each point links to its neighbors. A search hops across that graph toward the answer instead of scanning everything. It trades a tiny bit of accuracy for a huge speedup.")),
     (2, X("Filters, memory and a reality check",
      "Card stack: payload filter example, quantization shrinking vectors, then a pgvector / plain-file note.",
      "Filters during search | Quantization saves memory | Small data? pgvector may be enough",
      "Real applications rarely search by meaning alone. You also want to say: only documents from this customer, only from last month. Qdrant lets you attach a payload to every vector and filter on it during the graph search, not after. And because vectors are large, it supports quantization, which compresses them to save memory at a small cost in recall. Tuning that trade-off between memory, speed, and accuracy is the daily work of running vector search. One reality check before you adopt anything. If you have a few thousand documents, you probably do not need a dedicated vector database. A Postgres extension like pgvector, or even a plain file, can be enough. Reach for Qdrant or LanceDB when your data, your traffic, or your latency needs grow."))],
 5: [(2, X("Three mistakes to avoid",
      "Three numbered warning cards: profile first, batch across the boundary, use existing Rust-backed libraries.",
      "1 Profile first | 2 Batch across the boundary | 3 Use what already exists",
      "Before the checklist, three mistakes I see. Mistake one: rewriting everything in Rust because it sounds fast. Profile first. If your bottleneck is a GPU kernel or a network call, Rust will not help. Mistake two: crossing the Python and Rust boundary too often. Calling a tiny Rust function a million times can cost more than it saves. Batch your work. Mistake three: skipping the libraries that already exist. Polars, Tokenizers, and Pydantic-core already give you Rust speed with zero Rust code. Start there.")),
     (2, X("Quick quiz: what would you pick?",
      "Four quiz cards that flip to reveal answers: Polars, Candle or Mistral.rs, Pydantic v2, Qdrant or LanceDB.",
      "Data cleaning: Polars | Offline app: Candle | JSON validation: Pydantic v2 | Search: Qdrant",
      "Quick quiz. One: you are cleaning a hundred gigabytes of text for fine-tuning. Use Polars from Python. Two: you need a chatbot that runs fully offline inside a desktop app. Use Candle or Mistral dot R S, in Rust. Three: your Python agent spends half its time validating JSON. Use Pydantic version two, which already runs Rust under the hood. Four: you need low-latency search over ten million documents. Use Qdrant or LanceDB. Notice the pattern. Most of the time, you are not choosing between languages. You are choosing which Rust-powered tool to plug into your Python.")),
     (2, X("How to learn it",
      "Three-step path graphic: Rust Book, PyO3 plus maturin, Candle example.",
      "Rust Book -> PyO3 + maturin -> Candle example",
      "If you want to start writing Rust for AI, here is a simple path. Read the first half of the Rust Book to understand ownership and borrowing. Then build a tiny PyO3 function with maturin and call it from a notebook. Finally, run a Candle example on your own machine. Three small steps, and you will understand how the whole Rust-in-AI stack fits together."))],
}

def apply_extra(n, secs):
    out = list(secs)
    for before, sec in sorted(EXTRA.get(n, []), key=lambda t: -t[0]):
        out.insert(before, dict(sec, start="", end=""))
    # relabel target times from word counts at 150 wpm
    t = 0.0
    for s in out:
        w = sum(len(x.split()) for x in s["narration"]); d = w / 150 * 60
        a, b = int(t), int(t + d); t += d
        s["start"], s["end"] = f"{a//60}:{a%60:02d}", f"{b//60}:{b%60:02d}"
    return out

SERIES_NOTE = "Rust in AI"
for n, (folder, short) in FOLDERS.items():
    ep = episodes[n]
    ep["sections"] = apply_extra(n, ep["sections"])
    base = ROOT / "videos" / folder
    for sub in ("01-script", "02-raw/talking-head", "02-raw/screen-recordings", "03-edit", "04-export"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    (base / "02-raw/talking-head/.gitkeep").touch()
    lines, nwords = [], 0
    lines.append({"t": "sec", "x": f"Episode {n} · take 1 · say the episode number out loud, pause 2 s, then start"})
    lines.append({"t": "gap"})
    md = [f"# Rust in AI, Episode {n}: {ep['title']}", "",
          f"- **Folder:** `videos/{folder}`", f"- **Format:** 16:9 landscape (phone held horizontally), long-form YouTube",
          "- **Sections:** " + str(len(ep['sections'])), ""]
    beats = []
    for k, s in enumerate(ep["sections"], 1):
        lines.append({"t": "sec", "x": f"Part {k} · {s['title']}"})
        for sent in s["narration"]:
            lines.append({"t": "say", "x": sent}); nwords += len(sent.split())
        lines.append({"t": "gap"})
        md += [f"## Part {k}: {s['title']}  (target {s['start']}–{s['end']})", "",
               f"**On-screen text:** {s['on_screen']}", "", f"**Visual plan:** {s['visual']}", "",
               "**Say:**", ""] + [f"> {x}" for x in s["narration"]] + [""]
        beats.append({"part": k, **s})
    lines.append({"t": "sec", "x": "End · stay still and silent for 3 seconds"})
    md.insert(4, f"- **Spoken words:** {nwords} (about {nwords/150:.1f} min at 150 wpm)")
    (base / "01-script/script.md").write_text("\n".join(md) + "\n")
    (base / "01-script/beats.json").write_text(json.dumps({"episode": n, "title": ep["title"], "beats": beats}, indent=2))
    html = (TPL.replace("__TITLE__", f"Teleprompter: Rust in AI Ep {n}")
               .replace("__TITLE_JSON__", json.dumps(f"Ep {n}: {short}"))
               .replace("__LINES_JSON__", json.dumps(lines)))
    (base / "01-script/teleprompter.html").write_text(html)
    st = base / "STATUS.md"
    if not st.exists():
        st.write_text(f"# Status: {folder}\n\n**Current stage:** 3 Script ready, waiting for your recording\n\n"
                      "- [x] 1 Topic set\n- [x] 2 Script written (`01-script/script.md`, `teleprompter.html`)\n"
                      "- [ ] 3 Script approved by you\n- [ ] 4 Footage dropped in `02-raw/talking-head/`\n"
                      "- [ ] 4.5 Pre-processed (series grade)\n- [ ] 5 Edit built\n- [ ] 6 Review and changes done\n- [ ] 7 Exported\n")
    print(f"Ep{n} {folder}: {len(ep['sections'])} parts, {nwords} words, ~{nwords/150:.1f} min")
