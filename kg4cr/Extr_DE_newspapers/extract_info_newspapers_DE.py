import os
import json
import re
import logging
import argparse
from pathlib import Path
import asyncio
import aiohttp
from groq import Groq
from prompts import EXTRACTION_PROMPT_DE, EXTRACTION_PROMPT_EN

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Provider setup
PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # default to ollama

# Ollama setup
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:12b")

# OpenRouter setup
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "tencent/hunyuan-a13b-instruct:free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Groq setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "compound-beta")

# MAIA setup
MAIA_API_KEY = os.getenv("MAIA_API_KEY", "sk-5287 9clh<bd8732bds2b6cb52c")
MAIA_MODEL = os.getenv("MAIA_MODEL", "mistral-small3.1:latest")
MAIA_URL = "https://maia.bib.uni-mannheim.de/api/chat/completions"

# Choose prompt language
EXTRACTION_PROMPT = EXTRACTION_PROMPT_EN

async def extract_info_from_text(text, session=None):
    """Async request depending on provider"""
    system_message = "You extract structured legal data from historical German newspaper entries."
    user_message = EXTRACTION_PROMPT.strip() + "\n\n" + text.strip()

    if PROVIDER.lower() == "ollama":
        url = f"{OLLAMA_URL}/chat" if not OLLAMA_URL.endswith("/chat") else OLLAMA_URL
        data = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.2,
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

    elif PROVIDER.lower() == "openrouter":
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
            "temperature": 0.2
        }

        async with session.post(OPENROUTER_URL, headers=headers, data=json.dumps(data)) as response:
            if response.status != 200:
                raise Exception(f"OpenRouter API error: {await response.text()}")
            res = await response.json()
            return res["choices"][0]["message"]["content"]

    elif PROVIDER.lower() == "groq":
        def _call_groq():
            client = Groq(api_key=GROQ_API_KEY)
            completion = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.2,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
            )
            return completion.choices[0].message.content

        return await asyncio.to_thread(_call_groq)

    elif PROVIDER.lower() == "maia":
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
            "temperature": 0.2
        }
        async with session.post(MAIA_URL, headers=headers, json=data) as response:
            if response.status != 200:
                raise Exception(f"MAIA API error: {await response.text()}")
            res = await response.json()
            return res["choices"][0]["message"]["content"]

    else:
        raise ValueError(f"Unsupported provider: {PROVIDER}")


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


async def process_chunks(chunks):
    """Process chunks asynchronously and combine results"""
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [
            extract_info_from_text(chunk, session=session) for chunk in chunks
        ]
        raw_outputs = await asyncio.gather(*tasks, return_exceptions=True)

    for out in raw_outputs:
        if isinstance(out, Exception):
            logging.error(f"Chunk failed: {out}")
            continue
        matches = re.findall(r'{[\s\S]*?}', out)
        results.extend(matches)

    return results


async def process_single_file(input_path, output_path, max_words=5000, overlap_words=50):
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.is_file():
        logging.error(f"Input file not found: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        logging.warning("Input file is empty.")
        return

    logging.info(f"Processing file: {input_path.name}")
    chunks = smart_chunk_text(text, max_words=max_words, overlap_words=overlap_words)

    all_matches = await process_chunks(chunks)

    if not all_matches:
        logging.warning(f"No entities extracted from: {input_path.name}")
        return

    json_array_str = "[" + ",\n".join(all_matches) + "]"
    try:
        json_data = json.loads(json_array_str)
    except json.JSONDecodeError as e:
        logging.error(f"JSON parsing error: {e}\nRaw:\n{json_array_str}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(json_data, out, ensure_ascii=False, indent=2)

    logging.info(f"Output saved to: {output_path}")


if __name__ == "__main__":

    input_file = "./data/processed/DE_newspapers_subset/Reichsanzeiger_06_09_1927.txt"  # Path to the input .txt file
    output_file = "./data/processed/DE_newspapers_subset/Reichsanzeiger_06_09_1927.json"   # Path to save the output JSON file
    provider = "maia"  # Choose the LLM provider ('ollama', 'openrouter', 'groq', or 'maia')
    max_words = 4000  # Max words per chunk
    overlap_words = 50  # Number of overlapping words between chunks
    
    # directly pass these values without using argparse
    PROVIDER = provider
    asyncio.run(process_single_file(input_file, output_file, max_words, overlap_words))