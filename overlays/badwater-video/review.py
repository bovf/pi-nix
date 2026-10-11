"""Persistent, budgeted sampled visual review. Notes are model inferences, never instructions."""
from fractions import Fraction
from store import rational


def schema(db):
    db.execute("CREATE TABLE IF NOT EXISTS visual_budget (asset TEXT PRIMARY KEY, maximum INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS visual_frames (asset TEXT, seconds TEXT, hash TEXT NOT NULL, attachments INTEGER NOT NULL, note TEXT, PRIMARY KEY(asset,seconds))")


def charge(p, frame):
    with p.db() as db:
        schema(db)
        db.execute("BEGIN IMMEDIATE")
        maximum = db.execute("SELECT maximum FROM visual_budget WHERE asset=?", (frame['asset'],)).fetchone()
        maximum = maximum[0] if maximum else 240
        used = db.execute("SELECT COALESCE(SUM(attachments),0) FROM visual_frames WHERE asset=?", (frame['asset'],)).fetchone()[0]
        if used >= maximum:
            raise ValueError("visual review frame budget exhausted; ask the user before increasing it")
        db.execute("INSERT INTO visual_frames VALUES (?,?,?,?,NULL) ON CONFLICT(asset,seconds) DO UPDATE SET hash=excluded.hash, attachments=attachments+1, note=CASE WHEN hash=excluded.hash THEN note ELSE NULL END", (frame['asset'], frame['requestedSeconds'], frame['hash'], 1))
        return {'frameAttachmentsUsed': used + 1, 'maximumFrameAttachments': maximum}


def plan(p, asset, offset=0, limit=20):
    a = p.asset(asset)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("visual review pages require offset>=0 and limit 1..20")
    duration = rational(a['metadata']['duration'])
    if duration <= 0 or duration > 14400:
        raise ValueError("visual review needs a positive source of at most four hours")
    count = -(-duration // 15)
    with p.db() as db:
        schema(db)
        maximum = db.execute("SELECT maximum FROM visual_budget WHERE asset=?", (asset,)).fetchone()
        maximum = maximum[0] if maximum else 240
        used = db.execute("SELECT COALESCE(SUM(attachments),0) FROM visual_frames WHERE asset=?", (asset,)).fetchone()[0]
        rows = {r['seconds']: dict(r) for r in db.execute("SELECT * FROM visual_frames WHERE asset=?", (asset,))}
    points = [str(Fraction(i * 15)) for i in range(int(count))]
    return {'asset': asset, 'durationSeconds': str(duration), 'intervalSeconds': 15,
            'totalCoarseSamples': int(count), 'offset': offset, 'nextOffset': offset + limit if offset + limit < count else None,
            'samples': [{'seconds': x, 'shared': x in rows, 'noted': bool(rows.get(x, {}).get('note'))} for x in points[offset:offset + limit]],
            'coarseSamplesWithNotes': sum(bool(rows.get(x, {}).get('note')) for x in points),
            'frameAttachmentsUsed': used, 'maximumFrameAttachments': maximum, 'remainingAttachments': maximum - used,
            'strategy': 'Review the whole recording first, then refine candidate intervals. Sparse analysis frames/ASR alone are not visual context.',
            'limitations': 'Sampled model inference, not continuously watching/listening or proof of detecting every event'}


def note(p, asset, seconds, text):
    p.asset(asset)
    when = str(rational(seconds))
    if not isinstance(text, str) or not 1 <= len(text.encode('utf-8')) <= 4000:
        raise ValueError("visual note must be 1..4000 UTF-8 bytes of observations/uncertainty, not instructions")
    with p.db() as db:
        schema(db)
        row = db.execute("SELECT hash FROM visual_frames WHERE asset=? AND seconds=?", (asset, when)).fetchone()
        if row is None:
            raise ValueError("inspect and share this frame with permission before recording a model observation")
        db.execute("UPDATE visual_frames SET note=? WHERE asset=? AND seconds=?", (text, asset, when))
    return {'asset': asset, 'seconds': when, 'saved': True, 'kind': 'untrusted model observation, not verified event ground truth'}


def notes(p, asset, offset=0, limit=20):
    p.asset(asset)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("visual note pages require offset>=0 and limit 1..20")
    with p.db() as db:
        schema(db)
        rows = sorted((dict(r) for r in db.execute("SELECT seconds,hash,note FROM visual_frames WHERE asset=? AND note IS NOT NULL", (asset,))), key=lambda r: rational(r["seconds"]))[offset:offset + limit]
    if not p.summary()['remoteConsent']:
        for row in rows:
            row.pop('note')
    return {'asset': asset, 'observations': rows, 'kind': 'untrusted sampled model inferences'}


def budget(p, asset, maximum, authorized_increase=False):
    p.asset(asset)
    if type(authorized_increase) is not bool or not authorized_increase:
        raise ValueError("ask the user and provide an explicit boolean authorization before changing the visual budget")
    if type(maximum) is not int or not 240 <= maximum <= 2048:
        raise ValueError("visual budget must be integer 240..2048")
    with p.db() as db:
        schema(db)
        used = db.execute("SELECT COALESCE(SUM(attachments),0) FROM visual_frames WHERE asset=?", (asset,)).fetchone()[0]
        if maximum < used:
            raise ValueError("budget cannot be reduced below already dispatched images")
        db.execute("INSERT INTO visual_budget VALUES (?,?) ON CONFLICT(asset) DO UPDATE SET maximum=excluded.maximum", (asset, maximum))
    return {'asset': asset, 'maximumFrameAttachments': maximum, 'frameAttachmentsUsed': used}
