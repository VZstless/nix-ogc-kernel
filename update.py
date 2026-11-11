#!/usr/bin/env python3
"""
Usage:
    ./update.py                  # refresh flake.lock + kernel/versions.json
    ./update.py --check          # exit 1 if anything is stale, write nothing
    ./update.py --no-flake-lock  # only refresh the kernel pins
    ./update.py --refresh-hashes # re-download even if the ref is unchanged

Set GITHUB_TOKEN in CI: anonymous API access is limited to 60 req/hour.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

import requests

OWNER = "OpenGamingCollective"
REPO = "linux"

# Python key -> source selection
VARIANTS = {
    "linux-ogc": {"kind": "release"},
    "linux-ogc-lts": {"kind": "branch", "branch": "ogc-lts"},
}


def find_root() -> Path:
    """Locate the checkout this script should operate on.

    When run through `nix run .#update` the script itself lives read-only in the
    Nix store, so fall back to the caller's working directory (walking up until a
    `flake.nix` is found).  `OGC_KERNEL_ROOT` overrides everything.
    """
    env = os.environ.get("OGC_KERNEL_ROOT")
    if env:
        return Path(env).expanduser().resolve()

    here = Path(__file__).resolve().parent
    candidates = [here, Path.cwd()]
    for start in candidates:
        for candidate in (start, *start.parents):
            if (candidate / "flake.nix").is_file():
                return candidate
    return here


ROOT = find_root()
PINS = ROOT / "kernel" / "versions.json"
LOCK = ROOT / "flake.lock"
STORE = "/nix/store"

API = "https://api.github.com"
NIX_TIMEOUT = 1800


def github_headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


@lru_cache(maxsize=None)
def github(path: str) -> dict | list:
    r = requests.get(f"{API}{path}", headers=github_headers(), timeout=60)
    r.raise_for_status()
    return r.json()


def latest_release_tag() -> str:
    return github(f"/repos/{OWNER}/{REPO}/releases/latest")["tag_name"]


def branch_head(branch: str) -> str:
    return github(f"/repos/{OWNER}/{REPO}/commits/{branch}")["sha"]


def tag_series(tag: str) -> str | None:
    """Map a release tag to the matching `modDirVersion`.

    v7.3.3-ogc1       -> 7.3.3
    v7.2-rc7-ogc7     -> 7.2.0-rc7
    v6.18.60-lts-ogc1 -> 6.18.60
    """
    m = re.match(r"^v?(\d+)\.(\d+)(?:\.(\d+))?(?:(-rc\d+))?", tag)
    if not m:
        return None
    major, minor, patch, rc = m.groups()
    if rc:
        return f"{major}.{minor}.0{rc}"
    return f"{major}.{minor}.{patch or 0}"


@lru_cache(maxsize=None)
def mod_dir_version(ref: str) -> str:
    """Kernel `modDirVersion` for a tag / branch / commit, read from Makefile."""
    url = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{ref}/Makefile"
    r = requests.get(url, timeout=60)
    r.raise_for_status()

    fields = {}
    for line in r.text.splitlines():
        m = re.match(r"^(VERSION|PATCHLEVEL|SUBLEVEL|EXTRAVERSION)\s*=\s*(.*?)\s*$", line)
        if m:
            fields[m.group(1)] = m.group(2)

    try:
        major, minor, sublevel = (
            fields["VERSION"],
            fields["PATCHLEVEL"],
            fields["SUBLEVEL"],
        )
    except KeyError as exc:
        raise RuntimeError(f"Cannot find version information from {url}") from exc

    extra = fields.get("EXTRAVERSION", "")
    if extra.startswith("-rc"):
        # rc kernels keep a zero patchlevel in the module directory name
        return f"{major}.{minor}.0{extra}"
    return f"{major}.{minor}.{sublevel}{extra}"


def version_for_branch(mod: str) -> str:
    """Label a branch build like the newest release of the same series.

    The `ogc-lts` branch carries a plain upstream Makefile (EXTRAVERSION is
    empty), so the `-lts-ogcN` suffix only exists in release tags.  Pick the
    newest release that targets the same kernel version, and fall back to the
    bare `modDirVersion` when the branch already moved past the last release.
    """
    for release in github(f"/repos/{OWNER}/{REPO}/releases?per_page=100"):
        tag = release["tag_name"]
        if tag_series(tag) == mod:
            return tag.removeprefix("v")
    return mod


def archive_url(ref: str) -> str:
    # Mirrors the URL that fetchFromGitHub derives, so the hashes match.
    return f"https://github.com/{OWNER}/{REPO}/archive/{ref}.tar.gz"


@lru_cache(maxsize=None)
def prefetch_sri(url: str) -> str:
    """NAR hash (SRI) of the unpacked tree behind `url`."""
    r = subprocess.run(
        ["nix", "store", "prefetch-file", "--unpack", "--json", "--", url],
        capture_output=True,
        text=True,
        timeout=NIX_TIMEOUT,
    )
    if r.returncode != 0:
        raise RuntimeError(f"prefetch failed {url}: {r.stderr.strip()}")
    return json.loads(r.stdout)["hash"]


def load_previous() -> dict:
    if not PINS.exists():
        return {}
    try:
        return json.loads(PINS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def resolve(name: str, cfg: dict, previous: dict, refresh: bool) -> dict:
    if cfg["kind"] == "release":
        ref_kind, ref = "tag", latest_release_tag()
        version = ref.removeprefix("v")
    else:
        ref_kind, ref = "rev", branch_head(cfg["branch"])
        version = None

    mod = mod_dir_version(ref)
    if version is None:
        version = version_for_branch(mod)

    old = previous.get(name, {})
    if not refresh and old.get(ref_kind) == ref and old.get("hash"):
        print(f"{name}: {version} (unchanged, using existing hash)")
        h = old["hash"]
    else:
        h = prefetch_sri(archive_url(f"refs/tags/{ref}" if ref_kind == "tag" else ref))
        print(f"{name}: {version} {h}")

    return {"version": version, "modDirVersion": mod, ref_kind: ref, "hash": h}


def refresh_flake_lock(check: bool) -> bool:
    """Update flake.lock; in check mode report whether it is already current."""
    if check:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "flake.lock"
            subprocess.run(
                ["nix", "flake", "update", "--output-lock-file", str(out)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            current = json.loads(out.read_text(encoding="utf-8"))
        return current == json.loads(LOCK.read_text(encoding="utf-8"))

    subprocess.run(["nix", "flake", "update"], cwd=ROOT, check=True)
    print("flake.lock refreshed")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="check without refresh")
    ap.add_argument("--no-flake-lock", action="store_true", help="skip nix flake update")
    ap.add_argument(
        "--refresh-hashes",
        action="store_true",
        help="refresh hash even if ref is not changed",
    )
    args = ap.parse_args()

    if not shutil.which("nix"):
        print("`nix` command not found", file=sys.stderr)
        return 2

    root_posix = ROOT.as_posix()
    if root_posix == STORE or root_posix.startswith(f"{STORE}/"):
        print(
            f"refusing to work on read-only store path {ROOT}\n"
            "run this from a writable checkout (e.g. `nix run .#update` inside the repo)\n"
            "or point OGC_KERNEL_ROOT at it",
            file=sys.stderr,
        )
        return 2

    previous = load_previous()
    pins = {
        name: resolve(name, cfg, previous, args.refresh_hashes)
        for name, cfg in VARIANTS.items()
    }

    stale = pins != previous
    if not args.no_flake_lock:
        lock_ok = refresh_flake_lock(check=args.check)
        stale = stale or not lock_ok
        if args.check:
            print(f"flake.lock: {'up to date' if lock_ok else 'out of date'}")

    if args.check:
        if stale:
            print("new release detected")
            return 1
        print("all releases are tracked with upstream")
        return 0

    if pins != previous:
        PINS.write_text(
            json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"write into {PINS.relative_to(ROOT)}...")
    else:
        print("kernel pins unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
