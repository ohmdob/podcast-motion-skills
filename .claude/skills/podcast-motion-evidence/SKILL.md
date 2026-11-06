---
name: podcast-motion-evidence
description: The Evidence Board look for a podcast or talk-show film - the speakers in front of a cork wall, every card pinned up as a polaroid with its rows on sticky notes, and each finished card shrinking onto the ledge, joined to the last by red string, so the board fills up as the case is made. Investigative and tactile, in 16:9. Works with footage or a script with drawn hosts, given a cutout of the speakers. Use when the producer picks Evidence Board, or for a mystery, true story, explainer or anything argued step by step. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "evidence board", "บอร์ดสืบสวน", "กระดานหลักฐาน", "สืบสวน", "polaroid", "detective board".
model: claude-opus-5-5
---

# Podcast Motion: Evidence Board

**Status: one scripted film rendered, not yet approved by a producer.** The Hail Mary showcase (2 minutes, two drawn hosts, Thai, 16:9) was built and rendered in it, and passed the master's QC. It hasn't been run on real footage or approved, so show test frames and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** the speakers in front of a cork wall. A card drops in as a pinned polaroid (an index card when it has no picture), its rows slap on as sticky notes on their words, and when the card is done it shrinks onto the wooden ledge, tied to the one before by red string. By the end the ledge holds the whole case.
- **Best for:** stories argued step by step: a mystery, a history, a myth-bust, an explainer with many parts.
- **Costs:** the pictures, if any. Everything else is free.

**It needs the cutout.** This look paints its own ground behind the speakers, so it needs `build/cutout.webm`: `rvm_matte.py`, then `make_cutout.py` (see `podcast-motion-pop-studio`), about 70 minutes of free machine time for a 30-minute recording. For drawn hosts, make the matte from their own alpha instead: the person matte, trained on real people, once lost a drawn host's whole head. The cold open keeps the room, because it has no cutout of its own.

## Build

```bash
python3 scripts/build.py episodes/EPxx/clips/Cnn_name --frames
python3 scripts/build.py episodes/EPxx/full --frames
```

`scripts/` is this skill's folder. The film's folder needs `full_edit.py --render` done first. Cards come from `cards.json` as in every look, and `opts.times` puts each row on its word. Pictures are found as in `podcast-motion-animatic` (`assets_src/panels/`, `a_<name>.png`), fitted to their subject and balanced to white by `card_stage.py` in `podcast-playbook`. It writes `variant_evidence/`. 16:9 only. Render and master as in `podcast-playbook`.

## Theme

```json
"looks": {"evidence": {"cork": "#B9875A", "note": "#FFE36E", "note2": "#FFB5C2", "string": "#C1121F"}}
```

Any key overrides the default.

## Notes

- **The ledge holds about 14 cards** in 16:9 before it runs out of room. A longer chapter should be split.
- **One long row of Thai has no space to break at,** so a card with one row gets a wider note. Write rows with spaces where a break can go.
- **No real people in pictures, no text in an image.** The same rules as every look: faces stay natural, and type stays live.
