#!/usr/bin/env python3
# Copyright 2026 Jeremy Melanson
# SPDX-License-Identifier: Apache-2.0

"""Assert that the internal documentation stays out of the published repository.

This repository is public.  The internal collection -- ``CLAUDE.md`` and
``.claude/`` -- is not: it is written for people working *on* json-dump and is
kept on the developer's machine.  Both paths are listed in ``.gitignore``, which
is necessary and nowhere near sufficient:

- ``.gitignore`` has no effect on a path that is *already tracked*.  A file
  committed once stays committed, and every later commit carries it.
- ``git add -f`` overrides it silently, and so does any tool that stages by
  absolute path rather than by pathspec.

Neither failure is visible in a diff.  The commit is the moment that matters:
once a path is in a commit it is in the history, and deleting it later does not
take it out -- the fix becomes a rewrite rather than a commit.  So this runs at
commit time, where the permanent copy gets made, and again at push, which is the
last point before the exposure stops being local and starts being irreversible.
At about 40ms it is cheap enough for both.

The second half of the check is the rule that makes the split worth having:
nothing published may *point at* the internal collection.  Someone reading the
manpage from a distro package, or the README rendered on PyPI, cannot follow a
"see CLAUDE.md" reference -- it resolves to nothing and advertises that the real
explanation is somewhere they cannot reach.  Where a shipped file needs a fact
the internal docs also record, it has to state the fact.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The internal collection, as pathspecs relative to the repository root. A
# directory entry covers everything beneath it.
INTERNAL_PATHS = ("CLAUDE.md", ".claude")

# The strings that constitute a reference to it. Kept separate from the paths
# above because a reference is a matter of prose -- "see CLAUDE.md" -- while a
# path is a matter of the index.
INTERNAL_NAMES = ("CLAUDE.md", ".claude/")

# Files whose job is to name the internal paths, and which would otherwise
# report themselves. Both are machinery rather than documentation: .gitignore
# has to spell out what it excludes, and this script has to spell out what it
# looks for.
ALLOWED_TO_NAME_THEM = frozenset({".gitignore", "scripts/check_docs.py"})


def tracked_files() -> list[str] | None:
    """Every path in the index, or None when there is no index to read.

    Returning None rather than raising keeps `make check` usable from an
    unpacked sdist, which has no git metadata and therefore nothing this check
    could be wrong about.  Resolving git to an absolute path up front makes
    "git is not installed" the same quiet no-op as "this is not a checkout".
    """
    git = shutil.which("git")
    if git is None:
        return None
    try:
        out = subprocess.run(
            [git, "-C", str(ROOT), "ls-files", "-z"],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [p for p in out.stdout.decode().split("\0") if p]


def tracked_internal(tracked: list[str]) -> list[str]:
    offenders = []
    for path in tracked:
        for internal in INTERNAL_PATHS:
            if path == internal or path.startswith(internal + "/"):
                offenders.append(path)
                break
    return sorted(offenders)


def references(tracked: list[str]) -> list[tuple[str, int, str]]:
    hits = []
    for path in sorted(tracked):
        if path in ALLOWED_TO_NAME_THEM:
            continue
        try:
            text = (ROOT / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            # Absent (a stale index entry) or binary. Neither can contain prose
            # that points a reader anywhere.
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if any(name in line for name in INTERNAL_NAMES):
                hits.append((path, lineno, line.strip()))
    return hits


def main() -> int:
    tracked = tracked_files()
    if tracked is None:
        print("ok: not a git checkout, nothing to check")
        return 0

    staged = tracked_internal(tracked)
    if staged:
        print("error: internal documentation is tracked by git:")
        for path in staged:
            print(f"    {path}")
        print()
        print("This repository is published. Untrack it before it is pushed:")
        print(f"    git rm --cached {' '.join(staged)}")
        print()
        print("If it has already been committed, .gitignore will not help --")
        print("the history keeps a copy. Rewrite the affected commits instead.")
        return 1

    pointers = references(tracked)
    if pointers:
        print("error: published files reference the internal documentation:")
        for path, lineno, line in pointers:
            print(f"    {path}:{lineno}: {line}")
        print()
        print("A reader with a package installed and no checkout cannot follow")
        print("these. State the fact instead of citing where it is written.")
        return 1

    print(f"ok: {len(tracked)} tracked files, no internal docs and no references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
