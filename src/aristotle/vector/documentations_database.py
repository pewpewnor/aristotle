import json
import os
from typing import Any, Dict, List, Optional

import faiss
import frontmatter
import numpy as np
from langchain_ollama import OllamaEmbeddings

from .. import project_config
from .chunk import split_markdown


class Encoder:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or project_config.ollama_embedding_model
        base_url = project_config.ollama_base_url.rstrip("/api").rstrip("/")
        self.embeddings = OllamaEmbeddings(model=self.model_name, base_url=base_url)

    def encode_string(self, text: str) -> np.ndarray:
        embedding = self.embeddings.embed_query(text)
        return np.array([embedding], dtype=np.float32)

    def encode_list(self, texts: List[str]) -> np.ndarray:
        embeddings = self.embeddings.embed_documents(texts)
        return np.array(embeddings, dtype=np.float32)


def build_index(embeddings, dim, index_path):
    abs_path = os.path.abspath(index_path)
    dir_path = os.path.dirname(abs_path)
    os.makedirs(dir_path, exist_ok=True)

    normalized_embeddings = embeddings / np.linalg.norm(
        embeddings, axis=1, keepdims=True
    )

    index = faiss.IndexFlatIP(dim)
    index.add(normalized_embeddings)  # type: ignore
    faiss.write_index(index, abs_path)


def save_metas(meta, meta_path):
    abs_path = os.path.abspath(meta_path)
    dir_path = os.path.dirname(abs_path)
    os.makedirs(dir_path, exist_ok=True)

    with open(abs_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=True)


def load_index(index_path, meta_path):
    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return index, meta


def search(index, meta, query_embedding, k):
    scores, ids = index.search(query_embedding, k)
    results = []
    for score, idx in zip(scores[0], ids[0]):
        if idx < len(meta):
            m = meta[idx].copy()
            m["score"] = float(score)
            results.append(m)
    return results


def enrich_chunk_with_context(chunk: str, codebase_name: str, reference: str) -> str:
    context_header = f"[Codebase: {codebase_name}] [File: {reference}]\n\n"
    return context_header + chunk


class DocumentationsDatabase:
    def __init__(self):
        self.encoder = Encoder()
        self.index_path = f"{project_config.faiss_data_dir}/faiss_index"
        self.meta_path = f"{project_config.faiss_data_dir}/meta.json"
        self.index = None
        self.meta = None
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            self.refresh_index()

    def search(
        self, query: str, top_k: int = project_config.top_k_vector_search
    ) -> List[Dict[str, Any]]:
        if not os.path.exists(self.index_path) or not os.path.exists(self.meta_path):
            return [{"info": "Vector DB is empty", "metadata": {}}]

        try:
            if self.index is None or self.meta is None:
                self.refresh_index()

            encoded_query = self.encoder.encode_string(query)
            normalized_query = encoded_query / np.linalg.norm(
                encoded_query, axis=1, keepdims=True
            )

            results = search(self.index, self.meta, normalized_query, top_k)
            results.sort(key=lambda x: x.get("score", 0), reverse=True)
        except Exception as e:
            print("[ERROR] while searching docs:", e)
            return []
        return results

    def refresh_index(self):
        self.index, self.meta = load_index(self.index_path, self.meta_path)

    def load_file(
        self,
        file_path: str,
        codebase_name: str,
        reference: Optional[str] = None,
        append: bool = True,
    ) -> int:
        if not file_path.endswith(".md"):
            return 0

        if reference is None:
            reference = os.path.basename(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw = f.read()
            metadata, text = frontmatter.parse(raw)
            metadata = metadata or {}
            parts = split_markdown(text, codebase_name, reference)
            if not parts:
                return 0

            enriched_chunks = [
                enrich_chunk_with_context(chunk, codebase_name, reference)
                for chunk in parts
            ]

            all_metas = [
                {
                    "codebase": codebase_name,
                    "reference": reference,
                    "text": chunk,
                    "enriched_text": enriched_chunk,
                }
                for chunk, enriched_chunk in zip(parts, enriched_chunks)
            ]

            X = self.encoder.encode_list(enriched_chunks)

            if (
                append
                and os.path.exists(self.index_path)
                and os.path.exists(self.meta_path)
            ):
                existing_index, existing_meta = load_index(
                    self.index_path, self.meta_path
                )

                normalized_embeddings = X / np.linalg.norm(X, axis=1, keepdims=True)
                existing_index.add(normalized_embeddings)
                faiss.write_index(existing_index, self.index_path)

                existing_meta.extend(all_metas)
                save_metas(existing_meta, self.meta_path)
            else:
                build_index(X, X.shape[1], self.index_path)
                save_metas(all_metas, self.meta_path)

            self.refresh_index()
            return 1
        except:
            return 0

    def load_dir(
        self,
        codebase_path: str,
        codebase_name: str,
        reference_prefix: str = "",
        print_progress=False,
        append: bool = True,
    ) -> int:
        all_chunks, all_metas = [], []
        file_count = 0
        for root_path, dir_names, file_names in os.walk(codebase_path):
            dir_names[:] = [d for d in dir_names if not d.startswith(".")]
            for file_name in file_names:
                if not file_name.endswith(".md"):
                    continue
                file_path = os.path.join(root_path, file_name)
                reference = (
                    f"{reference_prefix}{root_path[len(codebase_path)+1:]}/{file_name}"
                )
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        raw = f.read()
                    metadata, text = frontmatter.parse(raw)
                    metadata = metadata or {}
                    parts = split_markdown(text, codebase_name, reference)
                    if not parts:
                        continue

                    enriched_chunks = [
                        enrich_chunk_with_context(chunk, codebase_name, reference)
                        for chunk in parts
                    ]

                    all_chunks.extend(enriched_chunks)
                    all_metas.extend(
                        [
                            {
                                "codebase": codebase_name,
                                "reference": reference,
                                "text": chunk,
                                "enriched_text": enriched_chunk,
                            }
                            for chunk, enriched_chunk in zip(parts, enriched_chunks)
                        ]
                    )
                    file_count += 1
                except:
                    pass

        if all_chunks:
            X = self.encoder.encode_list(all_chunks)

            if (
                append
                and os.path.exists(self.index_path)
                and os.path.exists(self.meta_path)
            ):
                existing_index, existing_meta = load_index(
                    self.index_path, self.meta_path
                )

                normalized_embeddings = X / np.linalg.norm(X, axis=1, keepdims=True)
                existing_index.add(normalized_embeddings)
                faiss.write_index(existing_index, self.index_path)

                existing_meta.extend(all_metas)
                save_metas(existing_meta, self.meta_path)
            else:
                build_index(X, X.shape[1], self.index_path)
                save_metas(all_metas, self.meta_path)

            self.refresh_index()
        return file_count
