---
name: podcast-motion-animatic
description: The Animatic look for a podcast or talk-show film - storyboard panels held on screen and moved in stepped, hand-made motion, cut to the voice, with pencil-sketched pictures and lettered words in loose frames, and the speaker between panels. Optional cards beside the speaker, pictures that move with the story and a themed blueprint ground. Works with footage, from audio alone, or from a script with drawn hosts, in 16:9 and 9:16. Use when the producer picks Animatic, wants an animated or illustrated feel for a talk, or has an audio-only podcast with no camera to turn into video. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "animatic", "animatic podcast", "animatic motion", "การ์ดอธิบาย", "ภาพเคลื่อนไหวเล่าเรื่อง", "สตอรี่บอร์ด", "ภาพสเก็ตช์", "พอดแคสต์เสียงอย่างเดียว", "audio-only podcast video".
model: claude-opus-5-5
---

# Podcast Motion: Animatic

**Status: one scripted film rendered and approved by its producer: 2 minutes, two drawn hosts, cards, blueprint, 16:9.** On real footage and at 9:16 it has only been read on test frames, so show those and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** a storyboard brought to life. Each point in the talk is a panel, held and moved in stepped motion, under the real voice.
- **Best for:** talks about things you can draw, and audio-only shows.
- **Extra step:** none, and no matte.
- **Costs:** the pictures, unless the show already has them. It reuses any stills it finds.

## Faces stay natural

**Panels draw ideas and objects, never the people talking.** An illustrated guest is the one thing this look must not do: the guest's credibility is the point of the show, and a stylised face has already been rejected on sight on a real show. So **never give it a picture of a person,** and don't ask a generator to draw one. Between panels you see the real speaker, in natural colour.

**Hosts who are already characters are the one exception,** when the producer asks: the reason above is about a real person's credibility. They take the speaker's place, and panels still show only objects and words. See `references/scripted-show.md` in `podcast-playbook`.

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

## Cards, motion and theme

What one producer asked for, one request at a time, and all of it held up. Each is off until the show asks, and the code is in `scripts/animatic_cards.py`, whose top lists every option.

```json
"looks": {"animatic": {"layout": "card", "blueprint": true, "paper": "#0A1A33", "ink": "#E6F4FF", "pencil": "#9CC4E4", "accent": "#FFB547"}}
```

- **`"layout": "card"` keeps the speaker on screen.** A full-frame panel hides them, and the producer asked for image cards and explaining text like Pop Studio's. The card takes the side away from whoever is talking: heading first, rows landing on their words and staying, then a picture filling what the words leave. 16:9 only so far. Type behind the hosts, Pop Studio's other half, needs a cutout, so it isn't here.
- **`opts.motion` moves the picture with the story.** Built in: `still`, `drop`, `arc`, `fly`, `drift`, `sway`, `hop`, `swarm`, `flipbook`. A slow push-in on every panel wasn't enough for the producer; a ball being thrown tells the story as well as showing it. Write your own in `moves.py`: `examples/hail-mary/moves.py` has one line told in three drawings, and a ball from early in the film landing at the end.
- **Two looks are this card engine with a theme of their own:** `podcast-motion-photo-card` (`"colour": true`, pictures kept in full colour) and `podcast-motion-chalkboard` (`"blueprint": true, "grid": false` on a green board). Both options are off here unless the show sets them.
- **`"blueprint": true` themes it.** Take the theme from the story, and ask: a navy grid suited a space film. It inverts every sketch and lays it over with screen, so moved pictures show no edge.
- **Draw what a generator can't give you cleanly.** A flipbook of 18 drawings, a walking alien and a solid ship cost nothing, and read better than sketched photographs. `examples/hail-mary/draw_art.py` shows how. A drawing of someone else's character is still theirs, so raise it before publishing.
- **`"wide"` in `paper.json`** gives a two-shot. Hosts who trade short lines never get one from the planner, and a viewer should see both early and at the end.

## Mistakes already paid for

- **A card must land on its own framing.** The planner holds a shot for at least a second, so a card could hide half a face for 0.9 s. In card layout the shots now cut exactly on card edges and on each change of speaker.
- **A sliver of the other host at the frame edge looks like a mistake.** The card gets a solid strip out to the edge behind it.
- **Picture too small in its window:** give it what the words leave, then use `zoom`. A busy row of text over a tiny apple looked unfinished.
- **Flip a picture that flies backwards.** The ship's nose pointed the way it had come.
- **Check that what hangs meets what it hangs from.** Strings stopping short of the puppet were on screen for 10 s before a fresh reviewer said so.
- **A lettered card is the weakest one on a film with moving pictures.** Keep them for a number, and draw something for the rest.

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
- **Step through each card's arrival frame by frame.** The first second of a card is where framing and entrance faults hide, and samples every few seconds miss them.
