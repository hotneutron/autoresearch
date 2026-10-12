"""Validate display-only translations without changing evidence or authority."""
from .review import string

LOCALES = {"zh-CN"}
PACKET_TEXT = {"title", "question", "takeaway", "why_it_matters", "decision", "review_question", "recommendation", "review_by"}
WORKFLOW_TEXT = {"project_name", "goal", "background", "current_question", "next_checkpoint"}
EFFORT_TEXT = {"title", "question", "motivation", "approach", "outcome", "decision", "rationale", "uncertainty", "next_step"}


def fields(value, allowed):
    if not isinstance(value, dict) or value.keys() - allowed:
        raise ValueError("Translation contains unknown or non-display fields")


def texts(value, limit=2000):
    for text in value.values():
        string(text, limit)


def aligned(value, original):
    if not isinstance(value, list) or len(value) != len(original):
        raise ValueError("Translated items must align with canonical items")


def validate_translations(translations, packet):
    if not isinstance(translations, dict) or translations.keys() - LOCALES:
        raise ValueError("Unsupported translation locale")
    for locale, translated in translations.items():
        fields(translated, PACKET_TEXT | {"changed", "limitations", "workflow", "sources", "metrics", "actions"})
        texts({k: v for k, v in translated.items() if k in PACKET_TEXT})
        for key in ("changed", "limitations"):
            if key in translated:
                aligned(translated[key], packet[key])
                for value in translated[key]:
                    string(value, 2000)
        for key, allowed in (("sources", {"label"}), ("metrics", {"name", "rule", "scope"}), ("actions", {"label"})):
            if key in translated:
                aligned(translated[key], packet[key])
                for value in translated[key]:
                    fields(value, allowed); texts(value)
        if "workflow" in translated:
            if "workflow" not in packet:
                raise ValueError("Translation cannot introduce a workflow")
            value, original = translated["workflow"], packet["workflow"]
            fields(value, WORKFLOW_TEXT | {"success_criteria", "glossary", "efforts", "feedback_dispositions"})
            texts({k:v for k,v in value.items() if k in WORKFLOW_TEXT})
            if "success_criteria" in value:
                aligned(value["success_criteria"], original["success_criteria"])
                for text in value["success_criteria"]: string(text, 2000)
            if "glossary" in value:
                aligned(value["glossary"], original["glossary"])
                for entry in value["glossary"]:
                    fields(entry, {"term", "meaning"}); texts(entry)
            if "efforts" in value:
                aligned(value["efforts"], original["efforts"])
                for entry, canonical in zip(value["efforts"], original["efforts"]):
                    fields(entry, EFFORT_TEXT | {"id", "alternatives"})
                    if entry.get("id") != canonical["id"]:
                        raise ValueError("Translated effort identity differs")
                    texts({k:v for k,v in entry.items() if k in EFFORT_TEXT})
                    if "alternatives" in entry:
                        aligned(entry["alternatives"], canonical["alternatives"])
                        for alternative in entry["alternatives"]:
                            fields(alternative, {"option", "reason"}); texts(alternative)
            if "feedback_dispositions" in value:
                aligned(value["feedback_dispositions"], original["feedback_dispositions"])
                for entry, canonical in zip(value["feedback_dispositions"], original["feedback_dispositions"]):
                    fields(entry, {"feedback_id", "reason"})
                    if entry.get("feedback_id") != canonical["feedback_id"]:
                        raise ValueError("Translated feedback identity differs")
                    if "reason" in entry: string(entry["reason"], 2000)
