# Data files

Everything a film says on screen lives in these files, so the tools hold nothing about any one show. Templates are in `assets/templates/`; `init_show.py` copies them in.

## Project layout

```
my-show/
  show.json · STYLES.md · .env (optional) · .gitignore
  1080p/ · transcripts/ · outputs/ · data/ledger.md
  assets/music/ · assets/sfx/        the show's own library, used before the skill's
  episodes/EPxx/matte/               the person matte of the whole recording (keep it)
  episodes/EPxx/full/                paper.json · cards.json · srt_fixes.json · REVIEW.md · audio/ · assets_src/ · build/ · variant_*/
  episodes/EPxx/clips/Cnn_name/      paper.json · cards.json · captions.json · STORYBOARD.md · REVIEW.md · build/ · variant_*/
```

`variant_*` folders are generated: fix the data or the tool, not the HTML.

## show.json

```json
{
  "name": "My Show",
  "mark": "MY SHOW",
  "lang": "tha",
  "speakers": 2,
  "fps": 25,
  "face_split_x": 1000,
  "body_split_x": 800,
  "people": {"H": {"name": "", "role": ""}, "G": {"name": "", "role": ""}},
  "looks": {"morning-show": {"blue": "#0A4BD0", "ticker": false}},
  "words": {"back": ["…"]}
}
```

- `mark`: the show's name as set in type. There is no logo step.
- `lang`: `tha` and `eng` have filler lists built in; `words` adds or replaces any of them (`back`, `srt_back`, `srt_drop`, `srt_lead`, `srt_tail`, `cold_label`, `html`).
- `face_split_x`, `body_split_x`: where the two people divide, in source pixels. H is the person on the left of frame, G the right.
- `people`: leave a name empty until the producer has confirmed it. A look shows no plate for an empty name.
- `looks`: a show's own colours, by look. Judge a new palette on real frames first.

## paper.json

```json
{
  "title": "Episode title", "title_lines": ["Episode", "title"], "sub": "Series or topic",
  "source": "1080p/EP02.mp4",
  "voice": {"mix": 0.4, "chain": "gentle"},
  "cold": [[120.0, 124.8], [310.2, 314.4]],
  "cold_cards": [["The question?", "q", "H"], ["The answer", "verdict", "G"]],
  "chapters": [
    {"id": "ch01", "title": "Chapter title", "keep": [["00:03", "first words of the range", "00:16", "last words of the range"]]}
  ],
  "end_rows": ["One thing to remember", "Another"],
  "music_under": ["ch14"],
  "title_objects": ["cup"],
  "aliases": {"mug": "cup"},
  "windows": ["room"]
}
```

- `source`: the recording, relative to the project.
- `voice`: the blend chosen by ear. `mix` is the isolated share, 0 to 1; `chain` is `gentle` or `none`. With no isolated voice, the mix is ignored.
- `cold`: the cold open as `[in, out]` recording seconds, and one `cold_cards` entry `[text, kind, who]` per cut. An episode needs a cold open, because frame 0 has to be a hook.
- `keep`: anchors matched fuzzily near their timecode. Times are `mm:ss` from the recording. An empty last-words string cuts at the nearest silence.
- `music_under`: chapters that keep a low bed under the talk, such as a rapid-fire round.
- Pop Studio only: `title_objects` on the title card, `aliases` from a card's object name to a file, `windows` for pictures with no single subject, shown in an arch from `assets_src/pop/src_<name>.png`.
- Optional paths: `sfx_dir`, and `music: {"a": "...", "b": "..."}`, relative to this folder.
- Caption-First: `"captions_proofed": true` once a speaker of the language has read them.
- Animatic: `"audio_only": true` for a show with no camera.

**A clip** adds `"clip": true` and `"from": "../../full"`, drops `cold` and `cold_cards`, and has one chapter. `from` is where its audio, transcript, face tracking and voice blend come from. A `voice` in the clip's own file overrides that blend. A clip with no episode behind it leaves out `from` and keeps those files itself.

`build/chapters.json` is the film's clock, written by `build_full.py` (`--plan` writes it too, and builds nothing). `make_srt.py` and `matte_qc.py` read it.

## cards.json

A list of `[chapter id, start tc, end tc, kind, title, rows, opts]`:

```json
[
  ["ch01", "00:06", "00:20", "q", "The question?", [], {"who": "H"}],
  ["ch01", "01:16", "01:28", "rows", "Heading", ["First point", "Second point"], {"times": [76.4, 80.1]}],
  ["ch02", "02:02", "02:17", "term", "A term", ["What it means"], {"obj": "cup"}],
  ["ch02", "03:10", "03:14", "stat", "3 in 4", ["of the people the guest has seen"], {}],
  ["ch03", "05:01", "05:05", "verdict", "No", ["Only if you already do it"], {"still": "cup"}]
]
```

**Kinds:** `q` question · `term` a term and what it means · `stat` a number · `rows` a list · `take` a takeaway · `verdict` a rapid answer. A one-off visual for one claim isn't a kind: hand-build it as its own sub-composition.

**`opts`:** `who` forces the speaker it belongs with (`H` or `G`) · `times` is recording seconds, one per row, to land each row on its word (Whiteboard, Morning Show and Animatic; Studio Cut and Pop Studio space rows evenly) · `obj` and `still` name a picture (Pop Studio and Studio Cut) · `panel` names a picture for Animatic, which also uses `still` and `obj`.

Timecodes take `mm:ss` or the `hh:mm:ss` the transcript prints. A card's chapter id must exist in `paper.json`, or the build stops.

## captions.json

`[{"s": 0.12, "e": 1.92, "who": "H", "t": "the words", "hi": "words"}]`, on the film's own clock. 3 to 5 words a group, fillers removed, numbers as digits, one highlighted phrase at most.

## edl.json (a clip isolated on its own)

```json
{"source": "1080p/EP02.mp4", "work_offset": 125.0, "tail": 3, "cuts": [[0.2, 2.1], [2.4, 5.6]],
 "voice": {"mix": 0.4, "iso": "audio/isolated.mp3", "boost": "audio/boost.wav", "start": 120, "chain": "gentle"}}
```

`cuts` are on the clock of `audio/work.wav`, which starts at `work_offset` in the recording. `voice.start` is the recording time where `iso` and `boost` begin.

## shots.json (Ideogram)

`[{"out": "episodes/EP02/full/assets_src/a_cup.png", "prompt": "…", "size": "(2K) 2560x1440 (16:9)", "seed": 100, "quality": "medium"}]`. Naming: `a_<name>.png` becomes the still `<name>` for Studio Cut; `assets_src/pop/<name>.png` is a cutout object for Pop Studio; `assets_src/panels/<name>.png` is a panel for Animatic, which also finds the other two.

## srt_fixes.json

`[["misheard", "corrected", from second, to second]]`, applied to the first transcript pass within that range.

## pass1.json and scribe.json

`build/pass1.json` is `[{"a", "b", "who", "t"}]`, written by `transcript.py rows`. `audio/scribe.json` is ElevenLabs Scribe's response, or the same shape from `transcript.py import`.
