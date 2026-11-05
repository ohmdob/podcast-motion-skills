---
name: podcast-motion-whiteboard
description: The Whiteboard look for a podcast or talk-show film - real footage beside a board, with marker notes, rings and arrows that draw what the guest is saying, so the graphics can only ever be the guest's own words. Suits explanations, how-to and expert interviews, with no pictures and no cutout, in 16:9 and 9:16. Use when the producer picks Whiteboard, or wants an explainer feel for a talk where someone is teaching. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "whiteboard", "กระดานไวท์บอร์ด", "เขียนบนกระดาน", "explainer look".
model: claude-opus-5-5
---

# Podcast Motion: Whiteboard

**Status: a candidate, test frames only.** It has been built and read on real frames from one real episode, and has not had a full render or a producer's approval. So: show the test frames and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** footage beside a board. Notes are written on as the guest says them.
- **Best for:** explanations. It follows the rule that graphics only draw the guest's words, because a person's notes on a board are exactly that.
- **Costs:** nothing beyond the voice and transcript. No pictures, no matte.

## Build

```bash
python3 scripts/build.py episodes/EPxx/full --ratio both --frames
python3 scripts/build.py episodes/EPxx/clips/Cnn_name --ratio both --frames
```

`scripts/` is this skill's folder. The film's folder needs `full_edit.py --render` done first, with `faces.jsonl` and `pass1.json` in `build/` (`references/full-episode.md` in `podcast-playbook`). `--frames` writes a contact sheet of real frames to judge. It writes `variant_whiteboard/` and `variant_whiteboard_9x16/`. Render and master as in `podcast-playbook`.

## Land the notes on the words

**This is what makes or breaks the look, and the main thing to spend time on.** A note that lands late reads as a slide, and one that lands early gives away the answer. By default rows are spaced through a card, which is only a starting point. For each card, give `opts.times`, recording seconds from the transcript, one per row:

```json
["ch02", "01:40", "01:55", "rows", "Three things to try", ["The first", "The second", "The third"], {"times": [101.5, 105.0, 109.0]}]
```

Keep a board to the point: a heading and up to four short notes. Write notes as the guest said them, with no added facts.

## What's on screen

- **16:9:** with no card, the speaker has the full frame. With a card, the board slides in on the side away from them, cut to the height of its notes, because a tall board with one line on it reads as a blank box.
- **9:16:** the footage band sits on top (y 0 to 820), and the board fills everything below. The board is always there, so it needs its own place: notes between y 850 and 1330, where the app leaves the screen clear. With no note up, it carries the chapter's name, so a viewer landing anywhere knows the topic.
- **One mark per card, and it has to mean something:** a ring holds an answer or a number, a line stresses the point, an arrow joins a term to what it means. **A line that means nothing is decoration.** Painted lines that meant nothing were rejected on an earlier look.
- **Marker colours:** blue for headings, red for a verdict or number, green for ticks, ink for notes.
- **Chapter, title and end cards:** the whole frame is the board.

Handwriting is Itim, which holds Thai and Latin and stays readable. Hand-lettered type can be hard to read on a phone, so **read every note at phone size**, and raise the size or cut the words before anything else.

```json
"looks": {"whiteboard": {"board": "#FBFCFA", "frame": "#9AA5AB", "ink": "#1E2933", "blue": "#1746C7", "red": "#D3261F", "green": "#0B7F56"}}
```

## What to check

- **Does the ring clear the words?** Rings and lines are placed by measuring the text. Long headings can crowd them: shorten the heading.
- **Does a board cover a gesture that matters?** It stands on the far side from the speaker, and can still hide their hands. The planner holds the framing while a card is up.
- **Marks drawn on a Thai heading:** an underline sits below any vowels and tone marks. Look at it.
- **Fine on purpose:** `timeline_track_too_dense`, because a chapter holds many timed notes, and in 9:16, `container_overflow` and `panel_out_of_canvas` on the board running past the frame.
