import os
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple

import pygit2

from .. import project_config


def get_codebase_path(codebase_name: str) -> str:
    Path(project_config.git_clone_dir).mkdir(parents=True, exist_ok=True)
    return os.path.join(project_config.git_clone_dir, codebase_name)


def clean_git_url(git_url: str) -> str:
    url = git_url.strip()
    if url.endswith("/"):
        url = url[:-1]
    if re.search(r"(github|gitlab|bitbucket)\.com", url, re.I) and not url.endswith(
        ".git"
    ):
        url += ".git"
    return url


def build_reference_prefix(repo: pygit2.Repository, git_url: str) -> str:
    base_url = git_url[:-4] if git_url.endswith(".git") else git_url
    head_ref = repo.head
    if head_ref is not None and head_ref.name.startswith("refs/heads/"):
        branch = head_ref.shorthand
    else:
        branch = "main"
    return f"{base_url}/blob/{branch}/"


def clone_git_repository(
    git_url: str,
    codebase_name: Optional[str] = None,
    remove_old_clone: bool = True,
    commit_id: Optional[str] = None,
) -> Tuple[str, str]:
    git_url = clean_git_url(git_url)

    if codebase_name is None:
        repo_name = git_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        codebase_name = repo_name

    codebase_path = get_codebase_path(codebase_name)
    print(f"[INFO] Cloning '{git_url}' to '{codebase_path}'")

    if os.path.exists(codebase_path):
        if remove_old_clone:
            shutil.rmtree(codebase_path)
        else:
            raise FileExistsError(f"Codebase path '{codebase_path}' already exists.")

    clone_depth = 1 if commit_id is None else 0

    repo = pygit2.clone_repository(
        git_url, codebase_path, callbacks=pygit2.RemoteCallbacks(), depth=clone_depth
    )

    if commit_id:
        try:
            commit = repo.revparse_single(commit_id)
        except KeyError:
            raise ValueError(f"Commit '{commit_id}' not found in repository.")

        repo.checkout_tree(commit)
        repo.set_head(commit.id)
        print(f"[INFO] Checked out commit {commit_id}")

    reference_prefix = build_reference_prefix(repo, git_url)
    return os.path.abspath(codebase_path), reference_prefix
