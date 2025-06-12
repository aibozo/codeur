from pathlib import Path


def normalize_repo_path(path: str | Path, repo_root: str | Path) -> str:
    """Return the path relative to the repository root if possible."""
    abs_path = Path(path).resolve()
    try:
        return str(abs_path.relative_to(Path(repo_root).resolve()))
    except Exception:
        return str(abs_path)
