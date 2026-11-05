# A show with no recording

For a topic or a script and nobody in front of a microphone yet. It ends in the same pipeline as a recording, so the cut, the look, the master and QC all work unchanged. Run once: a 2-minute two-host Thai film in the Animatic look, approved by its producer. `examples/hail-mary/` in `podcast-motion-animatic` holds that film's files.

```bash
# in the show's folder, after init_show.py --clip EP01/C01_name
# write script.json, then pick voices from the free previews
python3 $S/el.py voices --lang th --previews assets/casting
python3 $S/el.py tts $C/script.json $C/audio/takes --voices H=ID,G=ID       # quotes; add --yes after approval
python3 $S/scripted_source.py $C                                             # takes → voice track, transcript, and the source video
# write cards.json and paper.json from build/lines.json, so a new take moves every card with it
python3 $S/full_edit.py $C --render
python3 <look>/scripts/build.py $C --ratio 16x9 --frames
python3 $S/script_srt.py $C outputs/NAME.th.srt
```

`paper.json` needs `"source"` before `scripted_source.py` runs, and `"clip": true` with its `chapters` after. Use `"voice": {"mix": 1.0, "chain": "none"}`, since there is nothing to clean. Anchors in `keep` must leave out spaces, because the cut's text has none.

## The script

- **Look in the characters' own art for a running gag.** "แน่ใจนะ?" came from one host's "Are U sure?" sticker, and it opened and closed the film.
- **Every claim traces to a page you read.** Note the source beside the line, in `STORYBOARD.md`. Mark anything from memory as unchecked, or cut it.
- **Check who a number belongs to.** A real script asked "what did the audience think?" and answered with a critics' score. Every number on it was right, and a fresh reviewer still caught it. Read each question with its answer.
- **Short cards drop conditions.** "50:50" was "about half of Rocky's shots, by one director's count". Keep the subject in the heading.
- **Thai particles carry gender.** Until the producer says who a host is, write without ครับ/ค่ะ.

## Casting

- **Start from the free previews.** `el.py voices --previews` downloads them. The producer on the real film chose from these at once, and the 719-credit audition never ran.
- **Only some models speak Thai.** At the time of writing `eleven_v4`, `eleven_v4_turbo`, `eleven_v3` and `eleven_v3_conversational` do; `eleven_multilingual_v2` and the flash and turbo 2.5 models do not. `el.py voices` lists them live.
- **A voice in your library needs no slot.** One from the shared library takes a voice slot on the account, so say so first.
- **A scratch voice gets judged as the voice.** The Mac's Thai voice, sped up to fit, was rejected on first hearing. Don't play one to a producer as anything but a timing guide, and don't publish one: check Apple's licence, which limits system voices to personal, non-commercial use.
- **Say that the voices are synthetic** in the description.

## Length

- **Measure with `full_edit.py`, not with the takes.** It shortens pauses over 0.24 s to 0.16 s, which took 12 s out of 129 s of real voice. A first estimate from the raw takes led to cutting lines that had to come back.
- **Thai on `eleven_v4` ran about 11 characters a second.** A script of 1,335 characters came to 1:57 of film after the pauses. At that rate the first draft, 1,641 characters, would have run about 2:25.
- **Trim words before speeding up.** A line dropped from `script.json` costs nothing, a changed line costs only itself, and takes stay on disk. Keep `--tempo` within a percent or two.
- **It cost less than quoted:** about 0.44 credits a character on `eleven_v4`, against a quote of 1.

## Drawn hosts

Only when the producer asks, and only for characters who are already drawn: a real person's face stays natural, always.

- **`ideogram.py edit --mode edit`** redraws a character from its reference, in a new style, at about 18 credits. First strip anything written on the reference. Keeping the largest shape in the alpha channel removed a sticker's lettering.
- **Say what makes them them, and what must change.** "Handsome adult man, sharper jaw, narrower eyes" fixed a first pass that read as soft and young. Ask for adult proportions on a chibi character.
- **Precise Edit with `--box`** keeps every other pixel, so the mouth and blink frames line up with the portrait. Blinks worked first time on both hosts. It barely opened a thin closed mouth, so `examples/hail-mary/paint_mouth.py` paints one instead, for free.
- **The matte is a flood from the edges, and hair traps ground inside it.** On a dark set those patches show as white blobs: list them as `holes` in `hosts.json`. Keep a wider `hair` rule off the face, because one took the white out of an eye. Look at both eyes after any change.
- **Keep each host in their half.** H left of x 763 and G right of x 1157, mics included, or a close-up catches a sliver of the other. A sliver at the edge reads as a mistake.
- **Mouths flap on loudness.** It isn't lip sync, and in stepped motion it doesn't need to be.
