"""Source-backed public review explanations; never infer science or authority.
Revision History: 2026-10-12 — contextual changes/questions and narrative evidence.
"""
from .review import identifier, string

SECTION_FIELDS = {
    'changes': {'id', 'title', 'before', 'after', 'why_it_matters', 'evidence'},
    'limitations': {'id', 'question', 'why_unanswered', 'goal_impact', 'next_evidence', 'evidence'},
    'insights': {'id', 'title', 'comparison', 'support', 'finding', 'interpretation', 'goal_relevance', 'caveat', 'evidence'},
}
TEXT_FIELDS = {k: v - {'id', 'evidence'} for k, v in SECTION_FIELDS.items()}


def validate(value, source_count):
    if not isinstance(value, dict) or set(value) != {'schema_version', *SECTION_FIELDS} or type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('Unsupported or incomplete contextual review narrative')
    for section, required in SECTION_FIELDS.items():
        items = value[section]
        if not isinstance(items, list) or not 1 <= len(items) <= (12 if section == 'insights' else 6):
            raise ValueError('Explain changes, unanswered questions and evidence in bounded lists')
        seen = set()
        for item in items:
            if not isinstance(item, dict) or set(item) != required:
                raise ValueError('Narrative item needs its full explanatory context')
            identifier(item['id'])
            if item['id'] in seen:
                raise ValueError('Duplicate narrative item identity')
            seen.add(item['id'])
            for key in TEXT_FIELDS[section]:
                string(item[key], 1600 if key not in {'title', 'question'} else 320)
            indices = item['evidence']
            if not isinstance(indices, list) or not indices or len(set(indices)) != len(indices) or any(type(i) is not int or not 0 <= i < source_count for i in indices):
                raise ValueError('Narrative must reference distinct released evidence sources')
    return value


def from_workflow(workflow, summary):
    """Use supplied effort meaning, not guessed metric interpretations or history."""
    efforts = workflow['efforts'][-6:]
    if not efforts:
        return dict(schema_version=1,
            changes=[dict(id='checkpoint',title='Current research question',before=workflow['current_question'],after=summary,why_it_matters=workflow['goal'],evidence=[0])],
            limitations=[dict(id='next-evidence',question=workflow['current_question'],why_unanswered='No study findings are recorded in this overview yet.',goal_impact=workflow['goal'],next_evidence=workflow['next_checkpoint'],evidence=[0])],
            insights=[dict(id='starting-point',title='What is known at this checkpoint',comparison=workflow['current_question'],support='No completed study support has been supplied.',finding=summary,interpretation='This is the author-reported project context, not an experimental conclusion.',goal_relevance=workflow['goal'],caveat='Read the released source and next checkpoint before drawing scientific conclusions.',evidence=[0])])
    return dict(schema_version=1,
        changes=[dict(id=e['id'],title=e['title'],before=e['question'],after=e['outcome'],why_it_matters=e['rationale'],evidence=e['evidence']) for e in efforts],
        limitations=[dict(id=e['id'],question=e['question'],why_unanswered=e['uncertainty'],goal_impact=e['motivation'],next_evidence=e['next_step'],evidence=e['evidence']) for e in efforts],
        insights=[dict(id=e['id'],title=e['title'],comparison=e['approach'],support='Use the cited study for exact observation counts and grouped support; no independent support is inferred here.',finding=e['outcome'],interpretation=e['rationale'],goal_relevance=e['motivation'],caveat=e['uncertainty'],evidence=e['evidence']) for e in efforts])
