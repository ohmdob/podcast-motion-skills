# Stages A to D: recording, moments, sound, script

Commands here run from the show's folder, with `F=episodes/EPxx/full` and the recording at `1080p/EPxx.mp4`.

## A. Ingest

**In:** camera files. **Out:** one 1920×1080 file, a first transcript, and a note of what is wrong with them.

- **Keep the camera's frame rate.** It is the only rate at which a talking head never judders. Set `"fps"` in `show.json`. Scale to 1920×1080 here if needed, because the framing and the matte are tuned for it.
- **Measure the sound before anything else:** `ffmpeg -ss 0 -t 180 -i FILE -af ebur128=peak=true -f null -`
- **Look at frames from each take.** A camera moved between takes means framing numbers don't carry across them.
- **Ask for the camera originals.** Boosting a merged MP4 with compressed audio by 28 dB also boosts its artefacts. Camera files often hold uncompressed audio, which gives isolation far more to work with.
- **Note the problems for later stages:** how quiet it is, how soft the picture is (that limits punch-ins), set clutter at the frame edges, a recording that starts mid-sentence.

**Tell the producer, for next time:** set the recorder's gain so speech peaks around −12 dBFS and **give each person their own mic track.** That single change removes the hardest parts of the sound stage, speaker labels and overlapping cuts. Focus on the guest's seat, and record a clean opening line.

### The first transcript

First the boosted voice, which everything after this is built on. Set the gain from your measurement: +30 dB suited one very quiet recording.

```bash
ffmpeg -i 1080p/EPxx.mp4 -vn -ac 1 -ar 48000 -c:a pcm_s24le $F/audio/raw.wav
ffmpeg -i $F/audio/raw.wav -af "volume=30dB,alimiter=limit=0.89:attack=5:release=50" -c:a pcm_s16le $F/audio/boost.wav
python3 $S/el.py scribe $F/audio/boost.wav $F/audio/scribe_raw.json --note "EPxx first pass"     # quotes; add --yes after approval
python3 $S/transcript.py rows $F/audio/scribe_raw.json --md transcripts/EPxx.md --rows $F/build/pass1.json \
    --take 0:speaker_0=H,speaker_1=G
```

**No ElevenLabs key:** transcribe locally, then give it the same shape. `$F/audio/scribe.json` is what the cut reads. Pick `--language` for the show; a model without `.en` handles languages other than English. This route hasn't been tried on Thai speech, so read the result against the sound before relying on it.

```bash
npx hyperframes transcribe 1080p/EPxx.mp4 --language th --model medium --to srt -o transcripts/EPxx.srt
python3 $S/transcript.py import transcripts/EPxx.srt $F/audio/scribe.json
python3 $S/transcript.py rows $F/audio/scribe.json --md transcripts/EPxx.md --rows $F/build/pass1.json
```

Any `.srt` works in the middle step. An `.srt` has no word times, so they are spread evenly through each cue: good enough to find anchors, and real cuts still come from silence detection. It also has no speakers, so **every row comes out as one person: correct the `who` in `pass1.json` from the footage,** because the shot planner relies on it.

## B. Find the moments ★

**In:** the transcript. **Out:** a ranked shortlist, each with a timecode and one sentence: *what does the viewer learn?*

A good clip is a complete arc: **a question people really ask → a belief → a turn → an answer they can repeat.** It starts on the question, not on the build-up, and holds up with no context. Prefer one with a number or a clear yes/no, because those become the visual.

| Clip | Timecode | Arc | Check first |
|---|---|---|---|
| C01 name | mm:ss–mm:ss | The question → the answer | Anything needing an expert's check, or where the words get muddled |

★ The producer picks the moments.

## C. Clean the sound ★

**In:** the range of the source with a few seconds' handle, or the whole recording. **Out:** `audio/isolated.mp3`, and a voice chosen by ear.

```bash
python3 $S/el.py isolate $F/audio/boost.wav $F/audio/isolated.mp3 --note "EPxx"     # quotes first; add --yes after approval
python3 $S/el.py scribe  $F/audio/isolated.mp3 $F/audio/scribe.json --note "EPxx second pass"
```

- **Boost before isolating,** to give the model a healthy level.
- **The second transcript** has a time for every character, and the cut's anchors and the subtitles' timing are read from it.
- **Isolation alone is not the finish.** On a real episode the numbers looked excellent (noise floor −24.7 dB → −76 dB) and QC passed 8/8, yet the producer heard the voice as warped within seconds. The speech had so little signal above 4 kHz that the AI was rebuilding it, and a heavy chain (de-esser, 2.4:1 compressor, `dynaudnorm`) then pushed up the residue in the gaps.

**★ Pick the treatment by ear, for every new recording, before anything is rendered.** This one test, done first, would have saved a full mix.

```bash
python3 $S/voice_test.py $F outputs/audio_test 10,18 40,50 [--blends .8,.6,.4]
```

It writes the same words in each treatment at the same loudness. Use the film's own words, including the lines you expect to open with; the ranges are recording times, from the transcript. Set the choice in `paper.json`: `"voice": {"mix": 0.4, "chain": "gentle"}` (40% isolated + 60% real voice, the choice on that episode). A short sample can mislead: 60/40 was picked first and then heard as off in the film, so judge with the film's own words. Changing the choice later needs no new picture (see full-episode.md, Sound).

**With no isolated voice,** `full_edit.py` sets its silence line from the recording's own quiet parts, because boosted room tone may never reach the fixed line an isolated voice uses. Tell the producer what that costs: measured against an isolated voice, it finds about 43% of the long pauses, and about 76% of the time it trims is truly silent. So the cut keeps more pauses and needs listening to, and tighter pacing means trimming by hand in `paper.json`.

**Two faults QC can't see, both handled in `voice_lib.py`:**
- **`loudnorm ... linear=true` isn't a promise.** When the gain would break its true-peak target, which a quiet recording always does, it runs dynamic without saying so; the voice rode by up to 10 dB over a film. So: one fixed gain and a limiter.
- **Align on speech envelopes, not waveforms.** The isolated voice is rebuilt, so it barely correlates with the real one, and waveform correlation returned different answers depending on the input. Envelopes agree across the whole recording.

## D. Lock the script ★

**In:** the first transcript and the isolated voice. **Out:** a transcript you trust, `captions.json`, word timings.

**Do not trust one transcript pass.** What went wrong on a real episode:
- **Speaker labels swapped between takes.** `speaker_0` was the host in one and the guest in the next. `transcript.py --take` handles that once you know.
- **Diarization on a mono mix failed:** it called 48 of the first 50 seconds one person. Set speakers by hand, from the footage.
- **Isolation doesn't always help transcription.** A second pass misheard lines the first got right. Compare both and keep the one that makes sense.
- **Names drift.** The guest appeared under four different names. **Ask; never guess a name on screen.**

**Steps for words on screen:**
1. **Reconcile the text.** Write `tokens.txt` as what was really said, fillers included, split by spaces where you want timings.
2. **Align,** on the clip's own stretch of voice: `ffmpeg -ss SECONDS_INTO_ISOLATED -t LENGTH -i $F/audio/isolated.mp3 -c:a pcm_s24le audio/work.wav`, then `python3 $S/el.py align audio/work.wav audio/tokens.txt audio/align.json`. With no isolated voice, take it from `audio/boost.wav`.
3. **Write `captions.json`:** `{s, e, who, t, hi}`, 3 to 5 words a group, fillers removed, numbers as digits, one highlighted phrase at most.
4. **★ A speaker of the language reads the captions while listening.** An agent can only compare two transcripts; it cannot hear which is right.

**Alignment is for captions, not for cuts.** It stretched a 0.45 s pause into 0.8 s and placed the next word late. For cuts, trust `silencedetect`: `ffmpeg -i work.wav -af silencedetect=noise=-38dB:d=0.12 -f null -`.

## A clip with no episode behind it

To isolate only a clip's range, which costs far less, use `edl.py`. You write its `edl.json` by hand: the cut list and the voice blend, in file-formats.md. Say the handle starts at 120 s and the clip's first word is at 125 s:

```bash
C=episodes/EPxx/clips/Cnn_name
mkdir -p $C/audio
ffmpeg -ss 120 -t 60 -i 1080p/EPxx.mp4 -vn -ac 1 -ar 48000 -c:a pcm_s24le $C/audio/raw.wav
ffmpeg -i $C/audio/raw.wav -af "volume=30dB,alimiter=limit=0.89:attack=5:release=50" -c:a pcm_s16le $C/audio/boost.wav
python3 $S/el.py isolate $C/audio/boost.wav $C/audio/isolated.mp3
ffmpeg -ss 5 -i $C/audio/isolated.mp3 -c:a pcm_s24le $C/audio/work.wav      # starts where edl.json's work_offset says, here 125
python3 $S/edl.py $C
python3 $S/prep_assets.py $C
```

This route gives `build/edit.mp4`, `voice.wav` and `tokens.json`, for a clip you direct by hand in HyperFrames. To use a look's data-driven builder, make the clip from the episode's audio instead (SKILL.md, "An episode and a clip").
