---
name: gameplay-hype
description: The Gameplay Hype look - a 15 to 60 s vertical (9:16) short cut from game screen recordings, with no voice. Full-bleed crops that follow the action, cuts on the music's beat, punch-ins, shakes and flashes on the hits, big Thai kinetic words (stamps, damage numbers, combo counters, rank stamps, a BOSS slam) and a logo end card with a call to action, built as a HyperFrames composition from one plan.json. Use when the producer picks Gameplay Hype, or wants a trailer-style or TikTok/Reels/Shorts clip from gameplay footage, or merges several gameplay recordings into one vertical short with motion. Triggers include "gameplay hype", "hype clip", "คลิปไฮป์", "ตัดเกมเพลย์", "รวมคลิปเกมเป็นแนวตั้ง", "ใส่โมชั่นให้คลิปเกม", "merge gameplay 9x16 add motion".
model: claude-opus-5-5
---

# Gameplay Hype

**Status: one film rendered, awaiting a producer's approval.** Fantasy Diary EP02+EP03 (30 s, two recordings, Thai, no voice) was built in it. Its `plan.json` is the worked example: `references/example-plan.json`. Until a show approves this look, show the shot sheet and a few snapshot frames before the long steps, and record the decision in the show's `STYLES.md`.

- **Idea:** the game's best moments, cropped to 9:16 so the hero fills the phone, cut on the beat, with each hit landing a punch-in, a shake, a flash or a word.
- **Best for:** a game's trailer, a feature or update teaser, a boss fight or a combo reel. Recordings with the game's own big moments on screen (damage numbers, combo counters, ranks, BOSS DEFEATED) work best.
- **Costs:** nothing. No voice, no generated pictures. The music and SFX are the producer's own.
- **Needs:** HyperFrames (`npx hyperframes`), ffmpeg, Python 3 with numpy (only for `beat`), and the show's logo for the end card. The Thai font and the effects default to the ones bundled in `podcast-playbook/assets`, so keep the folders side by side.

## Ask first

1. **The look**, if the show's `STYLES.md` hasn't approved it: there is no default.
2. **A voice or not.** This look is built for no voice. A voiceover belongs to `podcast-playbook` (ElevenLabs, with the spend in the ledger), and it needs captions.
3. Length (30 s unless asked), the music, the end card's line and URL. Use only a URL and names the producer has confirmed.

## Build

`scripts/` is this skill's folder. A clip lives in `episodes/<EP>/clips/<Cnn_name>/` and holds `plan.json` (format: `references/plan.md`).

```bash
python3 scripts/hype.py scout  rec.mov --every 0.5      # contact sheet: frame i is at about i*0.5 s
python3 scripts/hype.py beat   music.mp3 --want 30      # tempo, first beat, the loudest 30 s to start from
# write plan.json: shots on the beat grid, words, fx, sfx, end card
python3 scripts/hype.py cut    CLIP                     # shots -> CLIP/hf/assets/shots, about 20 s for 19 shots
python3 scripts/hype.py frames CLIP                     # CLIP/build/shots_sheet.jpg: check every crop
python3 scripts/hype.py compose CLIP                    # CLIP/hf/index.html
cd CLIP/hf && npx hyperframes check --json && npx hyperframes snapshot --at 0,3,6,...
python3 scripts/hype.py master CLIP --out film.mp4      # render, -14 LUFS, trim, black-frame QC
```

`cut s04 s06` re-cuts only those shots. After changing the plan, run `compose` again. Studio edits to `hf/index.html` are lost on the next `compose`, so carry them back into `plan.json`.

## Planning the film

- **Scout every recording.** Note each moment by its time: the hook, the game's own big text, the payoff. Where the hero stands across the frame becomes `cx`.
- **Story in 30 s:** a hook (the biggest hit, frame 0 already titled) → the start (a calm or story shot, 2 to 4 s) → a montage that builds (1 to 2 beats a shot) → the turn (BOSS, a red flash) → the climax (the ultimate move) → the payoff (BOSS DEFEATED, the rank) → an end card of at least 4 s. With two recordings, put the one with the boss last, whichever came first in the game.
- **The music:** `beat` finds the tempo and the loudest stretch. Start the music there, so its quieter tail falls on the end card. The tempo is measured, not heard: a person listens once.
- **Shots:** `tall` (a 9:16 crop, `cx` from→to pans across the shot) for a hero in action. `wide` (the frame across the width over its own blur) when the moment is wider than the crop: a group, the game's centred banners (BATTLE!, WAVE 2, BOSS DEFEATED). Use 3 to 4 wide shots in 30 s at most. `speed: 0.5` slows a calm end-card ground.
- **Words come only from the screen.** Numbers, ranks and names are the game's own (3,251 · 66 HITS · SSS), and each lands when it appears in the footage. Thai lines describe what is visible ("ฟันรัว!", "อีกระลอก!", "ท่าไม้ตาย!"). Don't invent features or claims.
- **Every flash, punch-in and shake has a cause:** a cut on the beat, a hit or a banner. Not every shot gets a word: about one word every 2 to 3 s.

## What's on screen

- The text column runs from x 40 to x 920 (clear of TikTok's right rail), and every word sits between y 280 and y 1330. Below 1330 is the platform's caption and buttons; above 280 is its top bar.
- Word kinds: `chip` (the show's mark on the hook), `title` (one or two lines, `small` over `big`), `stamp` (tilted, slams in), `num` (a big number with a `sub` label), `rank` (gold with a red offset), `boss` (huge red), and the end card (logo with `screen` blend, CTA, URL pill).
- Theme: `{"ink": "#1A1210", "gold": "#F6C54B", "red": "#E0322B", "bg": "#140E0C"}`. Take the gold from the game's logo.

## What to check

- **`frames`:** the hero is in every crop. A pan whose start and end both miss is the usual fault: watch the whole shot, not one frame.
- **Black frames:** `master` reports them. Clips overlap by 0.02 s for this reason: a clip that ends a millisecond before the next one starts renders black.
- **The end card's ground** is a moment with no game text (no BATTLE!), slowed down.
- **A logo on a dark JPEG:** `mix-blend-mode: screen` goes on the timed clip element, not the image. A parent with `z-index` or a filter isolates the blend, and the JPEG's box shows.
- **The busiest frames:** the game's damage numbers behind a big word. Move the word or accept it, but look.
- **Fine on purpose:** `nested_structure_needs_subcomposition` and `timeline_track_too_dense` (one file is what `compose` regenerates), and `duplicate_audio_track` for SFX that layer on a hit.
- **Still needs a person:** one watch with sound (do the cuts land on the beat?), and a read of every number against the game.
