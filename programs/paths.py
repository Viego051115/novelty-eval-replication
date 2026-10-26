"""Resolve workspace locations independently of the command's working directory."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = PROJECT_ROOT.parent / 'novelty-eval-replication'
