#!/usr/bin/env python3
"""Check bills.json and districts.json before publishing.

Run: python3 tools/validate.py [--previous-count N]
Exits non-zero (and publishes nothing) when a check fails, so a bad USLege pull
or an unreadable district color never reaches district websites.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AREAS = {
    "School Finance", "Property Taxes", "Bonds, Elections & Debt", "Governance & Local Control",
    "Accountability & Assessment", "Curriculum & Instruction", "Educator Workforce",
    "Special Populations", "Student Health & Discipline", "School Safety",
    "School Choice & Charters", "Operations & Business",
}
STAGES = {"introduced", "first_committee", "first_floor", "second_committee", "second_floor", "governor", "became_law"}
IMPACTS = {"", "High", "Medium", "Low"}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def luminance(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def main():
    errors = []
    prev = None
    if "--previous-count" in sys.argv:
        prev = int(sys.argv[sys.argv.index("--previous-count") + 1])

    data = json.loads((ROOT / "bills.json").read_text())
    bills = data.get("bills", [])
    if not DATE.match(str(data.get("updated", ""))):
        errors.append("bills.json: 'updated' must be YYYY-MM-DD")
    if not isinstance(data.get("preview"), bool):
        errors.append("bills.json: 'preview' must be true or false")
    if not bills:
        errors.append("bills.json: no bills")
    if prev and len(bills) < 0.8 * prev:
        errors.append(f"bills.json: bill count fell from {prev} to {len(bills)} (more than 20%)")
    seen = set()
    for n, b in enumerate(bills):
        tag = b.get("b", f"row {n}")
        key = (b.get("b"), b.get("s"))
        if key in seen:
            errors.append(f"{tag}: duplicate bill")
        seen.add(key)
        if not re.match(r"^(HB|SB|HJR|SJR|HCR|SCR|HR|SR) \d+$", str(b.get("b", ""))):
            errors.append(f"{tag}: bill number format")
        if not b.get("c"):
            errors.append(f"{tag}: missing caption")
        if not b.get("a") or not set(b["a"]) <= AREAS:
            errors.append(f"{tag}: policy areas missing or unknown: {b.get('a')}")
        if b.get("i", "") not in IMPACTS:
            errors.append(f"{tag}: unknown impact {b.get('i')!r}")
        if b.get("st") not in STAGES:
            errors.append(f"{tag}: unknown stage {b.get('st')!r}")
        for f in ("f", "l"):
            if not DATE.match(str(b.get(f, ""))):
                errors.append(f"{tag}: bad date in '{f}'")
        if not isinstance(b.get("sm"), bool):
            errors.append(f"{tag}: 'sm' must be true or false")

    districts = json.loads((ROOT / "districts.json").read_text())
    if "ntxec" not in districts:
        errors.append("districts.json: the 'ntxec' entry is required (it is the default)")
    for code, d in districts.items():
        if not re.match(r"^[a-z0-9-]+$", code):
            errors.append(f"districts.json: code '{code}' must be lowercase letters, digits or hyphens")
        c = d.get("colors", {})
        for k in ("primary", "dark", "highlight", "label"):
            if not HEX.match(str(c.get(k, ""))):
                errors.append(f"{code}: color '{k}' must be a #RRGGBB value")
        if errors:
            continue
        # primary and dark carry body-size text and links on white: 4.5:1
        for k in ("primary", "dark"):
            r = contrast(c[k], "#FFFFFF")
            if r < 4.5:
                errors.append(f"{code}: '{k}' {c[k]} has {r:.2f}:1 contrast on white (needs 4.5)")
        # highlight is used for the large headline text: 3:1
        r = contrast(c["highlight"], "#FFFFFF")
        if r < 3:
            errors.append(f"{code}: 'highlight' {c['highlight']} has {r:.2f}:1 contrast on white (needs 3)")
        # label is small text on the dark band: 4.5:1
        r = contrast(c["label"], c["dark"])
        if r < 4.5:
            errors.append(f"{code}: 'label' {c['label']} has {r:.2f}:1 contrast on 'dark' (needs 4.5)")
        for k, val in (d.get("fonts") or {}).items():
            if k in ("display", "body") and not re.match(r"^[A-Za-z0-9 ]+$", str(val)):
                errors.append(f"{code}: font '{k}' must be a Google Fonts family name")
        logo = d.get("logo")
        if logo and not (ROOT / logo).exists():
            errors.append(f"{code}: logo file {logo} not found")

    if errors:
        print("FAILED")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print(f"OK: {len(bills)} bills, updated {data['updated']}, {len(districts)} district entries")


if __name__ == "__main__":
    main()
