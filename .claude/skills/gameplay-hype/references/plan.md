# plan.json

One file describes the whole film. Relative paths are relative to the clip's folder. A full example is `example-plan.json`, the Fantasy Diary EP02+EP03 short.

## Top level

| key | meaning |
|---|---|
| `duration`, `fps`, `bpm` | Film length in seconds, 30 fps, and the music's tempo from `hype.py beat` |
| `sources` | `{"E2": "path/to/rec.mov"}`. Use the full-res originals: a 9:16 crop of a 720p copy is soft |
| `music` | `{"src", "start", "volume": 0.8, "fade_out": 1.6}`. `start` is the offset into the track, on a beat |
| `game_volume` | Gain on the recordings' own sound (2.2 lifts quiet game audio under the music) |
| `font` | A Thai `.ttf` for the words (copied in as `assets/fonts/thai.ttf`) |
| `logo` | The end card's logo. A logo on black works: it is screen-blended |
| `sfx_dir` | A folder of `<name>.mp3` effects that `sfx` names |
| `theme` | `ink`, `gold`, `red`, `bg` |

## shots

```json
{"id": "s01", "mode": "tall", "src": "E2", "in": 5.90, "beats": [0, 4], "cx": [0.52, 0.47]}
```

- `beats`: in and out on the music's beat grid. Times snap to whole frames. Shots must tile the film with no gaps: each shot's out beat is the next one's in beat.
- `in`: the source time the shot starts at.
- `mode`: `tall` (a 9:16 crop the full height of the source; `zoom` > 1 crops tighter) or `wide` (the frame scaled to 860 px high and cropped to the width, at y 450, over a blurred copy).
- `cx`: the crop's centre as a fraction of the source width, `[start, end]` for a pan.
- `speed`: 0.5 slows the picture and sound (an end-card ground).

## words

```json
{"id": "t-dmg", "shot": "s01", "at": 0.45, "dur": 1.8, "top": 880, "kind": "num", "text": "3,251", "sub": "DAMAGE", "gold": true}
```

- Timing: `shot` + `at` (seconds into the shot) or `atb` (beats into the shot), and `dur`. The exit (blur out) starts 0.16 s before the end; `"exit": false` keeps it until the clip ends.
- Place: `top` in px. Centred in the safe column by default; `left` or `right` in px for a stamp to one side.
- `kind`: `chip` (`text`) · `title` (`lines`: `[{"t", "size": "small"|"big", "gold"}]`) · `stamp` (`text`, `tilt`: `l`|`r`, `gold`) · `num` (`text`, `sub`, `gold`) · `rank` (`text`, `sub`, `small`) · `boss` (`text`).
- `enter`: `slam` (default; `from` = the starting scale, 1.8 to 3.2), `blur` (line by line), `blur-slam` (small line blurs in, big line slams), `on` (already there at the cut: the hook at frame 0), `none`.

## end

```json
{"shot": "s19", "cta": "เล่นบนเว็บได้เลย", "url": "example.com", "logo_top": 380, "cta_top": 930, "url_top": 1150}
```

The last shot is darkened by a veil. The logo arrives at +0.15 s, the CTA at +0.55 s and the URL at +0.85 s, and they hold to the end.

## fx

```json
{"shot": "s03", "atb": 1, "punch": 1.18, "shake": 0.8, "flash": [0.6, 0.25], "red": [0.75, 0.4]}
```

- `punch`: the camera steps to that scale in 0.12 s and holds until the next cut, where it resets.
- `shake`: a 0.25 s jolt; 1 is about 22 px.
- `flash` / `red`: a white or red flash `[opacity, fade seconds]`.

## sfx

```json
{"file": "whoosh_1", "shot": "s02", "at": -0.12, "dur": 0.68, "vol": 0.6}
```

A whoosh starts 0.1 to 0.15 s before its cut. A stamp or pop lands with its word.
