"""Project-neutral public decision records; publication never grants authority."""
from datetime import datetime
import re

from .review import identifier, string

STATUSES = {"planned", "running", "completed", "blocked", "deferred", "stopped"}
WORKFLOW_FIELDS = {"kind", "project_id", "project_name", "goal", "background", "success_criteria",
                   "status", "current_question", "next_checkpoint", "updated_at", "glossary", "efforts",
                   "feedback_dispositions"}
EFFORT_FIELDS = {"id", "title", "status", "question", "motivation", "approach", "alternatives",
                 "outcome", "decision", "rationale", "uncertainty", "next_step", "evidence"}


def object_fields(value, required, optional=()):
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - set(optional):
        raise ValueError("Workflow object has missing or unknown fields")


def evidence_indices(value, source_count):
    if not isinstance(value, list) or not 1 <= len(value) <= source_count:
        raise ValueError("Workflow needs distinct released evidence references")
    if any(type(i) is not int or not 0 <= i < source_count for i in value):
        raise ValueError("Workflow evidence reference is out of range")
    if len(set(value)) != len(value):
        raise ValueError("Workflow evidence references must be distinct")


def validate_workflow(value, source_count):
    object_fields(value, WORKFLOW_FIELDS)
    if value["kind"] != "overview":
        raise ValueError("Unknown workflow kind")
    identifier(value["project_id"])
    string(value["project_name"], 280)
    for key in ("goal", "current_question", "next_checkpoint"):
        string(value[key], 600)
    string(value["background"], 2000)
    criteria = value["success_criteria"]
    if not isinstance(criteria, list) or not 1 <= len(criteria) <= 12:
        raise ValueError("Explain success in 1–12 plain-language criteria")
    for criterion in criteria:
        string(criterion, 600)
    if not isinstance(value["status"], str) or value["status"] not in STATUSES:
        raise ValueError("Unknown workflow status")
    string(value["updated_at"], 100)
    stamp = datetime.fromisoformat(value["updated_at"])
    if stamp.tzinfo is None:
        raise ValueError("Workflow updated_at must include a timezone")
    glossary = value["glossary"]
    if not isinstance(glossary, list) or len(glossary) > 40:
        raise ValueError("Glossary must be a list of at most 40 terms")
    terms = set()
    for entry in glossary:
        object_fields(entry, {"term", "meaning"})
        string(entry["term"], 100); string(entry["meaning"], 600)
        if entry["term"].casefold() in terms:
            raise ValueError("Duplicate glossary term")
        terms.add(entry["term"].casefold())
    efforts = value["efforts"]
    if not isinstance(efforts, list) or len(efforts) > 100:
        raise ValueError("Provide at most 100 released effort summaries")
    seen = set()
    for effort in efforts:
        object_fields(effort, EFFORT_FIELDS, {"target"})
        identifier(effort["id"])
        if effort["id"] in seen:
            raise ValueError("Duplicate workflow effort id")
        seen.add(effort["id"])
        if effort["status"] not in STATUSES:
            raise ValueError("Unknown effort status")
        for field in EFFORT_FIELDS - {"id", "status", "alternatives", "evidence"}:
            string(effort[field], 1200 if field in {"rationale", "uncertainty", "motivation"} else 600)
        alternatives = effort["alternatives"]
        if not isinstance(alternatives, list) or len(alternatives) > 6:
            raise ValueError("Provide at most six alternatives considered")
        for alternative in alternatives:
            object_fields(alternative, {"option", "reason"})
            string(alternative["option"], 500); string(alternative["reason"], 600)
        evidence_indices(effort["evidence"], source_count)
        if "target" in effort:
            target = effort["target"]
            object_fields(target, {"packet_id", "packet_hash"})
            identifier(target["packet_id"])
            if not isinstance(target["packet_hash"], str) or not re.fullmatch(r"[a-f0-9]{64}", target["packet_hash"]):
                raise ValueError("Study target requires its exact packet hash")
    dispositions = value["feedback_dispositions"]
    if not isinstance(dispositions, list) or len(dispositions) > 100:
        raise ValueError("Provide at most 100 feedback dispositions")
    seen = set()
    for disposition in dispositions:
        object_fields(disposition, {"feedback_id", "disposition", "reason", "evidence"})
        identifier(disposition["feedback_id"])
        if disposition["feedback_id"] in seen:
            raise ValueError("Duplicate feedback disposition")
        seen.add(disposition["feedback_id"])
        if disposition["disposition"] not in {"adopted", "deferred", "declined"}:
            raise ValueError("Unknown feedback disposition")
        string(disposition["reason"], 1200)
        evidence_indices(disposition["evidence"], source_count)


def overview_packet(document):
    """Build an advisory-only packet. Caller supplies meaning and released sources."""
    object_fields(document, {"schema_version", "revision", "summary", "workflow", "sources", "prompt_verbatim"}, {"metrics", "translations", "changed", "limitations", "narrative"})
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ValueError("Overview document schema_version must be 1")
    workflow = document["workflow"]
    if not isinstance(document["sources"], list) or not 1 <= len(document["sources"]) <= 12:
        raise ValueError("Overview needs 1–12 released sources")
    validate_workflow(workflow, len(document["sources"]))
    string(document["summary"], 320); string(document["prompt_verbatim"], 32000)
    branch = identifier(workflow["project_id"] + "-overview")
    revision = document["revision"]
    if type(revision) is not int or revision < 1:
        raise ValueError("Overview revision must be a positive integer")
    from .narrative import from_workflow, validate
    from .review import strings
    narrative = document.get("narrative") or from_workflow(workflow, document["summary"])
    validate(narrative, len(document["sources"]))
    changed = document.get("changed", [document["summary"], "The current question is: " + workflow["current_question"]])
    limitations = document.get("limitations", ["Next evidence needed: " + workflow["next_checkpoint"],
        "This overview explains the reported findings; it does not itself measure whether the project has met: " + workflow["success_criteria"][0]])
    strings(changed); strings(limitations)
    return dict(schema_version=2, id=identifier(f"{branch}-r{revision}"), branch=branch,
                contract_id=identifier(workflow["project_id"]), revision=revision,
                title=f"{workflow['project_name']} · Start here", question="What are we trying to learn, why, and what happens next?",
                takeaway=document["summary"], why_it_matters="Follow the goal, evidence and public decision rationale before inspecting technical reports.",
                decision="Workflow status: " + workflow["status"], changed=changed,
                limitations=limitations, narrative=narrative,
                evidence_status="diagnostic", review_mode="advice", review_question="Suggest a direction here, or open a linked current study to steer its declared actions.",
                recommendation="Read Start here, then why each effort was tried, its evidence, uncertainty and next step.",
                review_by="Next safe research checkpoint; no deadline grants approval", historical=False,
                metrics=document.get("metrics", []), actions=[], sources=document["sources"], workflow=workflow,
                prompt_verbatim=document["prompt_verbatim"],
                **({"translations": document["translations"]} if "translations" in document else {}))


def publish_overview(inbox, document):
    return inbox.publish(overview_packet(document))
