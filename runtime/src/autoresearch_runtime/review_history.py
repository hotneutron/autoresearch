"""Read-only navigation of immutable report revisions and experiment providers.

User prompt, verbatim:
I need to monitor the history and progress of the expeirments in the review dashbaord. But now I can see is r48 snapshot. I have no visibility of what happened before. and overview tab doesn't show r1-r131 either. The current dashboard is un-usable.
## Revision History
- 2026-10-21T01:31:00Z: Bounded catalogs and exact packet retrieval; old revisions
  remain immutable/read-only and never inherit current approvals or execution.
"""
from __future__ import annotations
import json
from .review import identifier, now


def page_args(offset=0, limit=50):
    offset, limit = int(offset), int(limit)
    if offset < 0 or not 1 <= limit <= 100:
        raise ValueError('History needs offset >= 0 and limit between 1 and 100')
    return offset, limit


def catalog(inbox, branch=None, offset=0, limit=50):
    offset, limit = page_args(offset, limit)
    if branch is not None:
        identifier(branch)
    with inbox.connect() as db:
        series = [dict(r) for r in db.execute('SELECT p.branch,COUNT(*) AS count,MIN(p.revision) AS oldest_revision,MAX(p.revision) AS latest_revision,(SELECT id FROM packets q WHERE q.branch=p.branch ORDER BY revision LIMIT 1) AS first_packet_id,(SELECT id FROM packets q WHERE q.branch=p.branch ORDER BY revision DESC LIMIT 1) AS latest_packet_id FROM packets p GROUP BY p.branch ORDER BY p.branch')]
        where, args = (' WHERE branch=?', [branch]) if branch is not None else ('', [])
        total = db.execute('SELECT COUNT(*) FROM packets' + where, args).fetchone()[0]
        rows = db.execute('SELECT id,branch,revision,hash,published,body FROM packets' + where + (' ORDER BY revision DESC,id' if branch is not None else ' ORDER BY published DESC,revision DESC,id') + ' LIMIT ? OFFSET ?', [*args, limit, offset]).fetchall()
        items = []
        for row in rows:
            body = json.loads(row['body'])
            items.append({k: row[k] for k in ('id','branch','revision','hash','published')} | {k: body.get(k) for k in ('title','takeaway','decision','evidence_status','translations')} | {'kind': 'overview' if body.get('workflow',{}).get('kind') == 'overview' else 'study'})
            # Catalog translations are headings only, not the full workflow body.
            items[-1]['translations'] = {locale: {k: value[k] for k in ('title','takeaway','decision') if k in value} for locale,value in (body.get('translations') or {}).items()}
    return {'schema_version':1,'read_only':True,'generated':now(),'branch':branch,'offset':offset,'limit':limit,'total':total,'series':series,'items':items,'next_offset':offset+len(items) if offset+len(items)<total else None}


def packet(inbox, packet_id):
    identifier(packet_id)
    with inbox.connect() as db:
        row = db.execute('SELECT * FROM packets WHERE id=?',(packet_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown report revision')
        p = json.loads(row['body'])
        latest = inbox.latest(db,row['branch'])
        archived = latest['id'] != row['id']
        p.update(hash=row['hash'],published=row['published'],archive_read_only=archived,latest_packet_id=latest['id'])
        p['actions'] = [inbox.action_state(db,row,a) for a in p['actions']]
        if archived:
            for a in p['actions']:
                a.update(runnable=False,eligible=False,state='historical',state_reason='Historical revision is read-only; open the latest report to steer execution')
        p['acknowledged'] = any(json.loads(r[0])['kind']=='ack' for r in db.execute("SELECT body FROM feedback WHERE packet_id=? AND status!='stale'",(packet_id,)))
        prior = db.execute('SELECT body FROM packets WHERE branch=? AND revision<? ORDER BY revision DESC LIMIT 1',(row['branch'],row['revision'])).fetchone()
        p['previous'] = json.loads(prior[0]) if prior else None
        adjacent = {}
        for key, compare, order in (('older','<','DESC'),('newer','>','ASC')):
            adjacent[key] = db.execute(f'SELECT id FROM packets WHERE branch=? AND revision{compare}? ORDER BY revision {order} LIMIT 1',(row['branch'],row['revision'])).fetchone()
            adjacent[key] = adjacent[key][0] if adjacent[key] else None
        first = db.execute('SELECT id FROM packets WHERE branch=? ORDER BY revision LIMIT 1',(row['branch'],)).fetchone()[0]
        p['revision_navigation'] = {**adjacent,'first':first,'latest':latest['id']}
        feedback = [{**dict(r),'body':json.loads(r['body']),'branch':row['branch']} for r in db.execute('SELECT * FROM feedback WHERE packet_id=? ORDER BY seq DESC LIMIT 200',(packet_id,))]
        if 'workflow' in p:
            for effort in p['workflow']['efforts']:
                target = effort.get('target')
                if target:
                    bound = db.execute('SELECT branch FROM packets WHERE id=?',(target['packet_id'],)).fetchone()
                    current = inbox.latest(db,bound['branch']) if bound else None
                    target.update(is_current=bool(current and current['id']==target['packet_id'] and current['hash']==target['packet_hash']),current_packet_id=current['id'] if current else None)
    return {'schema_version':1,'read_only':True,'packet':p,'feedback':feedback}
