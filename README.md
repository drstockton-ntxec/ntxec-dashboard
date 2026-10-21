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

- NTXEC: `https://dashboard.ntxec.org/?d=ntxec`
- Mesquite ISD: `https://dashboard.ntxec.org/?d=mesquite`

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

1. Add the logo file under `logos/` (the district's official file, unaltered).
2. Add an entry to `districts.json` with the district's official colors.
3. Run `python3 tools/validate.py`. It fails if a color is too light to read on white.

## Refreshing the data

Replace `bills.json` with a new pull from USLege, run `python3 tools/validate.py --previous-count <old bill count>`, and commit. Every district page updates within a few minutes. Set `"preview": false` when live 90th session data begins.
