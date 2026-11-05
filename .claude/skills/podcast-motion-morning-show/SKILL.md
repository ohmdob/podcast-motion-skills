---
name: podcast-motion-morning-show
description: The Morning Show look for a podcast or talk-show film - the morning-TV format viewers already know, with lower thirds, a topic strip and an optional ticker over the real conversation, with no pictures and no cutout, in 16:9 and 9:16. Use when the producer picks Morning Show, or wants a familiar broadcast feel for an interview or discussion. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "morning show", "รายการเช้า", "แบบรายการทีวี", "lower thirds", "topic strip".
model: claude-opus-5-5
---

# Podcast Motion: Morning Show

**Status: a candidate, test frames only.** It has been built and read on real frames from one real episode, and has not had a full render or a producer's approval. So: show the test frames and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** morning TV, with lower thirds and a topic strip over the real conversation.
- **Why it works:** viewers already know the format, so it needs no explaining and suits any topic.
- **Costs:** nothing beyond the voice and transcript. No pictures, no matte.

## Build

```bash
python3 scripts/build.py episodes/EPxx/full --ratio both --frames
python3 scripts/build.py episodes/EPxx/clips/Cnn_name --ratio both --frames
```

`scripts/` is this skill's folder. The film's folder needs `full_edit.py --render` done first, with `faces.jsonl` and `pass1.json` in `build/` (`references/full-episode.md` in `podcast-playbook`). `--frames` writes a contact sheet of real frames to judge. It writes `variant_morning_show/` and `variant_morning_show_9x16/`. Render and master as in `podcast-playbook`.

## The honesty rules

A news format can make opinion read as reported fact, and that is the real risk of this look. The tool builds none of these, so don't add them by hand:

- **No "LIVE", "breaking", clock or date.** The talk was recorded, and it isn't news.
- **No real channel's branding,** colours or graphics package. The defaults are deliberately plain.
- **A headline is the guest's point, in the guest's words.** Cards add no facts. When a claim is one person's advice, don't let a banner make it sound like an announcement.
- **On health, legal or money topics,** a qualified person approves the claims, as in `podcast-playbook`. In this format it matters more, not less.

## Names

**A name plate appears only for a name set in `show.json`,** and that name goes there only once the producer has confirmed it. An empty name shows no plate, and the look still works. Don't guess one from a transcript: machine transcripts change people's names.

```json
"people": {"H": {"name": "", "role": ""}, "G": {"name": "", "role": ""}}
```

## What's on screen

- **Topic strip:** the show's mark and the chapter's title, always on, so a viewer landing anywhere knows the topic.
- **Lower third:** each card as a headline above the strip. A verdict or a number gets the accent plate, so the answer is what the eye lands on.
- **Side panel:** a list of three or more rows takes the side away from the speaker, because a lower third can't hold it. On a phone it stays below the footage, in short.
- **9:16:** the footage band sits at y 170 to 1070, the strip and headline below it inside the app's clear area, and a desk carrying the show's name fills the rest, so the frame reads as a set and not an empty space.
- **Ticker:** off, because it competes with subtitles. `"ticker": true` under `looks.morning-show` turns it on, and it only repeats this chapter's own headlines. Try it on real frames with subtitles showing before keeping it.

```json
"looks": {"morning-show": {"blue": "#0A4BD0", "deep": "#06328F", "accent": "#FFB400", "white": "#FFFFFF", "ink": "#0B1B3A", "ticker": false}}
```

A show's own colours are the first thing to change: they keep the look from reading as somebody else's channel.

## What to check

- **Does a lower third cover a gesture that matters?** It sits over the speaker's chest and hands.
- **Subtitles on the platform sit at the bottom too.** Turn them on over a test render and see what collides with the strip.
- **White text never goes on the amber sun.** Title and chapter cards keep their words short of it.
- **Long headlines:** on a phone, a card with a row gets one line of heading, which shrinks to fit, and only its first row shows. A headline too small to read wants fewer words, and the build warns when words would run under the desk.
- **Fine on purpose:** `timeline_track_too_dense`, because a chapter holds many timed headlines.
