"""Evidence-bound before/after plan changes produce a new contract, never mutate a run."""
from __future__ import annotations
from copy import deepcopy
from .contracts import digest, hash_text, identifier, seal, verify
from .protocol import pointer


def apply_delta(plan, delta, evidence):
    body = verify(delta)
    if body["prior_plan_sha256"] != digest(plan): raise ValueError("Prior plan changed")
    result = deepcopy(plan)
    for change in body["changes"]:
        path = change["pointer"]
        if not path.startswith("/") or not change.get("evidence_ids"): raise ValueError("Evidence-backed field change required")
        if pointer(plan, path) != change["before"] or change["before"] == change["after"]: raise ValueError("Delta before/after does not match actual plan")
        for ref in change["evidence_ids"]:
            if ref not in evidence: raise ValueError("Unknown evidence reference")
            hash_text(evidence[ref])
        tokens = [v.replace("~1", "/").replace("~0", "~") for v in path[1:].split("/")]
        target = result
        for token in tokens[:-1]: target = target[int(token)] if isinstance(target, list) else target[token]
        if isinstance(target, list): target[int(tokens[-1])] = change["after"]
        else: target[tokens[-1]] = change["after"]
    for condition in plan.get("required_conditions", []):
        if condition not in result.get("required_conditions", []): raise ValueError("Inherited scientific condition cannot be removed")
    return seal({"id": body["id"] + "-result", "plan": result, "prior_plan_sha256": digest(plan),
                 "delta_sha256": delta["sha256"], "requires_subject_commit": True, "requires_reviewed_round": True})


def condition_state(condition, subject, stored=None):
    sha = digest({"condition": condition, "subject": subject})
    stored = stored or {}
    return {"subject_sha256": sha, "state": stored.get("state", "pending") if stored.get("subject_sha256") == sha else "pending"}


def materialize_subject_plan(repository, document, result, *, expected_head, approved_delta_sha256):
    """Create a subject plan commit after exact delta approval; successor review is still required."""
    import json
    import subprocess
    from datetime import datetime, timezone
    from pathlib import Path
    from .contracts import relative
    body = verify(result)
    if body['delta_sha256'] != hash_text(approved_delta_sha256):
        raise ValueError('Applied delta approval differs')
    relative(document)
    if not document.startswith('.plan/') or not document.endswith('.md'):
        raise ValueError('Materialize an explicit subject .plan/ Markdown document')
    repository = Path(repository).resolve()
    head = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'HEAD'], text=True).strip()
    if head != expected_head: raise ValueError('Subject HEAD changed before plan materialization')
    if subprocess.check_output(['git', '-C', str(repository), 'status', '--porcelain'], text=True).strip():
        raise ValueError('Subject plan commit requires a clean dedicated checkout')
    target = (repository / document).resolve()
    if not target.is_relative_to(repository) or target.exists():
        raise ValueError('Create a new plan revision in the dedicated subject checkout')
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    plan = body['plan']
    prompt = plan.get('prompt_verbatim', '')
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('Subject plan must preserve its original instruction')
    text = '# Reviewed experiment plan\n\n## User Prompt, Verbatim\n\n```text\n' + prompt + '\n```\n\n'
    text += '## Frozen plan\n\n```json\n' + json.dumps(plan, ensure_ascii=False, indent=2) + '\n```\n\n'
    text += '## Revision History\n\n| Revision | Timestamp | Change |\n|---|---|---|\n| r1 | ' + now + ' | Materialized exact approved delta ' + body['delta_sha256'] + '; successor execution still requires round review. |\n'
    target.parent.mkdir(parents=True, exist_ok=True);target.write_text(text)
    subprocess.run(['git', '-C', str(repository), 'add', '--', document], check=True)
    subprocess.run(['git', '-C', str(repository), 'commit', '-qm', 'research: materialize approved experiment plan delta'], check=True)
    commit = subprocess.check_output(['git', '-C', str(repository), 'rev-parse', 'HEAD'], text=True).strip()
    return {'subject_commit': commit, 'plan_path': document, 'delta_sha256': body['delta_sha256'], 'requires_successor_round_review': True}
