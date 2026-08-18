#!/usr/bin/env python3
"""Repoint a copied venv's console scripts at their own interpreter.

    python3 pipeline/fix_venv_shebangs.py            # fix pipeline/.venv
    python3 pipeline/fix_venv_shebangs.py --check    # report only, exit 1 if broken
    python3 pipeline/fix_venv_shebangs.py --quiet    # fix, but say nothing if clean
    python3 pipeline/fix_venv_shebangs.py path/to/.venv [...]

The build scripts call this with --quiet on startup, so a course started by
copying another course's pipeline/ repairs itself on the first render instead
of failing confusingly weeks later.

WHY THIS EXISTS

A new course is normally started by copying an existing course's `pipeline/`
directory, `.venv` and all -- it is far faster than reinstalling manim, torch,
and the TTS models. But a virtualenv is not relocatable: every console script
in `.venv/bin/` (pip, manim, cython, pybabel, jsonschema, ...) carries an
absolute shebang naming the interpreter of the venv it was BUILT in. Copying
the directory does not rewrite them.

The result is a silent-success failure, which is the dangerous kind:

    $ pipeline/.venv/bin/pip install playwright
    Successfully installed playwright-1.62.0        # installed into the OTHER course
    $ pipeline/.venv/bin/python -c "import playwright"
    ModuleNotFoundError: No module named 'playwright'

pip reports success because it really did install something -- just into the
source course's venv, since that is the interpreter its shebang invoked. There
is no error to notice. Measured 2026-08-18: six course repos were affected,
about 41 scripts each, all pointing at systems-design or intro-statistics.

`.venv/bin/python` itself is a symlink to the system interpreter and keeps
working, which is why builds still run -- `pipeline/*.sh` invoke
`.venv/bin/python` directly and never the console scripts. Only the scripts
mislead you, so the damage shows up later as a package that installs but will
not import.

WHAT IT DOES

Rewrites the shebang of every regular file in `<venv>/bin/` whose first line
points at some *other* venv's python, so it names this venv's own interpreter.
Files without a shebang, symlinks, and shebangs that already point here are
left alone. Nothing outside `<venv>/bin/` is touched, and only line 1 of any
file changes.

This is idempotent and safe to run on every build.
"""
import sys
from pathlib import Path

MARKER = "/bin/python"          # only rewrite shebangs naming a python in a venv bin/


def venv_scripts(venv: Path):
    """Regular, non-symlink files in <venv>/bin that start with a shebang."""
    bindir = venv / "bin"
    if not bindir.is_dir():
        return
    for f in sorted(bindir.iterdir()):
        if not f.is_file() or f.is_symlink():
            continue
        try:
            with f.open("rb") as fh:
                head = fh.readline()
        except OSError:
            continue
        if head.startswith(b"#!"):
            yield f, head


def audit(venv: Path):
    """Return [(path, current_shebang)] for scripts pointing at another venv."""
    own = (venv.resolve() / "bin" / "python")
    want = f"#!{own}"
    stale = []
    for f, head in venv_scripts(venv):
        line = head.decode("utf-8", "replace").rstrip("\r\n")
        if MARKER not in line or line == want:
            continue
        # Resolve the interpreter it actually names; if that is this same venv
        # reached by another path (a symlinked repo root, say), it is merely
        # non-canonical rather than wrong -- still worth normalising.
        stale.append((f, line))
    return want, stale


def repoint(venv: Path, want: str, stale):
    for f, _ in stale:
        data = f.read_bytes()
        first_len = data.index(b"\n") + 1 if b"\n" in data else len(data)
        f.write_bytes(want.encode() + b"\n" + data[first_len:])


def main(argv):
    check_only = "--check" in argv
    args = [a for a in argv if not a.startswith("--")]

    if args:
        venvs = [Path(a) for a in args]
    else:
        venvs = [Path(__file__).resolve().parent / ".venv"]

    total, broken_venvs = 0, 0
    for venv in venvs:
        if not (venv / "bin").is_dir():
            print(f"{venv}: no bin/ directory -- skipping", file=sys.stderr)
            continue
        want, stale = audit(venv)
        if not stale:
            continue
        broken_venvs += 1
        total += len(stale)
        names = ", ".join(f.name for f, _ in stale[:6])
        more = f" (+{len(stale) - 6} more)" if len(stale) > 6 else ""
        points_at = stale[0][1][2:]
        print(f"{venv}: {len(stale)} script(s) point at another interpreter")
        print(f"    currently: {points_at}")
        print(f"    should be: {want[2:]}")
        print(f"    affected:  {names}{more}")
        if not check_only:
            repoint(venv, want, stale)
            print(f"    repointed {len(stale)} script(s)")

    if not total:
        if "--quiet" not in argv:
            print("venv console scripts OK (shebangs point at their own interpreter)")
        return 0
    if check_only:
        print(f"\n{total} stale shebang(s) in {broken_venvs} venv(s). "
              f"Fix with:\n    python3 {Path(__file__).name}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
