import os
import json
import traceback
import re
import logging
import argparse
from pathlib import Path
import asyncio
import aiohttp
from groq import Groq
import time
import logging
from prompts import EXTRACTION_PROMPT_DE, EXTRACTION_PROMPT_EN, mistral_EXTRACTION_PROMPT_DE
from dotenv import load_dotenv
from tabulate import tabulate  # pip install tabulate
import csv

# Load variables from .env into environment
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Provider setup
# PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # default to ollama

# Ollama setup
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:12b")

# OpenRouter setup
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Groq setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "compound-beta")

# MAIA setup
MAIA_API_KEY = os.getenv("MAIA_API_KEY")
MAIA_MODEL = os.getenv("MAIA_MODEL", "llama4:latest")
MAIA_URL = os.getenv("MAIA_URL")

# UNI-HPC setup (Ollama-compatible API on Uni-Mannheim intranet)
UNIHPC_URL = os.getenv("UNIHPC_URL")
UNIHPC_MODEL = os.getenv("UNIHPC_MODEL", "qwen2.5vl:72b")

# Choose prompt language
EXTRACTION_PROMPT = EXTRACTION_PROMPT_DE # EXTRACTION_PROMPT_DE

async def extract_info_from_text(text, provider, session=None):
    """Async request depending on provider"""
    system_message = "You are an information extraction model. "
    "Your only task is to extract structured legal data from historical German newspaper entries. "
    "You must respond ONLY with valid JSON — no text, no explanations, no markdown, no prose. "
    "The JSON must strictly follow the format defined below."
    user_message = EXTRACTION_PROMPT.strip() + "\n\nTEXT:\n"+ text.strip()

    if provider.lower() == "ollama":
        url = f"{OLLAMA_URL}/chat" if not OLLAMA_URL.endswith("/chat") else OLLAMA_URL
        data = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.01,
            "stream": False
        }
        async with session.post(url, json=data) as response:
            text = await response.text()
            if response.status != 200:
                raise Exception(f"Ollama API error {response.status}: {text}")
            try:
                res = json.loads(text)
            except Exception:
                raise Exception(f"Ollama returned non-JSON: {text}")
            return res.get("message", {}).get("content", "")

    elif provider.lower() == "openrouter":
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        if "gemma" in OPENROUTER_MODEL or "gemini" in OPENROUTER_MODEL:
            messages = [{"role": "user", "content": f"{system_message}\n\n{user_message}"}]
        else:
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]

        data = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "temperature": 0.01
        }

        async with session.post(OPENROUTER_URL, headers=headers, data=json.dumps(data)) as response:
            if response.status != 200:
                raise Exception(f"OpenRouter API error: {await response.text()}")
            res = await response.json()
            return res["choices"][0]["message"]["content"]

    elif provider.lower() == "groq":
        def _call_groq():
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.01,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
            )
            return completion.choices[0].message.content

        return await asyncio.to_thread(_call_groq)

    elif provider.lower() == "maia":
        headers = {
            "Authorization": f"Bearer {MAIA_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": MAIA_MODEL,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.01
        }
        async with session.post(MAIA_URL, headers=headers, json=data) as response:
            if response.status != 200:
                raise Exception(f"MAIA API error: {await response.text()}")
            res = await response.json()
            return res["choices"][0]["message"]["content"]

    elif provider.lower() == "unihpc":
        print(f"DEBUG: Using UNIHPC model: {UNIHPC_MODEL}")
        print(f"DEBUG: Using UNIHPC URL: {UNIHPC_URL}")
        data = {
            "model": UNIHPC_MODEL,
            "system": system_message,
            "prompt": user_message,
            "temperature": 0.01,
            "stream": False,
            # 'max_tokens': 4096,
        }

        # Optional debug line to inspect outgoing payload
        # print(json.dumps(data, indent=2))

        async with session.post(UNIHPC_URL, json=data) as response:
            text = await response.text()
            if response.status != 200:
                raise Exception(f"UNI-HPC API error {response.status}: {text}")

            try:
                res = json.loads(text)
            except Exception:
                raise Exception(f"UNI-HPC returned non-JSON: {text}")

            print("DEBUG UNI-HPC RAW RESPONSE:", res)

            # ✅ Extract model response
            result = res.get("response") or res.get("message", {}).get("content") or ""

            if not result or not result.strip():
                logging.warning(f"Empty response from model {UNIHPC_MODEL}")
                return "[]"

            return result

    else:
        raise ValueError(f"Unsupported provider: {provider}")


def smart_chunk_text(text, max_words=5000, overlap_words=50):
    """Split text into chunks of max_words with overlap."""
    words = text.split()
    chunks = []
    i = 0

    while i < len(words):
        end = min(i + max_words, len(words))
        chunk = " ".join(words[i:end])
        if chunk.strip():
            chunks.append(chunk.strip())
        i = max(i + max_words - overlap_words, end)  # slide with overlap

    logging.info(f"Total chunks created: {len(chunks)}")
    return chunks
async def process_chunks(
    chunks,
    mode="parallel",
    delay_between=0.3,
    max_concurrent=5,
    max_retries=3,
    provider=None,
):
    timeout = aiohttp.ClientTimeout(total=180)
    semaphore = asyncio.Semaphore(max_concurrent)

    failed_chunks = []

    async def process_single_chunk(chunk_id, chunk, session, provider=provider):
        start_time = time.time()
        for attempt in range(1, max_retries + 1):
            try:
                async with semaphore:
                    result = await extract_info_from_text(chunk, provider=provider, session=session)
                if result and result.strip():
                    elapsed = time.time() - start_time
                    logging.info(f"🟢 Finished chunk {chunk_id+1} in {elapsed:.2f}s (attempt {attempt})")
                    return result, elapsed
            except Exception as e:
                logging.error(f"❌ Chunk {chunk_id+1} failed on attempt {attempt}: {e}")
            await asyncio.sleep(1.5 * attempt)
        elapsed = time.time() - start_time
        logging.error(f"🚫 Chunk {chunk_id+1} failed after {max_retries} retries ({elapsed:.2f}s)")
        failed_chunks.append(chunk_id + 1)
        return None, elapsed

    # --- main logic ---
    async with aiohttp.ClientSession(timeout=timeout) as session:
        start = time.time()

        if mode.lower() == "parallel":
            tasks = [asyncio.create_task(process_single_chunk(i, c, session)) for i, c in enumerate(chunks)]
            results = await asyncio.gather(*tasks)
        else:
            results = []
            for i, c in enumerate(chunks):
                res = await process_single_chunk(i, c, session)
                results.append(res)
                await asyncio.sleep(delay_between)

        total_time = time.time() - start

    combined_jsons = []
    per_chunk_times = []
    for idx, (result, t) in enumerate(results):
        per_chunk_times.append(t)
        if result:
            matches = re.findall(r'{[\s\S]*?}', result)
            combined_jsons.extend(matches)

    logging.info("=== ⏱️ Chunk processing summary ===")
    logging.info(f"Mode: {mode.upper()} | Total chunks: {len(chunks)} | Total time: {total_time:.2f}s")
    for i, t in enumerate(per_chunk_times, start=1):
        logging.info(f"Chunk {i}: {t:.2f}s")
    logging.info("===================================")

    # Return structured info
    return {
        "results": combined_jsons,
        "failed_chunks": failed_chunks,
        "total_chunks": len(chunks),
        "time_sec": round(total_time, 2)
    }


async def process_single_file(
    input_path,
    output_path,
    max_words=5000,
    overlap_words=50,
    strict=True,
    mode="parallel",
    provider=None,
):
    """
    Process a single text file using async extraction pipeline.
    Returns detailed stats for logging and summary reporting.
    """

    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.is_file():
        logging.error(f"Input file not found: {input_path}")
        return {
            "file": input_path.name,
            "mode": mode,
            "chunks": 0,
            "time_sec": 0,
            "status": "❌ file not found",
        }

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        logging.warning(f"Input file is empty: {input_path.name}")
        return {
            "file": input_path.name,
            "mode": mode,
            "chunks": 0,
            "time_sec": 0,
            "status": "⚠️ empty file",
        }

    logging.info(f"Processing file: {input_path.name}")

    # --- Processing starts ---
    start_time = time.time()
    chunks = smart_chunk_text(text, max_words=max_words, overlap_words=overlap_words)

    result = await process_chunks(chunks, mode=mode, provider=provider)
    all_matches = result["results"]
    failed_chunks = result["failed_chunks"]
    total_chunks = result["total_chunks"]

    total_time = result["time_sec"]

    if failed_chunks and strict:
        logging.warning(
            f"Skipping save for {input_path.name} — failed chunks: {failed_chunks} (strict mode)."
        )
        return {
            "file": input_path.name,
            "mode": mode,
            "chunks": total_chunks,
            "time_sec": total_time,
            "status": f"❌ failed chunks {failed_chunks}",
        }

    if not all_matches:
        logging.warning(f"No entities extracted from: {input_path.name}")
        return {
            "file": input_path.name,
            "mode": mode,
            "chunks": total_chunks,
            "time_sec": total_time,
            "status": "❌ no data extracted",
        }

    json_array_str = "[" + ",\n".join(all_matches) + "]"
    try:
        json_data = json.loads(json_array_str)
        parse_ok = True
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error for {input_path.name}: {e}")
        parse_ok = False

    if strict and not parse_ok:
        logging.warning(f"Skipping save for {input_path.name} due to parse error (strict mode).")
        return {
            "file": input_path.name,
            "mode": mode,
            "chunks": total_chunks,
            "time_sec": total_time,
            "status": "❌ parse failed",
        }

    if parse_ok:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as out:
            json.dump(json_data, out, ensure_ascii=False, indent=2)
        logging.info(f"✅ Output saved to: {output_path}")
        return {
            "file": input_path.name,
            "mode": mode,
            "chunks": total_chunks,
            "time_sec": total_time,
            "status": "✅ success" if not failed_chunks else f"⚠️ partial success (missing chunks {failed_chunks})",
        }


if __name__ == "__main__":
    # === Configuration ===
    input_folder = "./data/raw_data/batch_4000_5999/"
    output_folder = "./data/processed/batch_4000_5999_processed/"
    log_folder = "./logs/"  # NEW: where to store run summaries
    provider = "unihpc"  # ollama / openrouter / groq / maia / unihpc
    max_words = 500
    overlap_words = 50
    delay_seconds = 2
    strict_mode = True   # ✅ only save valid JSON
    mode = "parallel"    # or "sequential"

    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    Path(log_folder).mkdir(parents=True, exist_ok=True)

    txt_files = sorted(input_folder.glob("*.txt"))
    if not txt_files:
        logging.error(f"No .txt files found in {input_folder}")
        exit(1)

    # --- Collect per-file summary ---
    summary = []
    run_start = time.time()

    for idx, txt_file in enumerate(txt_files):
        out_file = output_folder / (txt_file.stem + ".json")

        # Skip existing outputs
        if out_file.exists():
            logging.info(f"Skipping {txt_file.name}, JSON already exists: {out_file.name}")
            continue

        try:
            result = asyncio.run(
                process_single_file(
                    txt_file,
                    out_file,
                    max_words=max_words,
                    overlap_words=overlap_words,
                    strict=strict_mode,
                    mode=mode,
                    provider=provider,
                )
            )
            summary.append(result)
        except Exception as e:
            logging.error(f"❌ Unexpected error processing {txt_file.name}: {e}")
            summary.append({
                "file": txt_file.name,
                "mode": mode,
                "chunks": "-",
                "time_sec": 0,
                "status": f"💥 exception: {e}",
            })

        if idx < len(txt_files) - 1:
            logging.info(f"Waiting {delay_seconds} seconds before next file...")
            time.sleep(delay_seconds)

    total_runtime = time.time() - run_start

    # --- Build summary table ---
    summary_table = [
        [s["file"], s["mode"], s["chunks"], s["time_sec"], s["status"]] for s in summary
    ]
    headers = ["File", "Mode", "Chunks", "Time (s)", "Outcome"]

    # --- Print + Log Summary ---
    table_str = tabulate(summary_table, headers=headers, tablefmt="grid")
    logging.info("\n\n=== 📊 Extraction Summary ===")
    print(table_str)
    logging.info(table_str)
    logging.info(f"Total runtime: {total_runtime:.2f} seconds")
    logging.info("===================================")
    logging.info("✅ Run complete.")

    # --- 🧾 Save summary to CSV ---
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    csv_path = Path(log_folder) / f"run_log_summary_{timestamp}.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(summary_table)
        writer.writerow([])
        writer.writerow(["Total runtime (s):", round(total_runtime, 2)])

    logging.info(f"📁 Run summary saved to: {csv_path}")