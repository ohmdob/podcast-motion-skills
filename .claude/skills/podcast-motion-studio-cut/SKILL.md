---
name: podcast-motion-studio-cut
description: The Studio Cut look for a podcast or talk-show film - real graded footage recut from one camera into two, with typographic label cards and bright stills, quiet and trustworthy, for viewers who only want the content. Use when the producer picks Studio Cut, or wants a calm, credible, information-first treatment with the real room kept, for an episode or a clip, 16:9. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "studio cut", "แบบเรียบ ๆ น่าเชื่อถือ", "คงฉากจริงไว้".
model: claude-opus-5-5
---

# Podcast Motion: Studio Cut

**Status: built on a real full episode and a clip, and approved by a producer.** Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master. This skill is only the look. `$S` is `podcast-playbook/scripts`, a sibling of this skill's folder.

- **Idea:** real footage, cut as two cameras, with cards built like a label: heavy rules, a big bold term, rows.
- **Feels:** quiet and trustworthy.
- **Extra step:** none, and no matte.
- **Costs:** stills, if you want them. It builds without any.
- **Not built:** 9:16. Use Caption-First, Whiteboard, Morning Show or Pop Studio for a phone cut, or design it on real frames first.

## Build

The folder has been through `full_edit.py --render`, with `faces.jsonl` and `pass1.json` in `build/`. `--frames` adds a contact sheet of real frames, the quick way to judge the look.

```bash
python3 $S/build_full.py episodes/EPxx/full a --plan     # shots and cards, nothing built
python3 $S/build_full.py episodes/EPxx/full a --frames   # writes variant_a/
python3 $S/build_full.py episodes/EPxx/clips/Cnn_name a  # a clip, the same way
```

Then the review, render and master in `podcast-playbook` (`references/review-and-delivery.md`).

## Make it this show's

The label is a language, not a colour scheme: heavy rules and rows read as something official from the world the show is about. **Take the equivalent from this show's own world** (a receipt, a spec sheet, a court docket), and try it on real frames first.

```json
"looks": {"studio-cut": {"ink": "#10201F", "label": "#F4F7F5", "mark": "#E6E12E", "accent": "#0B7A76"}}
```

Those are the defaults. Type is Noto Sans Thai with HyperFrames' bundled Inter for Latin, 600 to 900.

## Rules that came from real mistakes

- **A card grows row by row** as the words arrive. Revealing a tall card with empty rows reads as a blank white box.
- **Bright stills that match the set.** Dark, moody stills looked like stock against bright footage, and a review flagged it. Stills are mirrored when the card sits on the subject's side. See `references/storyboard-and-assets.md` for the prompts: name them `assets_src/a_<name>.png`, and `opts.still` on a card picks one.
- **Grade through HyperFrames, never CSS filters.** Contrast .07, saturation .08, temperature .03, vignette .1, set as `data-color-grading`.
- **Frame so the other person is fully out of shot.** The planner computes it from the faces. A half-cut face looks like a mistake.
- **Words on the side away from the person.** Check that the head really is where you think: someone who moves between sections will run behind a fixed position.
- **End card:** summary on the left, the right side free for the platform's end-screen elements.
- **An illustration says so on screen,** if you hand-build one. A drawing can misrepresent a guest even when every number on it is right: an independent review caught exactly that on one clip.

Warnings that are fine on purpose: `timeline_track_too_dense` when a chapter holds many timed cards, and `duplicate_media_discovery_risk` when a card repeats a still.
