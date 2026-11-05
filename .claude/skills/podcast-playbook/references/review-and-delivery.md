# Stages H to J: review, master, publish

## H. Review and preview ★

1. **`npx hyperframes check --json`.** Fix errors, weigh warnings. Usually fine on purpose: `timeline_track_too_dense` when a chapter holds many timed cards, `duplicate_media_discovery_risk` when a card repeats an object, `line_unread` on a label that is read along with the voice, and `text_occluded` on a cutout (add `data-layout-allow-occlusion`, and judge by snapshot).
2. **`npx hyperframes snapshot --at <every beat>` and read the sheets. Describe each frame as a stranger would.** A first pass on one clip found a half-empty card, half-cut faces, a graphic stopping short of its mark, an end card filling half the frame, and an object colliding with type. `check` caught none of them. An OK from a tool says little: a look here once reported OK with a white layer hiding the whole film.
3. **`npx hyperframes snapshot --review`,** and open the phone sheet (360 px wide).
4. **Check the claims** one more time against `STORYBOARD.md`.
5. **Independent review:** a fresh agent gets only the storyboard and the frames, and returns `t · where · problem → fix`. On a real clip this caught an illustration that implied more than the guest had said, with every number on it correct. On a scripted film it caught a critics' score answering a question about the audience, and a camera bug: shots opening up to 0.9 s late, which reading single frames had missed. Give it consecutive frames around each card's arrival, because a fault that lasts a second falls between samples taken every few seconds. Run it before the producer sees the film, not after.
6. **★ `npx hyperframes preview --background`.** The producer can watch it and edit there. Then render.

## I. Master and QC

```bash
python3 $S/master_clip.py RENDER.mp4 outputs/NAME.mp4 --target SECONDS [--audio MIX.wav] [--size 1080x1920] [--fps 25]
python3 $S/master_clip.py --qc FILE.mp4 [--target SECONDS]
```

**Spec:** the camera's frame rate, −14 LUFS ±1, true peak ≤ −1 dBTP, within 0.5 s of target, no black ≥ 2 s, no frozen picture ≥ 12 s.

It copies the picture and applies one fixed gain to the sound, and stops if that would put the peaks over −1.2 dBTP. If it stops by a little, aim a little quieter with `--lufs -14.4`, which is still in spec; if by a lot, turn down what's peaking in the mix. Never limit it here: that's the fault this step exists to avoid. `--audio` takes the sound from the mix itself, so it is compressed once rather than twice.

**It measures; it cannot hear. A person listens once, on headphones, before release.** It can't see a see-through body either: that is `matte_qc.py`, for cutout looks.

**Beyond the checks, on the finished file:** correlate its sound with the voice track at several points to measure sync, compare it with the mix second by second to prove the gain really is fixed, and read frames at any moment that has failed before.

Export a smaller copy with `ffmpeg -i MASTER.mp4 -vf "scale=1280:720:flags=lanczos,format=yuv420p" -c:v libx264 -preset medium -crf 20 -profile:v high -c:a copy -movflags +faststart OUT.mp4`; for 9:16, `scale=720:1280`.

## J. Publish ★ (a plan: this stage hasn't been run)

**Before upload:**
- **Sign-offs:** names and titles correct; claims approved by a qualified person where the topic needs one; captions proofread by a speaker of the language.
- **Logo:** swap the typeset mark for the real one if the brand requires it. Never invent one.
- **Thumbnail:** 1280×720, under 2 MB, one face, up to four words. Render it from the film's own frames.
- **Captions file:** upload the `.srt`, so the platform has real text.
- **Description:** what the viewer learns, the guest's credentials, chapters, a link to the full episode, and, on health, legal or money topics, a line that this is general advice and not a personal recommendation.
- **End screen:** a video of 25 s or more can carry one, for 5 to 20 s, so leave room in the last seconds.

**Uploading to shared storage:** if a bucket holds other shows too, use `rclone copy --immutable`, never `sync`, which can delete. To replace a file already there, do it only when the producer asks for that file, assume there is no undo, and confirm afterwards that the folder's file list hasn't changed.
