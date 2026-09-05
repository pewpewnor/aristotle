import asyncio
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from datasets import concatenate_datasets, load_dataset
from evaluate_csv import evaluate_progress_file
from langchain_ollama import ChatOllama

from aristotle import project_config

MAX_SAMPLES = None
DIFFICULTY = "hard"
WANTED_CODEBASES = [
    "https://github.com/getzep/graphiti.git",
    "https://github.com/keras-team/keras.git",
    "https://github.com/microsoft/qlib.git",
    # "https://github.com/huggingface/diffusers.git",
]
WITH_FACTS = False
CONTINUE_FROM = 0
MAX_SAMPLES = 12

llm = ChatOllama(
    model=project_config.ollama_llm_main_model,
    base_url=project_config.ollama_base_url,
    temperature=project_config.llm_temperature,
)
fail = 0


async def ask_ollama(
    question: str, facts: List[str], codebase_name: str
) -> Tuple[str, float]:
    print(f"[STEP] Querying Ollama with question")

    if WITH_FACTS:
        context_text = "\n".join(facts)
        prompt = f"Context: {context_text}\n\nQuestion: {question} in {codebase_name}"
    else:
        prompt = f"Question: {question} in {codebase_name}"

    start = time.time()
    try:
        response = llm.invoke(prompt).content
        end = time.time()
        response_time = end - start

        print(f"[SUCCESS] Received answer from Ollama:", response)
        return response, response_time  # type: ignore
    except Exception as e:
        end = time.time()
        response_time = end - start
        print(f"[ERROR] Ollama error: {e}")
        raise Exception(str(e))


async def process_samples(df: pd.DataFrame) -> List[Dict[str, Any]]:
    print(f"[STEP] Processing {len(df)} samples")
    results = []

    i = 0
    for idx, row in df.iterrows():
        if i == MAX_SAMPLES:
            break
        if i < CONTINUE_FROM:
            i += 1
            continue

        print(f"\n[STEP] Processing sample {idx} [{i}/{len(df)}]")

        codebase_name = row["repo"].rstrip("/").split("/")[-1]  # type: ignore
        if codebase_name.endswith(".git"):
            codebase_name = codebase_name[:-4]

        try:
            agent_answer, time_taken = await ask_ollama(
                row["question"], row["facts"], codebase_name  # type: ignore
            )
            print("[EXPECTED] Expected answer:", row["answer"])

            result = {
                "user_input": row["question"],
                "response": agent_answer,
                "reference": row["answer"],
                "retrieved_contexts": [],
            }
            result["metadata"] = row["metadata"]
            result["time_taken"] = time_taken

            results.append(result)

            progress_row = {**result, "idx": idx, "metadata": str(row["metadata"])}
            progress_df = pd.DataFrame([progress_row])

            progress_df.to_csv(
                project_config.evaluation_progress_file,
                mode="a",
                header=not Path(project_config.evaluation_progress_file).exists(),
                index=False,
            )
            print(f"[SUCCESS] Sample {idx} processed and saved to progress file")
        except Exception as e:
            global fail
            fail += 1
            print(f"[ERROR] Failed to process sample {idx}: {e}")

        i += 1

    print(f"\n[SUCCESS] Processed {len(results)} samples successfully")
    print(f"[INFO] Failed samples: {fail}")
    return results


def prepare_dataframe(dataset_split) -> pd.DataFrame:
    print("[STEP] Preparing dataframe from dataset")

    df = pd.DataFrame(dataset_split.to_pandas())

    df["repo"] = df["metadata"].map(lambda m: m["repo"])
    df["commit"] = df["metadata"].map(lambda m: m["commit"])
    df["difficulty"] = df["metadata"].map(lambda m: m["difficulty"])

    print(f"[STEP] Filtering to only wanted repositories")
    df = df[df["repo"].isin(WANTED_CODEBASES)]
    df = df[df["difficulty"] == DIFFICULTY]

    print(f"[SUCCESS] Dataframe prepared with {len(df)} samples")
    return df  # type: ignore


def save_and_display_results(results_df: pd.DataFrame):
    print(f"[STEP] Saving results")
    results_df.to_csv(project_config.evaluation_metric_file, index=False)

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Samples evaluated: {len(results_df)}")
    print("\nMetric Scores:")
    print("-" * 60)

    excluded_cols = [
        "sample_id",
        "user_input",
        "response",
        "reference",
        "retrieved_contexts",
        "metadata",
    ]

    for col in results_df.columns:
        if col not in excluded_cols:
            mean_score = results_df[col].mean()
            print(f"{col:<30} {mean_score:.4f}")

    print("=" * 60)


async def main():
    print("[START] Beginning evaluation process with Ollama")

    print("[STEP] Loading dataset: Qodo/deep_code_bench")
    dataset_both = load_dataset("Qodo/deep_code_bench")

    df = prepare_dataframe(
        concatenate_datasets([dataset_both["train"], dataset_both["test"]])  # type: ignore
    )

    results = await process_samples(df)

    if not results:
        print("[ERROR] No samples were processed successfully")
        return None

    # print(f"\n[STEP] Evaluating...")

    # evaluate_progress_file(results)


if __name__ == "__main__":
    results = asyncio.run(main())
