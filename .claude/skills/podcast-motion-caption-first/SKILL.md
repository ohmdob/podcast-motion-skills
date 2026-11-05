---
name: podcast-motion-caption-first
description: The Caption-First look for a podcast or talk-show film - clean footage, large burned-in captions and one big moment for the number. The cheapest look to build and the strongest for clips, with no pictures and no cutout, in 16:9 and 9:16. Use when the producer picks Caption-First, wants a fast or low-cost treatment, or wants a Short or social clip that works with the sound off. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "caption first", "ซับใหญ่", "คลิปสั้นแบบซับล้วน", "big captions".
model: claude-opus-5-5
---

# Podcast Motion: Caption-First

**Status: a candidate, test frames only.** It has been built and read on real frames from one real episode, and has not had a full render or a producer's approval. So: show the test frames and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** clean footage and large captions only, plus one big moment per chapter for a number or a verdict.
- **Best for:** clips, and viewers with the sound off.
- **Costs:** nothing beyond the voice and transcript. No pictures, no matte.

## Build

```bash
python3 scripts/build.py episodes/EPxx/clips/Cnn_name --ratio both --frames      # a clip, using its captions.json
python3 scripts/build.py episodes/EPxx/full --ratio both --captions outputs/EPxx_full.th.srt --frames
```

`scripts/` is this skill's folder. The film's folder needs `full_edit.py --render` done first, with `faces.jsonl` and `pass1.json` in `build/` (`references/full-episode.md` in `podcast-playbook`), and an episode's `.srt` comes from `build_full.py FOLDER --plan` then `make_srt.py`. `--frames` writes a contact sheet of real frames to judge. It writes `variant_caption_first/` and `variant_caption_first_9x16/`. Render and master as in `podcast-playbook`.

## The one rule that changes the workflow

**Captions carry everything, so a proofread by a speaker of the language comes before the render, not after.** Burned-in errors can't be fixed after upload, and machine transcripts make serious mistakes. The build prints a DRAFT warning until `"captions_proofed": true` is in `paper.json`. Set it only when a person has read them while listening: never on your own judgement.

That makes this look a natural fit for a clip, with 20 to 30 lines to proofread. A whole episode has about 480, so for an episode, say what that proofread will take before choosing this look, and offer Studio Cut with a separate `.srt` as the alternative.

For a clip, write `captions.json` by hand: 3 to 5 words a group, fillers removed, numbers as digits, one highlighted phrase (`hi`) at most. Machine subtitles from `make_srt.py` are long and read worse, and they carry no highlight.

## What's on screen

- **16:9:** footage fills the frame, recut as two cameras. Captions sit on a white plate cut to each line, at the bottom.
- **9:16:** a footage band at the top (y 0 to 1000), recomposed so the other person stays out of shot; captions below it inside the app's clear area, up to y 1330; a desk below that with the chapter's name.
- **The big moment:** a `stat` or `verdict` card floods the frame in the accent colour for up to 3 s while the voice carries on and captions stay up. One per chapter, because a myth-bust with a number still deserves its one big visual moment, and more than that stops being a moment. Every other card kind is left out on purpose.
- **Frame 0:** the cold open's hook is on screen from the first frame. In a clip, a `q` card starting in the first second becomes the headline.

```json
"looks": {"caption-first": {"ink": "#111417", "paper": "#FFFFFF", "accent": "#FFD21F", "accent_ink": "#111417"}}
```

Those are the defaults. A show's own accent is the easiest way to make this look its own.

## What to check

- **Read the captions at phone size.** Three-line captions at 9:16 fill their zone; a long line wants splitting at the source.
- **Line breaks:** the browser breaks Thai at dictionary word boundaries and balances the lines. Read them anyway.
- **The plate covers the speaker's hands and chest,** and sometimes a gesture that matters. If it hides something, cut the shot differently.
- **Backchannels:** a filler left in a caption reads far worse than one heard. Filter them when you proofread.
- **Fine on purpose:** `composition_file_too_large` for a whole episode's captions, because the one host holds them all.
