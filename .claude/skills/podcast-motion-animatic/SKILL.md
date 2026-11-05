---
name: podcast-motion-animatic
description: The Animatic look for a podcast or talk-show film - storyboard panels held on screen and moved in stepped, hand-made motion, cut to the real voice, with pencil-sketched pictures and lettered words in loose frames, and the real speaker between panels. Works with footage or from audio alone, in 16:9 and 9:16. Use when the producer picks Animatic, wants an animated or illustrated feel for a talk, or has an audio-only podcast with no camera to turn into video. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "animatic", "animatic podcast", "สตอรี่บอร์ด", "ภาพสเก็ตช์", "พอดแคสต์เสียงอย่างเดียว", "audio-only podcast video".
model: claude-opus-5-5
---

# Podcast Motion: Animatic

**Status: a candidate, test frames only.** It has been built and read on real frames from one real episode, and from a test recording with no camera. It has not had a full-length render or a producer's approval. So: show the test frames and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** a storyboard brought to life. Each point in the talk is a panel, held and moved in stepped motion, under the real voice.
- **Best for:** talks about things you can draw, and audio-only shows.
- **Extra step:** none, and no matte.
- **Costs:** the pictures, unless the show already has them. It reuses any stills it finds.

## Faces stay natural

**Panels draw ideas and objects, never the people talking.** An illustrated guest is the one thing this look must not do: the guest's credibility is the point of the show, and a stylised face has already been rejected on sight on a real show. So **never give it a picture of a person,** and don't ask a generator to draw one. Between panels you see the real speaker, in natural colour.

## Build

```bash
python3 scripts/build.py episodes/EPxx/full --ratio both --frames
python3 scripts/build.py episodes/EPxx/clips/Cnn_name --ratio both --frames
```

`scripts/` is this skill's folder. The film's folder needs `full_edit.py --render` done first, with `faces.jsonl` and `pass1.json` in `build/` (`references/full-episode.md` in `podcast-playbook`). `--frames` writes a contact sheet of real frames to judge. It writes `variant_animatic/` and `variant_animatic_9x16/`. Render and master as in `podcast-playbook`.

## Panels

Every card in `cards.json` is a panel.

- **A card with a picture** (`opts.panel`, else `opts.still` or `opts.obj`): the picture as a pencil sketch, with the card's title under it and each row replacing the last as it lands.
- **A card with none:** its words, lettered in the frame.

It looks for `assets_src/panels/<name>`, then Studio Cut's stills, then Pop Studio's objects, as `.png` or `.jpg`. A named picture it can't find goes on as words, and the build reports it.

**Sketching is local and free, and it's what makes this cheap:** any photograph, or a picture from any tool, comes out in the same hand, so mixed sources still look like one storyboard. If your pictures are already drawn the way you want, set `"sketch": false`.

**Getting pictures** follows `references/storyboard-and-assets.md`: quote first, and with no Ideogram, ask the producer which alternative to use. One picture serves several cards, so a 20-minute episode can run on about 20 panels. Keep to one clear object, because a busy photograph sketches into noise:

```
Studio photograph of one single plain white cup, centred, on a plain pale background, soft even light, strong clear outline. No text, no letters, no logos, no people, no hands.
```

Save as `assets_src/panels/cup.png`, and write `{"panel": "cup"}` on the card.

**What makes it read as drawn:** the moves run at six steps a second (`steps()`), and cuts are hard. Smooth motion turns it into a slideshow, so leave that alone.

## No camera

For a show with audio only, make a plain video from the recording, and the whole pipeline runs as usual:

```bash
ffmpeg -f lavfi -i "color=c=0xF6F7F5:s=1920x1080:r=25" -i EPxx.wav -shortest -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac 1080p/EPxx.mp4
```

Then set `"audio_only": true` in `paper.json`. Between panels the frame holds the chapter's name. `faces.swift` finds no faces, which is fine. Speakers come only from the transcript, so correct `who` in `pass1.json`. **Keep a panel every few seconds:** with nothing else moving, a long gap is a frozen picture, and it fails the master's check at 12 s.

## What's on screen

- **16:9:** the speaker fills the frame between panels; a panel is a loose pencil frame on plain paper, with one line of caption below it.
- **9:16:** the frame sits at y 170 to 1070, with the caption below it inside the app's clear area, and the show's mark below that. The chapter's name takes the caption's place between panels.
- **Numbers and verdicts** are in red. There is no flood: a red word in a pencil frame is already the loudest thing on screen.
- **Paper is a cool off-white,** on purpose: cream paper with serifs is the look every show should avoid.

```json
"looks": {"animatic": {"paper": "#F6F7F5", "ink": "#1C2126", "pencil": "#59626A", "accent": "#D3261F", "sketch": true}}
```

Handwriting is Itim, which holds Thai and Latin.

## What to check

- **Read each caption and lettered panel at phone size.**
- **Does the sketch read as the thing it's meant to be?** Look at each one. A picture that doesn't, on a health or legal point especially, is worse than words: letter it instead.
- **A panel covers the speaker completely,** so don't put one over the moment their face is doing the work.
- **The same picture repeating** is fine for a few cards, and gets tired past that.
- **Fine on purpose:** `timeline_track_too_dense`, because a chapter holds many timed panels.
