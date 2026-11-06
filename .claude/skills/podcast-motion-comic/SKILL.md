---
name: podcast-motion-comic
description: The Comic look for a podcast or talk-show film - the speakers inked onto a halftone page that changes colour with every card, speed lines behind them, and comic panels that slam in with a caption box, the picture and a speech bubble pointing back at the speaker. A stat gets a starburst and a shake. Loud and playful, in 16:9. Works with footage or a script with drawn hosts, given a cutout of the speakers. Use when the producer picks Comic, or wants a pop, comic-book or manga feel. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "comic", "การ์ตูน", "คอมมิค", "มังงะ", "comic book", "manga".
model: claude-opus-5-5
---

# Podcast Motion: Comic

**Status: test frames on one scripted film, not yet approved by a producer.** It was built on the Hail Mary showcase (2 minutes, two drawn hosts, Thai, 16:9). It hasn't been run on real footage or approved, so show test frames and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** the speakers keep their own picture with an ink outline, on a halftone page whose colour changes with each card. Each card is a comic panel: a caption box with the heading, the picture, and the rows in a speech bubble whose tail points back at the speaker. A stat or a verdict gets a starburst and a shake; the covers are starbursts too.
- **Best for:** loud, playful topics, and Shorts that have to stop the scroll.
- **Costs:** the pictures, if any. Everything else is free.

**It needs the cutout.** This look paints its own ground behind the speakers, so it needs `build/cutout.webm`: `rvm_matte.py`, then `make_cutout.py` (see `podcast-motion-pop-studio`), about 70 minutes of free machine time for a 30-minute recording. For drawn hosts, make the matte from their own alpha instead: the person matte, trained on real people, once lost a drawn host's whole head. The cold open keeps the room, because it has no cutout of its own.

## Build

```bash
python3 scripts/build.py episodes/EPxx/clips/Cnn_name --frames
python3 scripts/build.py episodes/EPxx/full --frames
```

`scripts/` is this skill's folder. The film's folder needs `full_edit.py --render` done first. Cards come from `cards.json` as in every look, and `opts.times` puts each row on its word. Pictures are found as in `podcast-motion-animatic` (`assets_src/panels/`, `a_<name>.png`), fitted to their subject and balanced to white by `card_stage.py` in `podcast-playbook`. It writes `variant_comic/`. 16:9 only. Render and master as in `podcast-playbook`.

## Theme

```json
"looks": {"comic": {"pages": ["#FFD23F", "#3BCEAC", "#FF7AA8", "#5AA9E6", "#FF9F45"], "caption": "#FFE45E", "accent": "#E63946"}}
```

Any key overrides the default.

## Notes

- **Faces are never stylised.** The outline goes around the speaker, never over the face: no halftone, no posterising.
- **Speed lines sit behind the speaker,** only while their card is up, so a talk with no card stays calm.
- **No real people in pictures, no text in an image.** The same rules as every look: faces stay natural, and type stays live.
