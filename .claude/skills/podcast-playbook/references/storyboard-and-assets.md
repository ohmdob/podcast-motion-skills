# Stages E and F: storyboard and assets

## E. Storyboard ★

**In:** the locked script. **Out:** `STORYBOARD.md`, one per clip (`init_show.py --clip` starts one from the template).

The header carries the source range, runtime, cast, **the one thing**, every claim on screen with its source, what is illustration, and what is still open. Then one block per beat:

```
**The turn (24.10–30.60) · GUEST:** "the line as spoken"
- what this shows, with the time each thing lands
```

**Rules that pay off later:**
- **Text lands on the word that says it.** Take the time from the transcript or `tokens.json`. The graphic is the sentence becoming visible.
- **Frame 0 is the thumbnail:** never black, never a logo. The hook is on screen before the first word ends.
- **Something new every 2 to 4 s,** and every jump cut sits on a change of shot.
- **Show the other speaker fully or not at all.** A half-cut face at the frame edge looks like a mistake.
- **Text never goes in a generated image.** All type is live.
- **The picture carries the number.** A myth-bust with a number deserves one big visual moment, once, about two-thirds in.
- **Take the look from the subject and brand,** not from a stock template.

**★ The producer approves** the shot list before anything is paid for. When the brief says no stops, record your choices instead.

## F. Assets (quoted)

**In:** the storyboard. **Out:** stills, music, effects. **Quote the total first.** Each paid call writes its own ledger row.

### Ideogram 4.5 pictures

```bash
python3 $S/ideogram.py gen --batch shots.json            # quotes; add --yes after approval
python3 $S/ideogram.py edit IN.png OUT.png "change this one detail"
```

`shots.json` is `[{out, prompt, size?, quality?, seed?}]`. Paths are relative to the project. A file that already exists is skipped, so a re-run pays only for what is missing. It runs on Comfy Cloud as one queued job, and the job is saved before waiting, so if anything stops the tool, the same command collects it without paying again. Run a long batch in the background.

Check it first with `doctor.py`. On Comfy Cloud, a refusal with HTTP 402 means out of credits, and 429 an inactive subscription; nothing is spent either way. Sizes the node takes include `(2K) 2560x1440 (16:9)` and `(2K) 1440x2560 (9:16)`.

- **Photographic B-roll:** "Editorial still-life photograph…", lens, light, where the subject sits ("right of centre with calm space on the left", for the card), ending "No text, no letters, no logos, no labels, no people, no hands." Make them bright and high-key if the set is: dark, moody stills looked like stock against bright footage.
- **No real people.** B-roll shows objects. Never generate someone who looks like a guest or a host.
- **Objects for a cutout look:** the same photographs, cut out with `swiftc -O $S/cutout_still.swift -o /tmp/cutout && /tmp/cutout in.png out.png`. Clean on a single subject; it finds nothing in a busy picture. If a picture has no single subject, generate one: "Studio product photograph of one single…, centred, isolated on a plain seamless pale grey background…".
- **Will it survive the sketch?** Pale on pale goes to nothing: a white model ship came out as a few faint lines. A flat white disc with a dark patch read as an eye, not a dimming sun. A simple symbol is cheaper and better drawn in a few lines of code: see `podcast-motion-animatic/examples/hail-mary/draw_art.py`.
- **One detail wrong?** `edit`, not a re-roll. Precise Edit keeps every untouched pixel, so it can't lose what you liked. `--box x,y,w,h` crops a small detail, edits it at full size and pastes it back.

### No Ideogram: ask

If `COMFY_API` is empty or Comfy isn't answering and the storyboard wants pictures, **stop and ask the producer which alternative they want.** Offer the ones that fit, starting with what `doctor.py` found:

| Alternative | How | Mind |
|---|---|---|
| **Codex imagegen** | `python3 $S/codex_image.py --batch shots.json`: same file as Ideogram, quotes first, `--yes` to run | Uses the plan Codex is signed in with, and reports no cost. One run per image. It has no Precise Edit, so a wrong detail means a new image. Try one picture and look at it before a long batch |
| **Their own photographs** | Same names, same folders: `a_<name>.png` or `.jpg`, cropped to 16:9 by the build; a cutout object is `assets_src/pop/<name>.png` | Check they may be used, and shoot on the plain background a cutout needs |
| **Another service they name** | Follow its own instructions, and save to the same names | Same prompt rules. Add a ledger row by hand if it costs money |
| **No pictures** | Nothing to do: a card with no picture goes without | Or a look that uses none: Caption-First, Whiteboard, Morning Show. Animatic letters its panels in words instead |

Every rule above holds whichever tool makes the picture: no words in the image, no real people, the same framing notes in the prompt. **Look at each one**, because a model that draws letters anyway will put them in a picture. Check that it matches the set: mixing tools can make stills look like they come from different films, so don't mix them within one episode without saying so.

### Music

```bash
python3 $S/el.py music "feel, instruments, tempo, sparse so speech stays clear, no vocals" assets/music/bed_a.mp3 --dur 46
```

Ask for slightly more than you need. The tools carve room for the voice (high-pass 90 Hz, −4 dB at 2.6 kHz, −16 LUFS). Under voice it plays at 0.17; on an end card it comes up to about 0.42. On a real clip that kept the voice 16 dB above everything else: measure by subtracting the voice track from the final mix, because you can't judge it from loudness alone.

The skill ships two instrumental beds as a starting point: `bed_a` (felt piano and guitar, 96 BPM) and `bed_b` (marimba, claps, upright bass, 104 BPM). The build says when it uses one. Give each show its own in `assets/music/` when you can, so shows don't sound alike.

### Sound effects

Few and exact: each one has a cause on screen. The looks call these by name, from the episode's `assets_src/sfx/`, then the show's `assets/sfx/`, then the skill's:

| Name | What it is |
|---|---|
| `whoosh_1`, `whoosh_2` | Soft air, for a card or a chapter change |
| `stamp` | A dull, firm thud, for a verdict or a number |
| `pop`, `boop` | Soft, friendly hits, for objects landing |
| `riser` | A short swell, for one payoff |

A missing sound is left out of the mix and reported.

```bash
python3 $S/el.py sfx "soft airy whoosh, a card sliding quickly past, clean, no reverb" assets/sfx/whoosh_1.mp3 --dur 0.7
```

**Check every take.** A real "rubber stamp" came back near-silent twice with no error, so `el.py` now fails on a near-silent take and moves it aside, so you can reword and run again. A different wording ("fist on a thick wooden table") with no set duration worked, at 55 credits instead of 7. Takes can also peak above 1.0; the tools normalise them.
