"""Vendor orchestration: sandbox-run each vendors.txt line, classify, confirm, copy into the lib, merge lock + bundle."""
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import marketplace, tui
from .dirhash import tree_hash
from .doctor import LockError, read_lock
from .vendor import CHANGED, NEW, PROTECTED, UNCHANGED, Change, VendorError, classify, parse_vendors, read_lib_lock, write_lib_lock


def _review(c: Change) -> None:
    for label, files in (("changed", c.changed), ("added", c.added), ("removed", c.removed)):
        if files:
            print(f"    {label}: {', '.join(files)}")
    if c.risky:
        print(f"    ⚠ scripts/executables: {', '.join(c.risky)}")


def _install(src: Path, dest: Path, expect_hash: str) -> bool:
    """Copy via a temp sibling, verify hash, then swap in (so a bad copy never replaces a good skill)."""
    tmp = dest.with_name(f".{dest.name}.vendor-tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(src, tmp)
    if tree_hash(tmp) != expect_hash:
        shutil.rmtree(tmp)
        return False
    shutil.rmtree(dest, ignore_errors=True)
    tmp.rename(dest)
    return True


def run_vendor(lib: Path, vendors_file: Path, *, yes: bool = False, dry_run: bool = False, exec_=subprocess.run,
               confirm=tui.vendor_confirm, pick_bundle=tui.pick_bundle) -> int:
    if not vendors_file.is_file():
        print(f"error: {vendors_file} not found")
        return 2
    try:
        lines = parse_vendors(vendors_file.read_text())
    except VendorError as e:
        print(f"error: {vendors_file.name}: {e}")
        return 2

    rc = 0
    lock = read_lib_lock(lib)
    applied: list[tuple[str, str | None]] = []  # (new skill name, bundle hint) needing a bundle check
    lock_dirty = False
    for line in lines:
        print(f"\n{line.source}: {', '.join(line.skills)}")
        if line.ignored:
            print(f"  (ignored flags: {' '.join(line.ignored)}; sandbox is project-scope)")
        with tempfile.TemporaryDirectory(prefix="skills-tui-vendor-") as tmp:
            sandbox = Path(tmp)
            cmd = ["npx", "--yes", "skills", "add", line.source, "-s", *line.skills, "-a", "claude-code", "-y"]
            res = exec_(cmd, cwd=sandbox, capture_output=True, text=True)
            if res.returncode:
                print(f"  error: npx skills failed (rc={res.returncode}) {getattr(res, 'stderr', '') or ''}".rstrip())
                rc = 1
                continue
            try:
                got = read_lock(sandbox)
            except LockError as e:
                print(f"  error: {e}")
                rc = 1
                continue
            for name in line.skills:
                src = sandbox / ".claude/skills" / name
                entry = got.get(name)
                if entry is None or not src.is_dir():
                    print(f"  {name}: error: not found in source")
                    rc = 1
                    continue
                if tree_hash(src) != entry.get("computedHash"):
                    print(f"  {name}: error: sandbox hash mismatch, skipped")
                    rc = 1
                    continue
                change = classify(name, src, entry, lib, lock)
                print(f"  {name}: {change.status}" + (f" ({change.detail})" if change.detail else ""))
                if change.status in (UNCHANGED, PROTECTED):
                    continue
                _review(change)
                if dry_run:
                    continue
                if change.status == CHANGED and yes:
                    print("    skipped: --yes never applies updates to existing skills")
                    continue
                if not (change.status == NEW and yes) and not confirm(change):
                    print("    kept as is")
                    continue
                if not _install(src, lib / "skills" / name, entry["computedHash"]):
                    print("    error: copy hash mismatch, not applied")
                    rc = 1
                    continue
                lock[name] = entry
                lock_dirty = True
                print(f"    {'added' if change.status == NEW else 'updated'}")
                if change.status == NEW:
                    applied.append((name, line.bundle))

    if lock_dirty:
        write_lib_lock(lib, lock)
        if applied:
            _bundle_new(lib, applied, pick_bundle, interactive=not yes)
        print("\nDone. Review with `git diff`; nothing was committed.")
    return rc


def _bundle_new(lib: Path, applied: list[tuple[str, str | None]], pick_bundle, interactive: bool) -> None:
    data = marketplace.load(lib)
    have = marketplace.bundled_skills(data)
    for name, hint in applied:
        if name in have:
            continue
        if hint:
            marketplace.add_to_bundle(data, hint, [name], description=f"Vendored: {hint}")
        elif interactive:
            picked = pick_bundle(name, marketplace.bundle_names(data))
            if picked:
                marketplace.add_to_bundle(data, picked[0], [name], description=picked[1])
        if name not in marketplace.bundled_skills(data):
            print(f"  ⚠ {name} is not in any marketplace bundle (add it before committing)")
    marketplace.save(lib, data)
