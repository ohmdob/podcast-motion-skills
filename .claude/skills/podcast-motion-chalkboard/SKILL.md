---
name: podcast-motion-chalkboard
description: The Chalkboard look for a podcast or talk-show film - the speaker stays on screen with a green board beside them, a heading in chalk, rows that land on their words, and pictures turned to chalk-white sketches that move with the story. A classroom, teaching feel, built on the Animatic's card engine, in 16:9. Works with footage, from audio alone, or from a script with drawn hosts. Use when the producer picks Chalkboard, or wants an explainer or lesson feel with image-and-caption cards. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "chalkboard", "กระดานดำ", "ชอล์ก", "แบบห้องเรียน", "chalk".
model: claude-opus-5-5
---

# Podcast Motion: Chalkboard

**Status: test frames on one scripted film, not yet approved by a producer.** It was built on the Hail Mary showcase (2 minutes, two drawn hosts, Thai, 16:9). It hasn't been run on real footage or approved, so show test frames and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** the Animatic's card beside the speaker, drawn in chalk on a plain green board: every sketch inverted to chalk-white, with a yellow chalk accent.
- **Best for:** someone teaching or explaining, and topics with a classroom feel.
- **Costs:** the pictures, if any. Sketching is local and free.

## Build

```bash
python3 scripts/build.py episodes/EPxx/clips/Cnn_name --frames
python3 scripts/build.py episodes/EPxx/full --frames
```

`scripts/` is this skill's folder. It runs the Animatic's engine (`podcast-motion-animatic/scripts`), so keep the folders side by side. Cards, `opts.motion`, `"wide"` and your own `moves.py` all work exactly as in `podcast-motion-animatic`: read its "Cards, motion and theme". It writes `variant_chalkboard/`. 16:9 only, like the card layout. Render and master as in `podcast-playbook`.

## Theme

```json
"looks": {"chalkboard": {"paper": "#24382E", "ink": "#F1F3EC", "pencil": "#BFCBBB", "accent": "#F2D16B"}}
```

Any key overrides the default. A black board (`"paper": "#1E2124"`) suits a darker story. `"grid": true` brings the blueprint grid back.

## Pictures

- **Anything sketches to chalk:** photographs, stills, drawings. Pale on pale goes to nothing, so prefer a clear subject on a plain ground.
- **A picture in raw/ keeps its colour** (`assets_src/panels/raw/`), so a colourful nebula stays colourful on the board. Leave raw pictures out if you want all chalk.
- **No real people, no text in the image.** The same rules as every look: faces stay natural, and type stays live.
