---
name: podcast-motion-photo-card
description: The Photo Card look for a podcast or talk-show film - the speaker stays on screen with a clean white card beside them, a heading, rows that land on their words, and a picture in full colour that moves with the story. An editorial explainer feel, built on the Animatic's card engine, in 16:9. Works with footage, from audio alone, or from a script with drawn hosts. Use when the producer picks Photo Card, or wants image-and-caption cards with real colour pictures rather than sketches. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "photo card", "การ์ดภาพสี", "การ์ดรูปพร้อมคำอธิบาย", "image card with caption".
model: claude-opus-5-5
---

# Podcast Motion: Photo Card

**Status: one scripted film rendered, not yet approved by a producer.** The Hail Mary showcase (2 minutes, two drawn hosts, Thai, 16:9) was built and rendered in it, and passed the master's QC. It hasn't been run on real footage or approved, so show test frames and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** the Animatic's card beside the speaker, with each picture kept in its own colour as a framed photograph instead of a pencil sketch.
- **Best for:** explainers where the object itself matters: a product, a place, a dish, a document.
- **Costs:** the pictures. Everything else is free.

## Build

```bash
python3 scripts/build.py episodes/EPxx/clips/Cnn_name --frames
python3 scripts/build.py episodes/EPxx/full --frames
```

`scripts/` is this skill's folder. It runs the Animatic's engine (`podcast-motion-animatic/scripts`), so keep the folders side by side. Cards, `opts.motion`, `"wide"` and your own `moves.py` all work exactly as in `podcast-motion-animatic`: read its "Cards, motion and theme". It writes `variant_photo_card/`. 16:9 only, like the card layout. Render and master as in `podcast-playbook`.

## Theme

```json
"looks": {"photo-card": {"paper": "#FFFFFF", "ink": "#15181C", "pencil": "#5B6470", "accent": "#E8452C"}}
```

Any key overrides the default. `"colour": true` and `"sketch": false` are what make it this look, so leave them.

## Pictures

- **Studio photographs on a plain pale ground work best.** Each picture is balanced against its own border, so a pale grey studio ground comes out pure white and sits on the card with no box. A busy photograph keeps its ground and shows as a framed photo.
- **Line drawings mix in cleanly.** Pictures are laid over with multiply, so a drawn Rocky hanging from a photographed marionette bar shows both.
- **No real people, no text in the image.** The same rules as every look: faces stay natural, and type stays live.
