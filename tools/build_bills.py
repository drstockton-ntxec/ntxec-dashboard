#!/usr/bin/env python3
"""Build bills.json from a USLege pull, carrying forward what has not changed.

The scheduled refresh writes pull.json in three steps, running this script between them:

  1. Track pass. For each of the twelve "(90)" tracks, call get-track-bills (page with
     limit 99 until all bills are read) and record each bill under "tracks":
       {"id": <billId>, "type": "HB", "number": "6", "caption": "<summary field>",
        "lastAction": "<lastAction>", "lastActionDate": "YYYY-MM-DD", "impact": "High"|"Medium"|"Low"|null}
     Then run:  python3 tools/build_bills.py plan pull.json
     It prints JSON: {"lookup": [billIds], "summary_check": [billIds], "bill_count": N}

  2. Lookups. For each id in "lookup", call get-portal-bills on the 90th session portal
     with filters.search "<type> <number>", find the result whose id matches, and record
     under "lookups"[id]: {"stage": currentStage, "legislature": legislature,
     "sessionType": sessionType, "filed": firstActionDate as YYYY-MM-DD}.
     For each id in "summary_check", call list-bill-comments and record under
     "summaries"[id] true when any comment has accessLevel "Portal", else false.

  3. Build:  python3 tools/build_bills.py build pull.json   (writes bills.json)
     Then run tools/validate.py --previous-count <old count> before committing.

Exit code 3 from either command means there are no 90th session bills yet: leave the
preview bills.json in place and stop.
"""
import json
import sys
from datetime import date
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


def plan(pull):
    cur, prev = merge_tracks(pull), previous()
    if not cur:
        print(json.dumps({"bill_count": 0, "note": "No 90th session bills yet. Leave bills.json as is."}))
        sys.exit(3)
    lookup, summary_check = [], []
    for bid, b in cur.items():
        p = prev.get(bid)
        if (not p or p.get("l") != b["lastActionDate"] or p.get("la") != b["lastAction"]):
            lookup.append(int(bid))
        if not (p and p.get("sm")):
            summary_check.append(int(bid))
    print(json.dumps({"bill_count": len(cur), "lookup": lookup, "summary_check": summary_check}))


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
    if len(sys.argv) != 3 or sys.argv[1] not in ("plan", "build"):
        sys.exit(__doc__)
    pull = json.loads(Path(sys.argv[2]).read_text())
    {"plan": plan, "build": build}[sys.argv[1]](pull)
