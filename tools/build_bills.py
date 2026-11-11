#!/usr/bin/env python3
"""Build bills.json from a USLege pull, carrying forward what has not changed.

The scheduled refresh builds pull.json in a few steps, running this script between them.
pull.json lives in the scratchpad, never in the repo.

  1. Track pass. Call list-tracks, then get-track-bills for each of the twelve "(90)"
     tracks (limit 99, increasing offset until every bill is read). Then build pull.json
     straight from those tool results, without retyping anything:
       python3 tools/build_bills.py tracks <session record .jsonl> pull.json
     The session record is the newest .jsonl under ~/.claude/projects/ (it holds every
     tool result of the run). The command keeps, for each track, the bills from its most
     recent results and checks the count against the track's totalCount.
     (Equivalent manual format, one entry per bill under "tracks"["<track name>"]:
       {"id": <billId>, "type": "HB", "number": "6", "caption": "<summary field>",
        "lastAction": "<lastAction>", "lastActionDate": "YYYY-MM-DD", "impact": "High"|"Medium"|"Low"|null})

  2. Plan:  python3 tools/build_bills.py plan pull.json [--all-summaries]
     Prints JSON: {"lookup": [billIds], "summary_check": [billIds], "bill_count": N,
     "full_summary_sweep": true|false}
     "lookup" holds new bills and bills whose last action changed. "summary_check" holds
     those same bills plus, on a full sweep, every bill without a summary yet. A full
     sweep runs on Mondays or when --all-summaries is given.

  3. Lookups. Call get-portal-bills once on the "90th Legislative Session Education Bills"
     portal with limit 2000 (follow nextCursor if it is not null). The result is large, so
     it is saved to a file whose path the tool response gives (under the session's
     tool-results folder); pass that file (or several, one per page) here:
       python3 tools/build_bills.py lookups pull.json <portal result file> [...]
     It fills "lookups" for every id in the plan's "lookup" list and prints any bill
     ids that are not on the portal.
     Then, for each id in "summary_check", call list-bill-comments and record under
     "summaries"[id] true when any comment has accessLevel "Portal", else false.

  4. Build:  python3 tools/build_bills.py build pull.json   (writes bills.json)
     Then run tools/validate.py --previous-count <old count> before committing.

Exit code 3 from plan or build means there are no 90th session bills yet: leave the
preview bills.json in place and stop.
"""
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BILLS = ROOT / "bills.json"

# USLege track name (without " (90)") -> dashboard policy area
TRACK_AREAS = {
    "School Finance & Funding": "School Finance",
    "Property Taxes": "Property Taxes",
    "Bonds, Elections & Debt": "Bonds, Elections & Debt",
    "Governance & Local Control": "Governance & Local Control",
    "Accountability & Assessment": "Accountability & Assessment",
    "Curriculum & Instruction": "Curriculum & Instruction",
    "Educator Workforce": "Educator Workforce",
    "Special Populations": "Special Populations",
    "Student Health, Services & Discipline": "Student Health & Discipline",
    "School Safety & Security": "School Safety",
    "School Choice, Charters & Private Education": "School Choice & Charters",
    "Operations & Business": "Operations & Business",
}
AREA_ORDER = list(TRACK_AREAS.values())
SPECIAL = {"FirstSpecial": "1", "SecondSpecial": "2", "ThirdSpecial": "3", "FourthSpecial": "4",
           "FifthSpecial": "5", "SixthSpecial": "6"}


def area_for(track_name):
    base = track_name.replace(" (90)", "").strip()
    if base not in TRACK_AREAS:
        sys.exit(f"Unknown track '{track_name}'. Add it to TRACK_AREAS in tools/build_bills.py.")
    return TRACK_AREAS[base]


def merge_tracks(pull):
    """One record per bill id, with every policy area whose track holds it."""
    bills = {}
    for track_name, rows in pull.get("tracks", {}).items():
        area = area_for(track_name)
        for r in rows:
            b = bills.setdefault(str(r["id"]), dict(r, areas=[]))
            if area not in b["areas"]:
                b["areas"].append(area)
            # prefer a set impact if tracks disagree
            if not b.get("impact") and r.get("impact"):
                b["impact"] = r["impact"]
    for b in bills.values():
        b["areas"].sort(key=AREA_ORDER.index)
    return bills


def previous():
    if not BILLS.exists():
        return {}
    data = json.loads(BILLS.read_text())
    if data.get("preview"):
        return {}  # the preview holds 89th session bills; start the 90th fresh
    return {str(b["id"]): b for b in data["bills"] if "id" in b}


def session_code(legislature, session_type):
    if session_type == "Regular":
        return f"{legislature}R"
    if session_type in SPECIAL:
        return f"{legislature}{SPECIAL[session_type]}"
    sys.exit(f"Unknown session type '{session_type}'")


def plan(pull, all_summaries=False):
    cur, prev = merge_tracks(pull), previous()
    if not cur:
        print(json.dumps({"bill_count": 0, "note": "No 90th session bills yet. Leave bills.json as is."}))
        sys.exit(3)
    full = all_summaries or date.today().weekday() == 0 or not prev
    lookup, summary_check = [], []
    for bid, b in cur.items():
        p = prev.get(bid)
        changed = (not p or p.get("l") != b["lastActionDate"] or p.get("la") != b["lastAction"])
        if changed:
            lookup.append(int(bid))
        if changed or (full and not p.get("sm")):
            summary_check.append(int(bid))
    print(json.dumps({"bill_count": len(cur), "lookup": lookup, "summary_check": summary_check,
                      "full_summary_sweep": full}))


def tracks(session_file, out_file):
    """Build pull.json "tracks" from the get-track-bills results in a session record."""
    def results(o):
        if isinstance(o, dict):
            if o.get("type") == "tool_result":
                c = o.get("content")
                if isinstance(c, str):
                    yield c
                elif isinstance(c, list):
                    for x in c:
                        if isinstance(x, dict) and x.get("type") == "text":
                            yield x["text"]
            else:
                for v in o.values():
                    yield from results(v)
        elif isinstance(o, list):
            for v in o:
                yield from results(v)

    pages = {}  # track name -> list of result payloads, oldest first
    for line in Path(session_file).read_text().splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        for text in results(rec):
            if '"trackedBills"' not in text:
                continue
            try:
                d = json.loads(text)
            except ValueError:
                continue
            if d.get("trackedBills"):
                pages.setdefault(d["trackedBills"][0]["trackName"], []).append(d)

    def iso(s):
        return datetime.strptime(s[4:15], "%b %d %Y").date().isoformat()

    out = {}
    for name, ds in pages.items():
        area_for(name)  # fails on an unknown track
        total = ds[-1]["totalCount"]
        rows = {}
        for d in reversed(ds):  # newest first, so the latest copy of a bill wins
            if d["totalCount"] != total:
                break
            for b in d["trackedBills"]:
                rows.setdefault(b["billId"], b)
        if len(rows) != total:
            sys.exit(f"Track '{name}': read {len(rows)} of {total} bills. Read every page, then rerun.")
        out[name] = [{"id": b["billId"], "type": b["billType"], "number": b["billNumber"],
                      "caption": b["summary"], "lastAction": b["lastAction"],
                      "lastActionDate": iso(b["lastActionDate"]), "impact": b.get("impact")}
                     for b in rows.values()]
    Path(out_file).write_text(json.dumps({"tracks": out, "lookups": {}, "summaries": {}},
                                         indent=1, ensure_ascii=False))
    print(json.dumps({name: len(v) for name, v in out.items()}))


def lookups(pull_file, portal_files):
    pull = json.loads(Path(pull_file).read_text())
    cur, prev = merge_tracks(pull), previous()
    portal = {}
    for f in portal_files:
        for b in json.loads(Path(f).read_text())["bills"]:
            portal[str(b["id"])] = b
    missing = []
    for bid, b in cur.items():
        p = prev.get(bid)
        if p and p.get("l") == b["lastActionDate"] and p.get("la") == b["lastAction"]:
            continue
        pb = portal.get(bid)
        if not pb:
            missing.append(f"{b['type']} {b['number']} ({bid})")
            continue
        pull["lookups"][bid] = {"stage": pb["currentStage"], "legislature": pb["legislature"],
                                "sessionType": pb["sessionType"], "filed": pb["firstActionDate"][:10]}
    Path(pull_file).write_text(json.dumps(pull, indent=1, ensure_ascii=False))
    print(json.dumps({"filled": len(pull["lookups"]), "not_on_portal": missing}))


def build(pull):
    cur, prev = merge_tracks(pull), previous()
    if not cur:
        print("No 90th session bills yet. bills.json left as is.")
        sys.exit(3)
    lookups = pull.get("lookups", {})
    summaries = pull.get("summaries", {})
    out, missing = [], []
    for bid, b in cur.items():
        p = prev.get(bid, {})
        lk = lookups.get(bid)
        if lk:
            stage, sess, filed = lk["stage"], session_code(lk["legislature"], lk["sessionType"]), lk["filed"][:10]
        elif p:
            stage, sess, filed = p["st"], p["s"], p["f"]
        else:
            missing.append(bid)
            continue
        out.append({
            "id": int(bid),
            "b": f"{b['type']} {b['number']}",
            "s": sess,
            "c": b["caption"],
            "a": b["areas"],
            "i": b.get("impact") or "",
            "st": stage,
            "f": filed,
            "l": b["lastActionDate"][:10],
            "la": b["lastAction"],
            "sm": bool(summaries.get(bid, p.get("sm", False))),
        })
    if missing:
        sys.exit(f"Missing lookups for new bills: {missing}. Run the lookup step for them.")
    out.sort(key=lambda x: (x["b"].split()[0], int(x["b"].split()[1])))
    BILLS.write_text(json.dumps({"updated": date.today().isoformat(), "preview": False, "bills": out},
                                indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {len(out)} bills to bills.json")


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else ""
    if cmd == "plan" and len(args) in (2, 3) and args[2:] in ([], ["--all-summaries"]):
        plan(json.loads(Path(args[1]).read_text()), all_summaries=len(args) == 3)
    elif cmd == "build" and len(args) == 2:
        build(json.loads(Path(args[1]).read_text()))
    elif cmd == "tracks" and len(args) == 3:
        tracks(args[1], args[2])
    elif cmd == "lookups" and len(args) >= 3:
        lookups(args[1], args[2:])
    else:
        sys.exit(__doc__)
