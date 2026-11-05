# Stage G: the cut, the camera, and the full episode

A clip and an episode go through the same steps; a clip just has one chapter.

```bash
F=episodes/EPxx/full
python3 $S/full_edit.py $F                     # the plan: durations, and any bad anchors. Free, run it as often as you like
python3 $S/full_edit.py $F --render            # build/body.mp4, cold.mp4, voice_body.wav, voice_cold.wav
swiftc -O $S/faces.swift -o /tmp/faces && /tmp/faces 1080p/EPxx.mp4 $F/build/faces.jsonl    # once per recording, about a minute
python3 $S/build_full.py $F --plan               # the shots and cards, and the film's clock. Builds nothing
# then the chosen look's build, from its own skill
```

## The cut

"Tight" takes editorial decisions, not silence removal. On a real 30-minute recording that became 22 minutes of talk:

| Removed | Time |
|---|---|
| Content: tangents, repeats, muddled stretches, the host's recaps | ≈ 6:59 |
| Pauses over 0.24 s, shortened to 0.16 s | 0:54 |
| Lone backchannels ("mm", "yeah") with quiet on both sides | 0:05 |

Backchannels barely count on a mono mix, because most overlap the other speaker. Don't plan on them.

**If a cut would make a sentence say something else, keep the sentence.** A filler was kept in one line because cutting it turned the guest's advice into a command.

1. **Write `paper.json`:** chapters of `[start tc, first words, end tc, last words]` from the transcript you trust (file-formats.md). An empty end anchor cuts at the nearest silence, for where the transcript is unusable.
2. **Tune with `full_edit.py`:** it reports durations and flags two kinds of bad anchor. A low match is the obvious one. **A range of the wrong length is the dangerous one:** a phrase matched the host's similar line a few seconds early and silently deleted 11 s of an answer. Only a card that collapsed to 0.2 s revealed it.
3. **`--render` when the length is right.** It checks the picture's frame count against the plan and refuses a mismatch. It also refuses to render over weak anchors unless given `--force`, because a bad anchor can delete part of an answer.

**Fact-check the edit, not only the graphics.** Give a fresh agent the transcript, `cards.json` and `paper.json`. On a real episode it found no wrong numbers, but seven places where a tidy cut or a short card had dropped a condition: a teaser that ended just before the guest's caveat, a rule with its direction cut, a card giving the wrong reason. Restoring them added about 50 s, and that is the right trade. Run it before the long render.

**Three failures a check or a test exposed, each now handled in the tool:** ffmpeg's `select` tops out at about 100 functions and reports it as "Cannot allocate memory", so cuts go in groups. Padded neighbours overlapped by a few frames, so `select` played them once and the voice twice, 0.9 s of drift by the end, so slices are merged. A slice past the last frame left the picture one frame short, so slices are clamped.

## The camera: one camera becomes two

A shot is a scale and a position on a wrapper around the video; never move the timed `<video>` itself. Add a 1.2 to 1.4% drift inside each shot so no framing is ever frozen, and clamp position so the frame never leaves the picture. Re-measure faces for every take, because **the camera may be re-framed during a shoot** and every shot takes its framing from its own moment.

- A close-up needs enough scale that the other person is fully out of shot: about 1.44× and up on a typical two-shot, and the planner computes it from where the faces are.
- A soft recording limits punch-ins: stop where the picture stops holding (about 1.56× on one recording).
- A wide usually needs about 1.14× anyway, to lose a laptop, a mic stand or a picture frame at the edges.

## Who is on screen

- `faces.swift` gives face positions and mouth openness through the recording, processing about 140 samples a second, so 30 minutes takes about a minute. It assumes one person each side of `face_split_x` in `show.json`.
- **Mouth movement alone is a poor speaker detector** (59% correct on the part checked by eye), because a profile face is noisy. The transcript's labels are the base; they flip only when someone's mouth stays almost still through a whole segment.
- The planner cuts on a change of speaker and on real jumps, locks the framing while a card is up, adds a listening shot about every 25 s and a wide now and then. A typical episode: about 240 shots, mean 5.4 s.

## Cards

`cards.json`, written by hand from the transcript: about one every 17 s, each anchored to the words and adding no facts. The kinds are question, term, stat, rows, take and verdict, and the look decides how each one appears. Text goes on the side of frame away from the person.

- **A number stays with its unit, and a heading wraps rather than shrinking below its rows.** The tools do both; lines break only at spaces, so write card text with a space where a break can go.
- **Measure where the head is before placing type.** A person who sits further in during one section will run behind a fixed text position.
- `build_full.py … --plan` reports the shots and cards without building anything.

## Sound

Music under the cold open, title, chapter cards, a rapid-fire round (`music_under` in `paper.json`) and the end, and **nothing under plain talk:** 22 minutes of bed is tiring. Every look writes one `assets/mix.wav`.

**Changing the sound after a render takes about 3 minutes and no new picture.** Keep `build/renders/` until the producer signs off:

```bash
python3 $S/full_edit.py $F --render --voice-only     # new voice, cut from the stored edl.json so it can't drift from the picture
python3 $S/build_full.py $F b v                      # or the look's build: a new mix.wav
python3 $S/master_clip.py $F/build/renders/full.mp4 outputs/NEW.mp4 --target SECONDS --audio $F/variant_b/assets/mix.wav
```

**Read peaks in the mix, not the voice track.** The mix's mono-to-stereo step lowers peaks by about 2.3 dB and leaves loudness alone.

## Subtitles

**Ship `.srt`, not burned-in text, at this length.** With about 480 subtitles from a machine transcript some will be wrong, and burned-in errors can't be fixed after upload.

```bash
python3 $S/make_srt.py $F outputs/EPxx_full     # <prefix>.<lang>.srt and <prefix>_chapters.txt
```

Text comes from the first transcript pass, which tends to read better, and timing from the second, which has a time per character. Lines split only on real word boundaries. **Treat the file as a draft until a speaker of the language has read it while listening.** Machine mishearings can be serious: one pass turned a polite word into a rude one, and put the wrong name on a whole topic. `srt_fixes.json` holds corrections you are confident of; each is a judgement, so proof them too.

## Render

**Use segmented capture for anything long:**

```bash
(cd $F/variant_x && HF_SEGMENTED_CAPTURE=true npx hyperframes render --quality delivery --resume -o ../build/renders/full.mp4)
```

It streams frames straight into encoded segments, so a 23-minute film takes about 3 GB of working space, renders in about 11 minutes instead of 28 (15 to 17 with a transparent cutout), and can resume after a failure. The default render holds every frame on disk, about 24 GB. `--start`/`--end` chunks don't help: they copy the project into a plan folder capped at 2 GB, and a large source video exceeds it.

**After a new cutout, make sure `renders/.hf-segments` is empty before rendering.** `--resume` reuses finished segments from a run of the same composition and settings, and a new cutout can leave the HTML identical. Whether it notices the changed video hasn't been tested.

**Clear the extract cache afterwards.** Rendering a transparent video leaves its decoded frames in `$TMPDIR/hyperframes-extract-cache-*`, 58 GB once. It's safe to delete when the master is done.

## Long jobs

**Measure memory before anything that runs for an hour.** Run about 100 frames and read `vmmap --summary PID` every 30: if the footprint climbs, stop there. A leak in one runtime version took a whole session down, and a 2-minute test found the cause. If disk space vanishes with no file to show for it, the file is swap: check `sysctl vm.swapusage` before deleting anything.

**Make long jobs resumable, and keep them from taking the machine down.** Queue them so nothing waits on a person, and write outputs to a temporary name until QC passes. Stages feed each other, so they run in sequence: a new matte through to a 720p file took about 90 minutes of machine time.
