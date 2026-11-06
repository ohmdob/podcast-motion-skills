---
name: podcast-motion-bento
description: The Bento Grid look for a podcast or talk-show film - the footage becomes one rounded tile on a plain canvas and every card reflows the grid: the speaker's tile shrinks to their half while the other half fills with tiles for the heading, the picture and each row, landing on their words. Clean, modern and product-like, in 16:9. Works with real footage or drawn hosts, with no cutout. Use when the producer picks Bento Grid, or wants a tidy, app-like, keynote feel. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "bento", "เบนโตะ", "กริด", "แบบแอป", "bento grid", "tile layout".
model: claude-opus-5-5
---

# Podcast Motion: Bento Grid

**Status: test frames on one scripted film, not yet approved by a producer.** It was built on the Hail Mary showcase (2 minutes, two drawn hosts, Thai, 16:9). It hasn't been run on real footage or approved, so show test frames and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** no overlay at all: the footage itself is a rounded tile on a plain canvas. When a card comes, the speaker's tile shrinks to their half and the other half fills with tiles: the heading (dark for a question, blue for a term, the accent for a number), the picture, and one numbered tile per row, each landing on its word. Between cards the tile grows back to the full frame.
- **Best for:** calm, modern explainers, product talk, and anything that should feel like a keynote.
- **Costs:** the pictures, if any. Everything else is free.

## Build

```bash
python3 scripts/build.py episodes/EPxx/clips/Cnn_name --frames
python3 scripts/build.py episodes/EPxx/full --frames
```

`scripts/` is this skill's folder. The film's folder needs `full_edit.py --render` done first. Cards come from `cards.json` as in every look, and `opts.times` puts each row on its word. Pictures are found as in `podcast-motion-animatic` (`assets_src/panels/`, `a_<name>.png`), fitted to their subject and balanced to white by `card_stage.py` in `podcast-playbook`. It writes `variant_bento/`. 16:9 only. Render and master as in `podcast-playbook`.

## Theme

```json
"looks": {"bento": {"canvas": "#EFECE6", "accent": "#FF5A36", "blue": "#2E5BFF", "dark": "#1D1F24"}}
```

Any key overrides the default.

## Notes

- **No cutout and no matte:** the room stays, framed as a tile, so this is the cheapest of the four new looks.
- **A picture tile needs room.** When a heading and its rows leave less than 240 px, the picture is dropped and the heading takes the space.
- **No real people in pictures, no text in an image.** The same rules as every look: faces stay natural, and type stays live.
