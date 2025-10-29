# Historical German Newspaper Text Extraction

## Overview

This project extracts structured legal and business information from historical German newspaper articles (1920-1945) using Large Language Models (LLMs). The system processes OCR-scanned newspaper text and extracts entities such as court names, dates, company names, and registration codes into structured JSON format.

## Methodology

### Scoring System

The extraction quality is evaluated using a **weighted similarity score** that measures how well the extracted data matches ground truth annotations:

```
weighted_similarity_score = Σ (field_match_score × field_weight)
```

Each field is scored based on match type:
- **Regex match** (e.g., court names, company names): 2 points
- **Binary match** (e.g., registration codes, years): 2 points
- **Partial match**: 1 point

**Overall Similarity Score** is calculated as:
```
max_score = number_of_ground_truth_instances × ideal_weighted_similarity_score
obtained_score = number_of_parsed_instances × parsed_weighted_similarity_score
overall_similarity_score = obtained_score / max_score
```

This metric balances precision (correctly extracted fields) and recall (coverage of all instances).

---

## Model Performance Results

### OpenRouter Models

Performance on historical German newspaper extraction task:

| Rank | Model | Score | Comments |
|------|-------|-------|----------|
| 🥇 | **LLAMA-3.3-8b-instruct** | **0.77** | Best overall performance - instruction-tuned, multilingual, captured most instances |
| 🥈 | LLAMA-3.2-3b-instruct | 0.40 | Instruction-tuned, multilingual |
| 🥉 | (tencent)hunyuan-a13b-instruct | 0.34 | Reasonable performance |
| 4 | Gemma-3-12b | 0.20 | Captured fewer instances |
| 5 | Gemma-3-4b | 0.11 | Captured fewer instances |
| 6 | gpt-oss-20b | 0.09 | Strong English bias, poor German performance |

**Winner:** `LLAMA-3.3-8b-instruct` demonstrated superior performance for multilingual German text extraction tasks.

---

### MAIA UB Models

Performance on University of Mannheim's MAIA infrastructure:

| Rank | Model | Score | Key Issues |
|------|-------|-------|------------|
| 🥇 | **mistral-small3.1:latest** | **0.72** | Best performer, reliable JSON output |
| 🥈 | llama3.2-vision:90b | 0.67 | Registration code mismatches, hallucinations with larger context windows |
| 🥉 | Phi4:latest | 0.57 | Inconsistent JSON formatting |
| 4 | gemma2:latest | 0.56 | Poor registration number extraction |
| 5 | Llama3.1:latest | 0.46 | Missed instances, incorrect reg-no entries |
| 6 | groq.llama-3.3-70b-versatile | 0.29 | Hallucinations, parsing failures |
| 7 | deepseek-r1:14b | 0.12 | JSON parsing failures due to incorrect output |
| 8 | hf.co/cristianadam/Teuken-7B-instruct | 0.002 | Failed to return structured JSON |
| 9 | llama4:latest | - | No structured output |

**Winner:** `mistral-small3.1:latest` provided the best balance of accuracy and reliability.

---

### MAIA Uni-HPC Models

Performance on University's high-performance computing cluster (default chunk size: 500 words):

| Rank | Model | Score (Seq/Para) | Inference Time | Key Issues |
|------|-------|------------------|----------------|------------|
| 🥇 | **qwen2.5vl:72b** | **0.76 (para)** | ~470s | Best performer, only 2 reg-no mismatches |
| 🥈 | mistral-small3.2:latest | 0.69 (seq) | 162s | Fast, only 12 reg-no mismatches |
| 🥉 | llama3.2-vision:90b | 0.68 (para) | ~365s | 39 reg-code format errors (e.g., "HRA 2572" → "H-R. A 2572") |
| 4 | llama3.1:70b | 0.62 (seq) | 407s | 32 reg-no mismatches in parallel mode |
| 5 | gemma3:27b | 0.56 (para) | ~598s | 35 reg-no mismatches |
| 6 | gpt-oss:120b | 0.54 (para) | 240s | 30-32 reg-no mismatches |
| 7 | llama4:16x17b | 0.30 (para) | ~121s | 45 reg-code mismatches, parsing timeouts |
| 8 | granite4:small-h | 0.36 (seq) | 175s | Missed 49 reg-nos (seq), 46 (para) |
| 9 | qwen3:235b | - | - | "Thinking" mode output with `<think>` tags, failed parsing |
| 10 | deepseek-v3.1:671b | - | - | Timeout errors (model too large) |
| 11 | mistral-large:123b | - | - | Timeout errors |
| 12 | cogito:70b | - | ~377s | Incorrect JSON output format |

**Winner:** `qwen2.5vl:72b` achieved the highest accuracy with excellent performance in both sequential and parallel processing modes.

---

## Key Findings

### Best Models by Use Case

1. **For OpenRouter (cloud API):**
   - Use `LLAMA-3.3-8b-instruct` (score: 0.77)
   - Cost-effective with strong multilingual German support

2. **For MAIA UB (local inference):**
   - Use `mistral-small3.1:latest` (score: 0.72)
   - Reliable JSON output, good performance

3. **For Uni-HPC (high-performance computing):**
   - Use `qwen2.5vl:72b` (score: 0.76)
   - Highest accuracy, excellent reg-code extraction
   - Alternative: `mistral-small3.2:latest` (score: 0.69) for faster inference

### Common Issues Across Models

- **Registration code formatting:** Many models struggle with exact format (e.g., "HRA 123" vs "H-R. A 123")
- **Hallucinations:** Larger context windows (>500 words) increase false extractions
- **JSON compliance:** Smaller models often output invalid JSON or include explanatory text
- **Timeout errors:** Very large models (>600B parameters) exceed infrastructure limits
- **English bias:** Models like GPT-OSS perform poorly on German historical text

### Recommendations

- **Optimal chunk size:** 500 words (larger chunks increase hallucinations)
- **Processing mode:** Parallel processing recommended for speed, but monitor for consistency
- **Model selection:** Balance between accuracy, speed, and infrastructure constraints
- **Prompt engineering:** Critical for German historical text with legal terminology

---

## Performance Notes

- **Parallel processing:** 1.5-2x faster but may introduce slight inconsistencies
- **Sequential processing:** More reliable for complex extractions
- **Chunk overlap:** Critical for entities spanning chunk boundaries
- **Retry logic:** Up to 3 attempts per failed chunk before skipping

---