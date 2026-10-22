"""Check declared bootstrap dependencies against the pinned typos entrypoint."""

import re
import shlex
from pathlib import Path
from urllib.request import urlopen


def test_qa_bootstrap_declares_typos_downloader():
    workflow = (Path(__file__).parents[1] / ".github/workflows/ci.yml").read_text()
    qa_job = workflow.split("  qa_actions:\n", 1)[1].split("\n  lint:", 1)[0]
    action = re.search(r"uses: (crate-ci/typos@[^\s]+)", qa_job).group(1)
    repository, version = action.split("@")
    url = f"https://raw.githubusercontent.com/{repository}/{version}/action/entrypoint.sh"
    with urlopen(url, timeout=20) as response:
        entrypoint = response.read().decode()
    downloader = re.search(r"^\s*(wget)\s+--progress=", entrypoint, re.MULTILINE).group(1)
    bootstrap = re.search(r"run: (apt-get update && apt-get install[^\n]+)", qa_job).group(1)
    packages = shlex.split(bootstrap.split("apt-get install", 1)[1])
    assert downloader in packages, f"{action} requires {downloader}; bootstrap: {bootstrap}"
