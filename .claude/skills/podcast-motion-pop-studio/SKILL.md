---
name: podcast-motion-pop-studio
description: The Pop Studio look for a podcast or talk-show film - a painted TV set, with the speakers cut out of the frame in natural colour on flat colour fields, an arch behind each, huge type behind them, and real objects popping in. Friendly and lively, with the ground changing by chapter, in 16:9 and recomposed for 9:16. Use when the producer picks Pop Studio or wants a colourful, stop-the-scroll treatment for an episode, a Short or a clip. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "pop studio", "คนตัดพื้นหลังบนสีสด", "แบบสนุก ๆ สีสด".
model: claude-opus-5-5
---

# Podcast Motion: Pop Studio

**Status: built on a real full episode (16:9 and 9:16) and a clip, and approved by a producer.** Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master. This skill is only the look. `$S` is `podcast-playbook/scripts`, a sibling of this skill's folder.

- **Idea:** a painted TV set. Speakers are cut out in natural colour and stand on flat fields, with a painted arch or disc behind each that springs up on every cut.
- **Feels:** friendly and lively. The ground changes by chapter, which keeps a long film from feeling like one frame.
- **Colour:** tomato `#FF5A36`, mango `#FFC21A`, mint `#0FB98E`, sky `#1F6FE5`, pink `#FF9EC4`. Type: Mitr 600 to 700.
- **Extra step:** a matte, about 70 minutes of free machine time in all.
- **Costs:** objects, if you want them. Each is a generated or real photograph, cut out.

## Build

```bash
F=episodes/EPxx/full
uv run $S/rvm_matte.py 1080p/EPxx.mp4 episodes/EPxx/matte       # once per recording, on the UNCUT file. About 55 min for 30 min; re-run to resume
python3 $S/matte_qc.py episodes/EPxx/matte $F                   # see-through check through the edit, about 2 min
python3 $S/make_cutout.py episodes/EPxx/matte $F                # the speakers alone: about 15 min for 22 min of film
python3 $S/build_full.py $F b --frames                          # writes variant_b/, with a contact sheet of real frames
python3 $S/build_full.py $F v --frames                          # 9:16, after b: writes variant_b_9x16/
```

A clip takes the same commands with its own folder in place of `$F`. Master 9:16 with `--size 1080x1920`. The same mix and subtitles serve both.

## The matte, because it is the riskiest part

- **Run it on the whole uncut recording, through `uv`, before cutting.** Robust Video Matting has memory, so straight after a jump cut it would go see-through for about a second. `uv` pins onnxruntime: one later version leaked 41 MB a frame, filled the RAM and about 80 GB of swap, and took the machine down.
- **The model** (Peter Lin's RobustVideoMatting, GPL-3.0, 15 MB) downloads on first use, checked against a pinned hash. Keep `episodes/EPxx/matte/` (about 1.8 GB): a new cut of the same recording only needs a new cutout.
- **Check it.** `matte_qc.py` compares every frame with the 4 seconds around it and finds bodies dropping out. A moving arm or camera trips it too, so look at the worst of what it flags, on a loud colour: `ffmpeg -c:v libvpx-vp9 -ss SECONDS -i $F/build/cutout.webm -filter_complex "color=magenta:s=1920x1080[b];[b][0:v]overlay=shortest=1" -frames:v 1 frame.jpg`. It says nothing about wall left behind: read frames from the final file as well.
- **What it leaves:** scraps of furniture around the laps, so frame the bottom of the source (about y = 930 on one set) off the frame. Also some wall: a strip behind hair, thin light lines on edges, ghosted fast hands. Nobody knows how often without watching. Don't count on-screen pixels to measure it: that count failed on a known bad frame.
- **Measure memory before an hour-long job:** run about 100 frames and read `vmmap --summary PID`.

## Rules that came from real mistakes

- **Don't stylise faces.** A halftone version was rejected on sight. The guest's credibility is the point.
- **Layers, bottom to top:** ground → arches → verdict flood → headings → the cutout → rows → curtain. Type behind the person means a gesture passes in front of a heading. Rows stay on top so they can always be read.
- **Keeping one speaker:** a shot clips the other person with a vertical line proved empty for the whole shot (`free_split`, from the `.occ.npy` beside the cutout). A fixed midline cuts through a gesturing hand. A shot with no empty line and no card becomes a two-shot.
- **Cuts are hard, and the shapes move.** The camera jumps and the shape behind springs up. Gliding the camera on every cut made a talk feel seasick. Shapes rotate through arch, disc and double arch.
- **Never leave half the frame empty.** With no card, the speaker holds the middle and the chapter's name drifts behind them, huge and tone on tone. It leaves when a card arrives.
- **A chapter ends with a curtain:** an arch in the next chapter's colour rises over the frame, and the chapter card starts on that same colour.
- **Measure type with the real font** (`pop.fit`), because `check` doesn't flag a nowrap title running off the frame.
- **An element with one entrance keeps GSAP's default `immediateRender`.** With it off, it shows at rest until its tween starts, then jumps.
- **Type behind a head lands on the face first if the person is turned that way.** Stop the word short of it, and check at every scale: a tight shot once put an object against a nose.

## At 9:16

Recomposed, not cropped.
- **The app covers the frame:** words and products stay between y 168 and 1330. Below that goes only decoration.
- **Leave air around people.** 1.72× felt cramped; it ended at 1.38× normally, 1.48× for a punch-in, 0.96× in a two-shot.
- **Words above, face below:** the face sits at about y = 960.
- **A desk across the bottom of every shot,** with the chapter's name, so a viewer landing anywhere knows the topic. It also hides where the cutout ends.
- **The two-shot gets two cameras,** so the speakers stand closer than they sat.
- **Cut more often:** about every 2.5 s against 3.7 s, each with a new shape.
- **No burned-in captions on a whole episode:** machine subtitles can't be corrected once burned in. A clip's few lines can be proofread first.

## Objects and colour

`assets_src/pop/<name>.png` is a cutout object, and `opts.obj` on a card picks one. Text is live; objects carry no words. In `paper.json`: `title_objects`, `aliases`, and `windows` for a picture with no single subject. To recolour a palette by name, keep each ground's ink readable, and judge it on real frames:

```json
"looks": {"pop-studio": {"palettes": {"tomato": {"g": "#E84A2E"}}}}
```

`check` assumes a `<video>` is opaque and reports `text_occluded`: the cutout carries `data-layout-allow-occlusion`, so judge by snapshot. It can also report `text_occluded` as an error on a selector ending in `gt`, which is the chapter's name drifting behind the painted shapes. That one is on purpose, and fails `check` on some clips: look at the frame, and if that is all it is, carry on.
