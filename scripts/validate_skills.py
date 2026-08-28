#!/usr/bin/env python3
"""Validate SKILL.md frontmatter and directory layout for all skills."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"
DECISIONS_MD = REPO_ROOT / "docs" / "discuss" / "DECISIONS.md"
README_MD = REPO_ROOT / "README.md"
DISCUSS_DIR = REPO_ROOT / "docs" / "discuss"
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKIP_DIRS = {"template", "_template"}

PIPELINE_STAGES = {"exploring", "deciding", "ready-for-implementation", "blocked"}
ID_PATTERN = re.compile(r"(?:INV|ORD|EXP)-\d+[a-z]?")
STATUS_MAX_CHARS = 400
BLOCKED_ON_MAX_CHARS = 30
THREAD_FIELDS = {"id", "state", "last_round", "blocked_on"}
THREAD_STATES = {"open", "blocked", "paused", "closed"}
THREAD_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
THREAD_WIP_MAX = 3
THREAD_WIP_STATES = {"open", "blocked"}
EXP_TABLE_HEADING = "## 待验证尝试"
SKILLS_REF_PATTERN = re.compile(r"skills/([a-z0-9][a-z0-9-]*)/")

# 承重事实（K）table — see docs/discuss/34-*.md (INV-05 / ORD-53).
FACT_SECTION_HEADING = "## 承重事实"
FACT_ID_PATTERN = re.compile(r"^FACT-\d+$")
FACT_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FACT_COLUMNS = 8
FACT_STATES = {"已查证", "待查证·阻塞", "不敏感"}
FACT_GROUNDINGS = {"世界固有", "项目已交付", "外部系统"}
PLACEHOLDER_CELLS = {"", "—", "-", "–"}


def parse_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("missing YAML frontmatter (must start with ---)")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("unclosed YAML frontmatter")
    meta = yaml.safe_load(parts[1])
    if not isinstance(meta, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return meta


def validate_skill(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"]

    try:
        meta = parse_frontmatter(skill_md)
    except (yaml.YAMLError, ValueError) as exc:
        return [f"{skill_dir.name}: {exc}"]

    name = meta.get("name")
    description = meta.get("description")

    if not name or not isinstance(name, str):
        errors.append(f"{skill_dir.name}: 'name' is required in frontmatter")
    elif len(name) > 64:
        errors.append(f"{skill_dir.name}: 'name' exceeds 64 characters")
    elif not NAME_PATTERN.match(name):
        errors.append(f"{skill_dir.name}: 'name' must be lowercase alphanumeric with hyphens")
    elif name != skill_dir.name:
        errors.append(f"{skill_dir.name}: directory name must match name '{name}'")

    if not description or not isinstance(description, str) or not description.strip():
        errors.append(f"{skill_dir.name}: 'description' is required and must be non-empty")
    elif len(description) > 1024:
        errors.append(f"{skill_dir.name}: 'description' exceeds 1024 characters")

    body_lines = skill_md.read_text(encoding="utf-8").splitlines()
    if len(body_lines) > 600:
        errors.append(f"{skill_dir.name}: SKILL.md is very long ({len(body_lines)} lines); consider references/")

    return errors


def _extract_first_yaml_block(text: str) -> str | None:
    """Return the body of the first ```yaml fenced block, or None."""
    match = re.search(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    return match.group(1) if match else None


def _exp_table_status(decisions_text: str) -> dict[str, str]:
    """Map each EXP id to its 状态 cell (last column) in the §待验证尝试 table only.

    Scoping to that one section matters: several EXP ids also have rows in
    §外部前提登记与复查协议, whose last column is a review note rather than an
    execution status. That table appears later in the file, so an unscoped scan
    silently overwrote the real status and made C2 miss closed experiments.
    """
    status: dict[str, str] = {}
    in_section = False
    for line in decisions_text.splitlines():
        if line.startswith("## "):
            in_section = line.startswith(EXP_TABLE_HEADING)
            continue
        if not in_section or not line.lstrip().startswith("| EXP-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        exp_id = cells[0]
        if ID_PATTERN.fullmatch(exp_id):
            status[exp_id] = cells[-1]
    return status


def _sync_section_ids(round_text: str) -> set[str]:
    """IDs appearing in any 'DECISIONS 同步状态' section of a round file."""
    ids: set[str] = set()
    in_section = False
    for line in round_text.splitlines():
        if line.startswith("#"):
            in_section = "DECISIONS 同步状态" in line
            continue
        if in_section and line.lstrip().startswith("|"):
            ids.update(ID_PATTERN.findall(line))
    return ids


def _fact_rows(decisions_text: str) -> list[tuple[int, list[str]]]:
    """Rows of the §承重事实（K） table as (line_no, cells); ORD-53."""
    rows: list[tuple[int, list[str]]] = []
    in_section = False
    for lineno, line in enumerate(decisions_text.splitlines(), start=1):
        if line.startswith("## "):
            in_section = line.startswith(FACT_SECTION_HEADING)
            continue
        if not in_section:
            continue
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if cells and FACT_ID_PATTERN.match(cells[0]):
            rows.append((lineno, cells))
    return rows


def _check_fact_row(lineno: int, cells: list[str], known_ids: set[str]) -> list[str]:
    """C8: structural checks on one K row. Zero semantics — whether the claim is
    *true* stays with the human (Four Dark Corners §6.3: K is validated informally);
    the machine only checks the slot is well-formed. See docs/discuss/34-*.md."""
    fid = cells[0]
    prefix = f"cross-artifact[C8]: {fid} (line {lineno})"
    if len(cells) != FACT_COLUMNS:
        return [f"{prefix}: has {len(cells)} columns (expected {FACT_COLUMNS})"]

    _, _, evidence, checked_on, supports, grounding, state, recheck = cells
    errors: list[str] = []

    if state not in FACT_STATES:
        errors.append(f"{prefix}: 状态 '{state}' not in {sorted(FACT_STATES)}")
    if grounding not in FACT_GROUNDINGS:
        errors.append(f"{prefix}: 接地依据 '{grounding}' not in {sorted(FACT_GROUNDINGS)}")

    # Reverse-driven: a fact with no dependent decision is not load-bearing and
    # belongs in the round file, not here (ORD-53(b)).
    if supports in PLACEHOLDER_CELLS:
        errors.append(f"{prefix}: supports is empty — not load-bearing; keep it in the round file")
    for rid in ID_PATTERN.findall(supports):
        if rid not in known_ids:
            errors.append(f"{prefix}: supports '{rid}' absent from DECISIONS.md")

    if state == "已查证":
        if "http" not in evidence and "](" not in evidence:
            errors.append(f"{prefix}: 状态=已查证 requires a linked 证据 (got '{evidence}')")
        if not FACT_DATE_PATTERN.match(checked_on):
            errors.append(f"{prefix}: 状态=已查证 requires 查证日期 as YYYY-MM-DD (got '{checked_on}')")
    elif state == "待查证·阻塞" and recheck in PLACEHOLDER_CELLS:
        errors.append(f"{prefix}: 状态=待查证·阻塞 requires a non-empty 复查触发")

    return errors


def _check_thread(entry: object) -> list[str]:
    """C6: a thread row may only hold bounded types — never a sentence."""
    if not isinstance(entry, dict):
        return [f"cross-artifact[C6]: thread entry must be a mapping, got {type(entry).__name__}"]
    tid = entry.get("id")
    errors: list[str] = []
    if not isinstance(tid, str) or not THREAD_ID_PATTERN.fullmatch(tid):
        errors.append(f"cross-artifact[C6]: thread id '{tid}' must match {THREAD_ID_PATTERN.pattern}")
    if set(entry) != THREAD_FIELDS:
        errors.append(
            f"cross-artifact[C6]: thread '{tid}' fields {sorted(entry)} != {sorted(THREAD_FIELDS)}"
        )
    if entry.get("state") not in THREAD_STATES:
        errors.append(
            f"cross-artifact[C6]: thread '{tid}' state '{entry.get('state')}' not in {sorted(THREAD_STATES)}"
        )
    if not isinstance(entry.get("last_round"), int):
        errors.append(f"cross-artifact[C6]: thread '{tid}' last_round must be an int")
    blocked_on = entry.get("blocked_on")
    if not isinstance(blocked_on, str):
        errors.append(f"cross-artifact[C6]: thread '{tid}' blocked_on must be a string")
    elif len(blocked_on) > BLOCKED_ON_MAX_CHARS:
        errors.append(
            f"cross-artifact[C6]: thread '{tid}' blocked_on is {len(blocked_on)} chars "
            f"(max {BLOCKED_ON_MAX_CHARS})"
        )
    return errors


def report_thread_ages() -> list[str]:
    """Derive each thread's stall age instead of storing it, so it cannot go stale.

    Age is the number the human actually wants ("what's stuck?") and it existed
    nowhere in the system before; printing it here puts it at the point of use.
    """
    if not DECISIONS_MD.is_file():
        return []
    yaml_body = _extract_first_yaml_block(DECISIONS_MD.read_text(encoding="utf-8"))
    try:
        threads = yaml.safe_load(yaml_body)["pipeline-state"]["threads"]
    except Exception:  # noqa: BLE001 - purely informational; never block on it
        return []
    rounds = [int(m.group(1)) for p in DECISIONS_MD.parent.glob("*.md")
              if (m := re.match(r"(\d{2})-", p.name))]
    if not rounds or not isinstance(threads, list):
        return []
    latest = max(rounds)
    lines = [f"threads (round {latest}):"]
    for t in threads:
        age = latest - t["last_round"]
        stall = f" · 停滞 {age} 轮" if t["state"] != "closed" and age else ""
        blocked = f" · blocked_on: {t['blocked_on']}" if t.get("blocked_on") else ""
        lines.append(f"  {t['id']:<14} {t['state']:<8} r{t['last_round']}{stall}{blocked}")
    return lines


def validate_cross_artifact() -> list[str]:
    """Cross-artifact consistency checks (C1–C8); see docs/discuss/15-*.md, 33-*.md, 34-*.md."""
    errors: list[str] = []

    if not DECISIONS_MD.is_file():
        return [f"cross-artifact: DECISIONS.md not found: {DECISIONS_MD}"]
    decisions_text = DECISIONS_MD.read_text(encoding="utf-8")

    # C1: pipeline-state block present with required fields + valid stage.
    pipeline_state: dict | None = None
    yaml_body = _extract_first_yaml_block(decisions_text)
    if yaml_body is None:
        errors.append("cross-artifact[C1]: DECISIONS.md missing ```yaml``` pipeline-state block")
    else:
        try:
            block = yaml.safe_load(yaml_body)
        except yaml.YAMLError as exc:
            block = None
            errors.append(f"cross-artifact[C1]: pipeline-state block is not valid YAML: {exc}")
        if isinstance(block, dict) and isinstance(block.get("pipeline-state"), dict):
            pipeline_state = block["pipeline-state"]
            for field in ("stage", "status", "pending_exp"):
                if field not in pipeline_state:
                    errors.append(f"cross-artifact[C1]: pipeline-state missing '{field}'")
            stage = pipeline_state.get("stage")
            if stage is not None and stage not in PIPELINE_STAGES:
                errors.append(
                    f"cross-artifact[C1]: pipeline-state.stage '{stage}' not in {sorted(PIPELINE_STAGES)}"
                )
            if "pending_exp" in pipeline_state and not isinstance(pipeline_state["pending_exp"], list):
                errors.append("cross-artifact[C1]: pipeline-state.pending_exp must be a list")
        elif yaml_body is not None:
            errors.append("cross-artifact[C1]: first ```yaml``` block has no 'pipeline-state' mapping")

    # C5/C6: pipeline-state entropy bounds; see docs/discuss/33-*.md.
    # ORD-32 bounded the ≤12-line summary but left `status` unbounded, so all
    # pressure migrated there (284 -> 1195 chars in 51 days). Both bounds are
    # pure counting/type checks: zero false positives, inside the ORD-33 line.
    if pipeline_state is not None:
        status = pipeline_state.get("status")
        if isinstance(status, str) and len(status) > STATUS_MAX_CHARS:
            errors.append(
                f"cross-artifact[C5]: pipeline-state.status is {len(status)} chars "
                f"(max {STATUS_MAX_CHARS}); it is an index, not a narrative — "
                f"move prose to §当前态摘要 / §变更日志"
            )
        threads = pipeline_state.get("threads")
        if threads is not None:
            if not isinstance(threads, list):
                errors.append("cross-artifact[C6]: pipeline-state.threads must be a list")
            else:
                for entry in threads:
                    errors.extend(_check_thread(entry))
                # C7: in-flight thread count. `paused`/`closed` are explicit decisions
                # to set work down and do not count — so opening thread N+1 forces that
                # decision instead of letting a thread stall silently (graph: 15 rounds).
                in_flight = [
                    e["id"] for e in threads
                    if isinstance(e, dict) and e.get("state") in THREAD_WIP_STATES
                ]
                if len(in_flight) > THREAD_WIP_MAX:
                    errors.append(
                        f"cross-artifact[C7]: {len(in_flight)} threads in flight "
                        f"(max {THREAD_WIP_MAX}): {in_flight} — pause or close one first"
                    )

    # C2: each pending_exp id exists in the EXP table and is still open.
    exp_status = _exp_table_status(decisions_text)
    if pipeline_state is not None and isinstance(pipeline_state.get("pending_exp"), list):
        for exp_id in pipeline_state["pending_exp"]:
            if exp_id not in exp_status:
                errors.append(
                    f"cross-artifact[C2]: pending_exp '{exp_id}' has no row in §待验证尝试 table"
                )
                continue
            cell = exp_status[exp_id].lower()
            if "passed" in cell or "aborted" in cell:
                errors.append(
                    f"cross-artifact[C2]: pending_exp '{exp_id}' is marked closed (passed/ABORTED) in EXP table"
                )

    # C3: skills/* <-> README index, bidirectional.
    skill_names = {
        p.name
        for p in SKILLS_DIR.iterdir()
        if p.is_dir() and p.name not in SKIP_DIRS and not p.name.startswith(".")
    } if SKILLS_DIR.is_dir() else set()
    if README_MD.is_file():
        readme_text = README_MD.read_text(encoding="utf-8")
        referenced = set(SKILLS_REF_PATTERN.findall(readme_text))
        for name in sorted(skill_names - referenced):
            errors.append(f"cross-artifact[C3]: skill '{name}' not referenced in README.md")
        for name in sorted(referenced - skill_names):
            errors.append(f"cross-artifact[C3]: README.md references skills/{name}/ but no such skill dir")
    else:
        errors.append(f"cross-artifact[C3]: README.md not found: {README_MD}")

    # C4: every id in a round file's 同步状态 section must appear somewhere in DECISIONS.md.
    known_ids = set(ID_PATTERN.findall(decisions_text))
    for round_md in sorted(DISCUSS_DIR.glob("[0-9][0-9]-*.md")):
        round_text = round_md.read_text(encoding="utf-8")
        for rid in sorted(_sync_section_ids(round_text)):
            if rid not in known_ids:
                errors.append(
                    f"cross-artifact[C4]: {round_md.name} 同步状态 references '{rid}' absent from DECISIONS.md"
                )

    # C8: 承重事实（K）table structure (ORD-53). ORD-16 stayed stale for 6 weeks
    # because no container held the fact it rested on; this checks the container.
    seen_fact_ids: set[str] = set()
    for lineno, cells in _fact_rows(decisions_text):
        fid = cells[0]
        if fid in seen_fact_ids:
            errors.append(f"cross-artifact[C8]: duplicate {fid} (line {lineno})")
        seen_fact_ids.add(fid)
        errors.extend(_check_fact_row(lineno, cells, known_ids))

    return errors


def main(argv: list[str]) -> int:
    targets = argv[1:] if len(argv) > 1 else None

    if not SKILLS_DIR.is_dir():
        print(f"error: skills directory not found: {SKILLS_DIR}", file=sys.stderr)
        return 1

    skill_dirs = sorted(
        p for p in SKILLS_DIR.iterdir() if p.is_dir() and p.name not in SKIP_DIRS and not p.name.startswith(".")
    )

    if targets:
        skill_dirs = [SKILLS_DIR / t for t in targets]
        missing = [d for d in skill_dirs if not d.is_dir()]
        if missing:
            for d in missing:
                print(f"error: skill not found: {d.name}", file=sys.stderr)
            return 1

    if not skill_dirs:
        print("warning: no skills found under skills/", file=sys.stderr)
        return 0

    all_errors: list[str] = []
    for skill_dir in skill_dirs:
        all_errors.extend(validate_skill(skill_dir))

    # Cross-artifact checks are repo-global; run only on a full validation (no targets).
    cross_checked = targets is None
    if cross_checked:
        all_errors.extend(validate_cross_artifact())

    if all_errors:
        print("validation failed:", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    suffix = " + cross-artifact (C1–C8)" if cross_checked else ""
    print(f"ok: {len(skill_dirs)} skill(s) validated{suffix}")
    if cross_checked:
        for line in report_thread_ages():
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
