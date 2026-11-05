# What things cost

Measured on a real episode unless marked. Prices change, and the tools' own quote plus `python3 $S/el.py quota` are the live numbers; every run's actual costs are in the show's `data/ledger.md`.

## ElevenLabs

| Item | Rate | Notes |
|---|---|---|
| Audio Isolation | 660 credits a minute | 19,792 for 30 minutes |
| Scribe | 20 credits a minute | 605 for 30 minutes |
| Forced Alignment | about 21 credits a minute | 15 for 43 s |
| Music | about 630 credits per 46 s bed | Taken from the balance: the API returns no cost for this call, so its ledger row shows `?` |
| Sound effects | 6 to 24 with a set duration, 55 without | Check every take for silence |

## Ideogram 4.5, through Comfy Cloud

| Quality | Comfy credits an image |
|---|---|
| very_low (edit only) | 2.41 |
| low | 9.05 |
| medium | 18.1 |
| high | 60.35 |

These were measured on Edit, through a self-run ComfyUI on the same Comfy account. Text-to-image and Comfy Cloud are **assumed** to match until an invoice says otherwise, so check the first invoice. Comfy Cloud may also need an active plan for its API.

## Codex imagegen

An alternative when Ideogram isn't available, and only after asking. It counts against the plan Codex is signed in with and reports no cost, so its ledger rows say `plan`, not a figure.

## Typical jobs

| Job | ElevenLabs | Ideogram |
|---|---|---|
| One clip, isolating only its range (60 s handle) | ≈ 700 (isolation, Scribe, alignment); add ≈ 630 per new bed and ≈ 150 for a new set of effects | ≈ 127 for 7 images |
| A 30-minute episode | ≈ 20,400 (isolation + Scribe), plus ≈ 600 for a first transcript pass on the raw voice | ≈ 400 for 22 images |
| A clip from a processed episode | 0 | Only new images |
| Caption-First, Whiteboard or Morning Show | Voice and transcript only | 0: these looks use no pictures |
| Animatic, a 20-minute episode | Voice and transcript only | ≈ 360 for about 20 panels, less if it reuses existing stills; 0 with your own pictures or lettered panels |
| The whole method with no keys | 0 | 0 |

Music and effects are reusable across episodes, so they are usually a one-time cost per show.

Rendering, the matte, cutouts, face tracking, cuts, subtitles and QC are all free and local.
