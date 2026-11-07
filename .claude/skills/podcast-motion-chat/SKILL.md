---
name: podcast-motion-chat
description: The Chat Feed look for a podcast or talk-show film - the conversation as a messaging app. The speakers stand on a slowly shifting gradient while a phone beside them fills with the talk: typing, then each card's heading as a message from whoever said it, its picture as an image message, its rows as replies, and a stat as a big sticker. The feed keeps the chapter's history, scrolls as it grows, and moves to whichever side is free. In 16:9, given a cutout of the speakers. Use when the producer picks Chat Feed, or wants a social, phone-native feel. Works with podcast-playbook, which does the sound, the transcript and the cut. Triggers include "chat", "แชท", "แบบไลน์", "ข้อความ", "chat feed", "messaging".
model: claude-opus-5-5
---

# Podcast Motion: Chat Feed

**Status: one scripted film rendered, not yet approved by a producer.** The Hail Mary showcase (2 minutes, two drawn hosts, Thai, 16:9) was built and rendered in it, and passed the master's QC. It hasn't been run on real footage or approved, so show test frames and get a decision before any long render, then record the result in the show's `STYLES.md`. Read `podcast-playbook` first: it holds the sound, the cut, the gates and the master.

- **Idea:** the talk becomes a chat. A phone on the free side shows "typing…", then the card's heading as a message, its picture as an image message and its rows as replies; a stat or a verdict arrives as a big sticker. The feed keeps the whole chapter and scrolls up as it grows, and the phone slides across when the other host takes over. The ground is a soft gradient that drifts through the film.
- **Best for:** conversational topics, social clips, and audiences who live in messaging apps.
- **Costs:** the pictures, if any. Everything else is free.

**It needs the cutout.** This look paints its own ground behind the speakers, so it needs `build/cutout.webm`: `rvm_matte.py`, then `make_cutout.py` (see `podcast-motion-pop-studio`), about 70 minutes of free machine time for a 30-minute recording. For drawn hosts, make the matte from their own alpha instead: the person matte, trained on real people, once lost a drawn host's whole head. The cold open keeps the room, because it has no cutout of its own.

## Build

```bash
python3 scripts/build.py episodes/EPxx/clips/Cnn_name --frames
python3 scripts/build.py episodes/EPxx/full --frames
```

`scripts/` is this skill's folder. The film's folder needs `full_edit.py --render` done first. Cards come from `cards.json` as in every look, and `opts.times` puts each row on its word. Pictures are found as in `podcast-motion-animatic` (`assets_src/panels/`, `a_<name>.png`), fitted to their subject and balanced to white by `card_stage.py` in `podcast-playbook`. It writes `variant_chat/`. 16:9 only. Render and master as in `podcast-playbook`.

## Theme

```json
"looks": {"chat": {"H": "#E3EDFF", "G": "#FFE3EC", "sticker": "#FF3D6E"}}
```

Any key overrides the default.

## Notes

- **Every message is credited to whoever really said it.** A row can be the other host's line, so the sender comes from the transcript at the row's own time, never from the card. A chat that puts words in the wrong mouth misquotes someone.
- **Names come from `show.json` "people".** Confirm them before building, as for any name on screen.
- **Nothing is invented to look like chat:** no reactions, timestamps or read receipts, only the speakers' own words.
- **No real people in pictures, no text in an image.** The same rules as every look: faces stay natural, and type stays live.
