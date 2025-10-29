# run_pipeline.py
import os
import asyncio
import logging
import time
import csv
import argparse
from pathlib import Path
from tabulate import tabulate
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()

UNIHPC_URL = os.getenv("UNIHPC_URL")
print(f"Using UNIHPC_URL: {UNIHPC_URL}")

from extract_info_newspapers_DE import process_single_file

# === Argument Parser ===
def parse_args():
    parser = argparse.ArgumentParser(
        description="Run async legal info extraction pipeline on newspaper text files."
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Path to input folder containing .txt files (recursively processed)."
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        required=True,
        help="Path to output folder for processed JSON files."
    )
    parser.add_argument(
        "--log", "-l",
        type=str,
        default="./logs/",
        help="Folder where run summaries and logs will be saved."
    )
    parser.add_argument(
        "--provider", "-p",
        type=str,
        default="unihpc",
        choices=["unihpc", "ollama", "openrouter", "groq", "maia"],
        help="Which LLM provider to use."
    )
    parser.add_argument(
        "--max_words", "-mw",
        type=int,
        default=500,
        help="Maximum number of words per chunk."
    )
    parser.add_argument(
        "--overlap", "-ov",
        type=int,
        default=50,
        help="Word overlap between chunks."
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=2.0,
        help="Delay between processing files (seconds)."
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        default="parallel",
        choices=["parallel", "sequential"],
        help="Whether to process chunks in parallel or sequentially."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (only save valid JSON if all chunks succeed)."
    )

    return parser.parse_args()


# === Main Execution ===
if __name__ == "__main__":
    args = parse_args()

    input_folder = Path(args.input)
    output_folder = Path(args.output)
    log_folder = Path(args.log)
    provider = args.provider
    max_words = args.max_words
    overlap_words = args.overlap
    delay_seconds = args.delay
    strict_mode = args.strict
    mode = args.mode

    # === Logging setup ===
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # === Prepare folders ===
    output_folder.mkdir(parents=True, exist_ok=True)
    log_folder.mkdir(parents=True, exist_ok=True)

    # === Find all input text files ===
    txt_files = sorted(input_folder.rglob("*.txt"))
    if not txt_files:
        logging.error(f"No .txt files found in {input_folder} or its subfolders")
        exit(1)

    logging.info(f"📂 Found {len(txt_files)} text files across all subfolders")

    summary = []
    run_start = time.time()

    for idx, txt_file in enumerate(txt_files):
        relative_path = txt_file.relative_to(input_folder)
        out_file = output_folder / relative_path.parent / (txt_file.stem + ".json")
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if out_file.exists():
            logging.info(f"⏭️  Skipping {relative_path}, JSON already exists")
            continue

        logging.info(f"[{idx+1}/{len(txt_files)}] Processing: {relative_path}")

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
            logging.error(f"❌ Unexpected error processing {relative_path}: {e}")
            summary.append({
                "file": str(relative_path),
                "mode": mode,
                "chunks": "-",
                "time_sec": 0,
                "status": f"💥 exception: {e}",
            })

        if idx < len(txt_files) - 1:
            logging.info(f"⏳ Waiting {delay_seconds} seconds before next file...")
            time.sleep(delay_seconds)

    # === Summary output ===
    total_runtime = time.time() - run_start
    summary_table = [
        [s["file"], s["mode"], s["chunks"], s["time_sec"], s["status"]] for s in summary
    ]
    headers = ["File", "Mode", "Chunks", "Time (s)", "Outcome"]

    table_str = tabulate(summary_table, headers=headers, tablefmt="grid")
    print("\n\n=== 📊 Extraction Summary ===")
    print(table_str)
    logging.info(table_str)
    logging.info(f"Total runtime: {total_runtime:.2f} seconds")

    # === Save CSV summary ===
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    csv_path = log_folder / f"run_log_summary_{timestamp}.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(headers)
        writer.writerows(summary_table)
        writer.writerow([])
        writer.writerow(["Total runtime (s):", round(total_runtime, 2)])

    logging.info(f"📁 Run summary saved to: {csv_path}")
    logging.info("✅ Run complete.")
