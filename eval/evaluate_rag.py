import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from datasets import concatenate_datasets, load_dataset
from evaluate_csv import evaluate_progress_file

from aristotle import project_config
from aristotle.agent import AristotleAgent, docs_db, graph_db
from aristotle.agent.loaded_codebases import (get_loaded_codebase_status,
                                              update_loaded_codebase_status)
from aristotle.graph.parser import CodebaseParser
from aristotle.graph.parser.parser_settings import ParserSettings
from aristotle.repository_loader import clone_git_repository

MAX_SAMPLES = None
DIFFICULTY = None
WANTED_CODEBASES = [
    "https://github.com/getzep/graphiti.git",
    "https://github.com/keras-team/keras.git",
    "https://github.com/microsoft/qlib.git",
    # "https://github.com/huggingface/diffusers.git",
]
WITH_FACTS = False
LOAD_REPO = False
CONTINUE_FROM = 68


agent = AristotleAgent()
fail = 0


async def load_repository(git_url: str, commit_id: str, codebase_name: str):
    print(f"[STEP] Loading repository: {git_url} at commit {commit_id}")

    codebase_path = Path(f"./.cloned/{codebase_name}")

    if get_loaded_codebase_status(codebase_name) == "NOT_LOADED":
        try:
            print(f"[STEP] Cloning repository to '{codebase_path}'...")
            codebase_path, reference_prefix = clone_git_repository(
                git_url,
                codebase_name=codebase_name,
                remove_old_clone=False,
                commit_id=commit_id,
            )

            update_loaded_codebase_status(codebase_name, "LOADING_IN_PROGRESS")

            print(f"[STEP] Loading documents into vector database...")
            docs_db.load_dir(
                codebase_path,
                codebase_name,
                reference_prefix=reference_prefix,
                print_progress=False,
            )

            print(f"[STEP] Parsing codebase '{codebase_name}'...")
            parser = CodebaseParser(codebase_name, ParserSettings())
            parser.parse_dir(
                codebase_path, reference_prefix=reference_prefix, print_progress=False
            )

            print(
                f"[STEP] Inserting {len(parser.get_nodes())} nodes and {len(parser.get_relationships())} into graph database..."
            )
            await graph_db.insert_parser_results(parser)

            update_loaded_codebase_status(codebase_name, "LOADED")
            print(f"[SUCCESS] Repository loaded successfully: {codebase_name}")
        except Exception as e:
            print(f"[WARN] Failed to load codebase {git_url}: {e}")
    else:
        print(f"[STEP] {codebase_name} has already been loaded")


async def ask_aristotle_agent(
    question: str, facts: List[str], codebase_name: str
) -> Tuple[str, float]:
    print(f"[STEP] Querying Aristotle agent with question")
    if WITH_FACTS:
        context_text = "\n".join(facts)
        prompt = f"Context: {context_text}\n\nQuestion: {question} in {codebase_name}"
    else:
        prompt = f"Question: {question} in {codebase_name}"

    start = time.time()
    structured_response, error = await agent.chat(prompt)
    end = time.time()
    agent_response_time = end - start

    if error:
        print(f"[ERROR] Agent error: {error}")
        raise Exception(error)

    if structured_response:
        print(f"[SUCCESS] Received answer from agent:", structured_response.response)
        return structured_response.response, agent_response_time

    print(f"[WARN] No response from agent")
    raise Exception("No response generated")


async def process_samples(df: pd.DataFrame) -> List[Dict[str, Any]]:
    print(f"[STEP] Processing {len(df)} samples")
    results = []

    i = 0
    for idx, row in df.iterrows():
        if i < CONTINUE_FROM:
            i += 1
            continue

        print(f"\n[STEP] Processing sample {idx} [{i}/{len(df)}]")  # type: ignore

        codebase_name = row["repo"].rstrip("/").split("/")[-1]  # type: ignore
        if codebase_name.endswith(".git"):
            codebase_name = codebase_name[:-4]

        if LOAD_REPO:
            await load_repository(row["repo"], row["commit"], codebase_name)  # type: ignore

        try:
            agent_answer, time_taken = await ask_aristotle_agent(row["question"], row["facts"], codebase_name)  # type: ignore
            print("[EXPECTED] Expected answer:", row["answer"])

            with open(project_config.evaluation_temp_file) as f:
                retrieved_information = [
                    item.get("information") for item in json.load(f)
                ]

            result = {
                "user_input": row["question"],
                "response": agent_answer,
                "reference": row["answer"],
                "retrieved_contexts": retrieved_information,
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
            print(f"[SUCCESS] Sample {idx} processed and saved to progress file")  # type: ignore
        except:
            global fail
            fail += 1

        i += 1
    print(f"\n[SUCCESS] Processed {len(results)} samples successfully")
    return results


def prepare_dataframe(dataset_split) -> pd.DataFrame:
    print("[STEP] Preparing dataframe from dataset")

    df = pd.DataFrame(dataset_split.to_pandas())

    df["repo"] = df["metadata"].map(lambda m: m["repo"])
    df["commit"] = df["metadata"].map(lambda m: m["commit"])

    print(f"[STEP] Filtering to only wanted repositories")
    df = df[df["repo"].isin(WANTED_CODEBASES)]  # type: ignore

    print(f"[STEP] Limiting to {MAX_SAMPLES} samples per repository")
    if MAX_SAMPLES:
        df = df.head(MAX_SAMPLES)

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
    print("[START] Beginning evaluation process")

    print("[STEP] Loading dataset: Qodo/deep_code_bench")
    dataset_both = load_dataset("Qodo/deep_code_bench")

    df = prepare_dataframe(
        concatenate_datasets([dataset_both["train"], dataset_both["test"]])  # type: ignore
    )

    results = await process_samples(df)

    if not results:
        print("[ERROR] No samples were processed successfully")
        return None

    print(f"\n[STEP] Evaluating...")

    evaluate_progress_file(results)


if __name__ == "__main__":
    results = asyncio.run(main())
