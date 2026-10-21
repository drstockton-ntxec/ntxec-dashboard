# NTXEC Session Dashboard

One education bill dashboard for the 90th Texas Legislature, shared by NTXEC and its member districts. Every district sees the same bill data. Only the name, logo and colors change.

## Files

| File | What it is |
| --- | --- |
| `index.html` | The dashboard. Reads the two files below and picks branding from `?d=` in its link. |
| `bills.json` | The shared snapshot of every bill NTXEC tracks in USLege, with status and NTXEC impact designations. |
| `districts.json` | One entry per district: name, logo, colors. `ntxec` is the default. |
| `embed.js` | Optional helper that sizes the iframe to fit the dashboard. |
| `embed-test.html` | A stand-in district page for testing the embed. |
| `tools/validate.py` | Checks the data and district colors. Run before every publish. |

## Links

| District | Link |
| --- | --- |
| NTXEC | `https://dashboard.ntxec.org/?d=ntxec` |
| Mesquite ISD | `https://dashboard.ntxec.org/?d=mesquite` |
| Plano ISD | `https://dashboard.ntxec.org/?d=plano` |
| Denton ISD | `https://dashboard.ntxec.org/?d=denton` |
| Dallas ISD | `https://dashboard.ntxec.org/?d=dallas` |
| Richardson ISD | `https://dashboard.ntxec.org/?d=richardson` |

## Embed code for a district

Replace `mesquite` with the district's code.

```html
<iframe src="https://dashboard.ntxec.org/?d=mesquite"
        title="90th Legislative Session education bill dashboard"
        style="width:100%;border:0;min-height:900px"
        loading="lazy" data-ntxec-dashboard></iframe>
<script src="https://dashboard.ntxec.org/embed.js" async></script>
```

If the district's website does not allow scripts, the iframe line alone still works. The dashboard then scrolls inside its frame.

## Adding a district

1. Add the district's official logo file under `logos/` (resized proportionally, otherwise unaltered).
2. Add an entry to `districts.json`. Settings:
   - `colors.primary`: bars, links and rules. `colors.dark`: title, the "At a glance" band, table header, and High impact. `colors.highlight`: the "Education Bills" accent. `colors.label`: the small label on the dark band. `colors.medium` (optional): Medium impact, when primary is too close to dark.
   - `fonts.display` and `fonts.body` (optional): Google Fonts family names; `fonts.displayWeights` lists the heading weights to load.
   - `logoHeight` (optional, pixels) and `showName: false` when the logo already spells out the district name.
3. Run `python3 tools/validate.py`. It fails if a color is too light to read, or if High and Medium impact would look alike.

## Refreshing the data

The data comes from the twelve "(90)" Issue tracks in NTXEC's USLege account, one per policy area, and the public "90th Legislative Session Education Bills" portal. A bill shows **Read summary** when NTXEC has posted a portal comment on it. `tools/build_bills.py` explains the three steps (track pass, lookups, build) and carries forward anything that has not changed. After building, run `python3 tools/validate.py --previous-count <old bill count>` and commit only if it passes. Every district page updates within a few minutes of the commit.

Until prefiling opens November 9, 2026, the 90th tracks are empty and the builder leaves the 89th session preview in place.
