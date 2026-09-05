import re
from typing import List, Optional, Tuple

import requests

from .git_integration import clone_git_repository


def normalize_candidate_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    url = re.sub(r"^git\+", "", url, flags=re.I)
    m = re.match(r"^(git@[^:]+):(.+)$", url)
    if m:
        url = f"ssh://{m.group(1)}/{m.group(2)}"
    url = re.sub(r"[#?].*$", "", url)
    return url


def extract_repo_root(url: str) -> Optional[str]:
    if not url:
        return None
    url = normalize_candidate_url(url)
    patterns = [
        r"^(?:https?://|ssh://)(?:[^@/]+@)?(?P<host>(github|gitlab|bitbucket)\.com)(?:[:/]+)(?P<owner>[^/]+)/(?P<repo>[^/]+)",
        r"^(?:git@)?(?P<host>(github|gitlab|bitbucket)\.com)[:/](?P<owner>[^/]+)/(?P<repo>[^/]+)",
    ]
    for pat in patterns:
        m = re.search(pat, url, flags=re.I)
        if not m:
            continue
        host = m.group("host").lower()
        owner = m.group("owner").strip()
        repo = m.group("repo").strip()
        repo = re.sub(r"\.git$", "", repo, flags=re.I)
        repo = repo.split("/")[0]
        if owner and repo:
            return f"https://{host}/{owner}/{repo}"
    return None


def verify_url_exists(url: str, timeout: float = 5.0) -> bool:
    try:
        resp = requests.head(url, allow_redirects=True, timeout=timeout)
        if 200 <= resp.status_code < 400:
            return True
        if resp.status_code in (405, 501):
            resp2 = requests.get(url, allow_redirects=True, timeout=timeout)
            return 200 <= resp2.status_code < 400
    except requests.RequestException:
        return False
    return False


def get_all_project_git_urls(package_name: str) -> List[str]:
    resp = requests.get(f"https://pypi.org/pypi/{package_name}/json", timeout=10)
    if resp.status_code != 200:
        raise ValueError(f"Package '{package_name}' not found on PyPI")
    data = resp.json()
    candidates = []
    homepage = data["info"].get("home_page") or ""
    if homepage:
        candidates.append(homepage)
    project_urls = data["info"].get("project_urls") or {}
    for v in project_urls.values():
        if v:
            candidates.append(v)
    for extra_field in ("package_url", "docs_url", "repository"):
        v = data["info"].get(extra_field)
        if isinstance(v, str) and v:
            candidates.append(v)
    seen = set()
    dedup = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            dedup.append(c)
    results = []
    for cand in dedup:
        root = extract_repo_root(cand)
        if root:
            results.append(root)
            if root.endswith(".git"):
                results.append(root[:-4])
            else:
                results.append(root + ".git")
    return list(dict.fromkeys(results))


def clone_pypi_package(package_name: str) -> Tuple[str, str]:
    package_name = package_name.lower()
    candidates = get_all_project_git_urls(package_name)
    if not candidates:
        raise ValueError(f"No candidate Git URLs found for package '{package_name}'")
    errors = []
    for url in candidates:
        try:
            return clone_git_repository(url, package_name)
        except Exception as e:
            errors.append((url, str(e)))
            continue
    raise RuntimeError(
        f"Failed to clone '{package_name}' from all candidate URLs:\n"
        + "\n".join(f"- {url}: {err}" for url, err in errors)
    )
