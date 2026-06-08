# 60-second README clip — recording brief

Two production tracks, stitched at the end. **Veo generates new pixels — it cannot
screenshot the real UI**. So Veo handles the cinematic intro/outro (~14s), and a
plain screen recorder handles the actual product walkthrough (~46s).

When the final file is rendered, drop it at one of:

- `docs/fairguard_60s.gif` — what the README currently embeds
- `docs/fairguard_60s.mp4` — swap in by editing the `![…](docs/…)` line in `README.md`

## A. Storyboard (60 s)

| t | Source | Shot |
|---|--------|------|
| 0:00–0:08 | **Veo** | Cinematic intro — paper filings stacking into a digital lattice |
| 0:08–0:14 | Screen recording | Landing `/` — hero + headline stats |
| 0:14–0:24 | Screen recording | `/methods` — slow vertical scroll through the **Pipeline at a glance** section |
| 0:24–0:36 | Screen recording | `/findings` → click top card → `/findings/benjamin-steinberg-energy` showing the four-gate dashboard |
| 0:36–0:46 | Screen recording | Money-trail panel expanded — pause on the `$1.08B traced` headline + Cirba Solutions row |
| 0:46–0:54 | Screen recording | `/graph` — pan / zoom across one triangle pattern after the layout settles |
| 0:54–1:00 | **Veo** | Cinematic outro — quill over reporter's notes; end-card text |

## B. Veo prompts (Google Gemini video tool)

Veo 3 generates 8-second clips. Run the prompt **once for the intro**, then run the
**outro variant** once for the closing. Both prompts are designed to match the
project's color palette (indigo `#4F46E5`, emerald `#059669`, slate `#0F172A`) so
they stitch cleanly with the real-UI footage in the middle.

### Intro (run once → 0:00–0:08)

> **Cinematic establishing shot, 8 seconds, 16:9, 24fps.** Open on a slow top-down dolly across a wooden newsroom desk lit by a single warm lamp. Stacks of paper lobbying disclosures (cream paper, fine print, federal-blue letterheads with the words "QUARTERLY REPORT" subtly visible) lie scattered across the desk. A reporter's hands — out of focus, mid-frame, no face — push the stacks toward the center. As the stacks meet, the paper dissolves upward into a clean digital lattice of soft indigo and emerald data lines (the lattice is geometric, abstract, not literal UI). The camera tilts up to follow the lattice as it forms a calm grid that fills the upper third of the frame. **Mood:** investigative, deliberate, trustworthy — like a 60 Minutes cold open, not a tech ad. **Lighting:** warm tungsten foreground, cool blue background. **Color palette:** cream paper, federal navy, slate grey, indigo accents, single emerald highlight. **Camera:** slow steady dolly, no shake, no fast cuts. **Audio:** the soft rustle of paper, a single low piano note holding under, no music swell, no voiceover. **Text overlay (lower third, sans-serif, fades in at 0:05):** "FairGuard — federal lobbying, audited." **Avoid:** stock-footage cliché (no glowing CPU chips, no spinning globes, no fake hacker code), no human faces, no logos, no flashing transitions.

### Outro (run once → 0:54–1:00)

Same prompt as the intro, but replace the action line with:

> As the lattice settles, a single page of typed reporter's notes slides into the center of the frame; a fountain pen is poised over it. **Text overlay:** "139 candidates · open source · reproducible from a clean clone."

## C. Screen recordings to capture

**Setup before recording.**

- 1920×1080 (or 1440×900 retina) display, light theme, browser at 100% zoom.
- Hide browser chrome — Chrome → press `F11` for fullscreen, or open in a clean window.
- Make sure `web/public/findings.json` and `web/public/trails.json` are populated. If
  not, run `/fair-guard scan` and `/fair-guard trace` (or the underlying scripts —
  see the README) before recording.

**Recommended tools.**

- **OBS Studio** (free, every OS) — record to MP4, edit later.
- **ScreenToGif** (Windows-only, free) — record straight to GIF if you want to skip the conversion step.
- **DaVinci Resolve** (free editor) for stitching the Veo clips with the screen recordings.

**Clip list** (timings are target lengths, final cut should match the storyboard).

| # | What to record | Length | Notes |
|---|----------------|--------|-------|
| 1 | `npm run dev` running, browser at `localhost:3000` (the landing) | 6s | Capture from "Today's top three" headline downward; brief pause on the four big tiles. |
| 2 | `/methods` page, slow vertical scroll through **Pipeline at a glance** | 10s | Use mouse-wheel slowly; let each colored stage box fully enter the viewport before scrolling on. |
| 3 | `/findings`, hover on top card, click **Open full case →** | 4s | Cursor visible; click animation visible. |
| 4 | `/findings/benjamin-steinberg-energy` — show the four gate badges, scroll to gate-2 money trail | 8s | Pause ~1s on the four-gate dashboard so a viewer can read the labels. |
| 5 | Same page — expand the money-trail table; pause on `$1.08B traced` and the Cirba Solutions row | 10s | Slow cursor hover on the biggest line item. |
| 6 | `/graph`, after layout settles — pan/zoom across one triangle pattern | 10s | Use the existing drag-to-pan; don't add cursor highlight effects. |

## D. Stitching + export

Open the eight clips (1 Veo intro + 6 screen recordings + 1 Veo outro) in your
editor in the order above. Add a 0.2s fade between each. Render to MP4 first
(this is your master), then convert to GIF for the README.

### MP4 → GIF

```bash
ffmpeg -i fairguard_60s.mp4 \
  -vf "fps=15,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
  -loop 0 \
  docs/fairguard_60s.gif
```

Target: under 10 MB so GitHub renders inline. At 960px × 15fps × 60s that lands
around 6–9 MB.

### Or — keep it as MP4 in the README

GitHub READMEs render MP4 when you upload via a draft issue's attachment uploader
and paste the resulting URL. Edit `README.md` and replace the `<img>` line with:

```html
<video src="docs/fairguard_60s.mp4" controls width="100%"></video>
```

…or use the GitHub-hosted URL from the draft issue.
