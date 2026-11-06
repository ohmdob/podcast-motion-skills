---
name: podcast-playbook
description: Turn a raw recorded podcast or talk show, or a script with no recording at all, into a finished YouTube episode and short clips of 2 to 30 minutes - script and voices, sound clean-up, transcript, paper edit, storyboard, one-camera recut, on-screen cards, 16:9 and 9:16, subtitles, master and QC - with ElevenLabs and/or Ideogram through Comfy Cloud, whichever keys are in .env (ELEVENLABS_API, COMFY_API). Sound and transcript have free local fallbacks; with no Ideogram it asks which alternative to use, such as Codex imagegen. Use this whenever the user has a recorded conversation or interview to edit, or wants to plan, cut, clean, caption, clip, master or publish an episode, even if they name only one step - "clean the audio", "find clips in this interview", "make a Short from EP02", "generate stills for this episode", "ตัดพอดแคสต์", "ทำคลิปสั้นจากรายการ", "ตัดตอนใหม่", "ทำเสียงให้สะอาด", "ทำพอดแคสต์จากสคริปต์", "ไม่มีเทป". The look of the film comes from a podcast-motion-* skill; this skill is the method around it.
model: claude-opus-5-5
---

# Podcast Playbook

Turns a raw recording into a full episode and short clips, run so that the next episode needs no re-learning. Each stage says what goes in, what comes out, which tool runs it, how it is checked, and where the producer signs off (★).

In this file `$S` means this skill's `scripts/` folder. Read the base directory shown when the skill loads and use the full path.

## Start here, every time

```bash
python3 $S/doctor.py [show folder]
```

It says which keys are set, whether the services answer, which tools are missing, and what each step will use. It is free and never prints a key. A new show starts with:

```bash
python3 $S/init_show.py ~/shows/my-show --name "My Show" --mark "MY SHOW" --lang tha
python3 $S/init_show.py ~/shows/my-show --episode EP02
```

## Keys

Keys live in `.env`, in the show's folder or at the root of the skills repo, whichever is set. The tools read the file themselves.

```
COMFY_API=
ELEVENLABS_API=
```

- **Either key is optional, and so is having both.** See the table below for what each one changes.
- **Trust `doctor.py` for what is set.** The shared file can sit in any folder above the skill, and a blank `NAME=` looks set if you only list the names.
- **Never print a value, and never `cat` or `source` the file.** The tools read it themselves, so nothing needs exporting. To see what a file holds, print names only: `cut -d= -f1 .env`.
- **`.env` never goes in a skill folder or in git.** Packaging a skill does not exclude it.
- `COMFY_API` is the key from platform.comfy.org, and Ideogram runs on **Comfy Cloud** (cloud.comfy.org). The optional third line, `COMFY_HOST=http://…:8188`, is for a ComfyUI you run yourself instead. A key is refused over plain http to a public address.

| Step | With `ELEVENLABS_API` | Without it |
|---|---|---|
| Voice clean-up | Audio Isolation, blended with the real voice | Ordinary denoise only (free). It keeps more room tone, and it was already most of the blend a producer chose by ear on a real episode |
| Transcript | Scribe | `npx hyperframes transcribe` or any `.srt`, then `transcript.py import` (commands in sound-and-script.md) |
| Word timing | Forced Alignment | From that transcript, coarser; check it by ear |
| Music, effects | `el.py music`, `el.py sfx` | The skill's bundled beds and effects, or your own files |

| Step | With `COMFY_API` | Without it |
|---|---|---|
| Pictures | Ideogram 4.5 through Comfy Cloud | **Ask the producer which alternative** (below). Caption-First, Whiteboard and Morning Show use no pictures, so they don't need the question. Animatic wants them, and letters its panels in words without them |

**No Ideogram means asking, not choosing.** If the film needs pictures and `COMFY_API` is empty or Comfy isn't answering, stop and ask which way to get them, and offer: **Codex imagegen** (`codex_image.py`, when `doctor.py` finds `codex`), **their own photographs**, **another service they name**, or **no pictures**. Don't pick for them, and don't quietly build without any. A card whose picture is missing just goes without, so a skipped question wouldn't show up as an error.

With neither key, the whole method still runs for free. Tell the producer plainly which path this run takes, because it changes how the voice will sound.

## Spending

Money is spent only with a number quoted first and the producer's approval, and that is enforced by the tools:

- A paid command **only quotes unless given `--yes`**, and exits 3 having spent nothing. Show the quote, wait for approval, then add `--yes`.
- **Never retry a paid call on your own.** A duplicate pays twice. A lost connection ends in `UNKNOWN:` and a ledger row: check `el.py quota` before anything else.
- Every paid call writes a row in the show's `data/ledger.md`, and a tool will not spend without a `show.json` to find it.
- `ideogram.py` can be re-run safely: it collects a job already paid for instead of submitting a new one.

Rates and what a whole episode costs: [references/budget.md](references/budget.md). Run `python3 $S/selftest.py` after changing `el.py`, `ideogram.py` or `studio.py`; it checks these promises offline.

## Principles

1. **The recording is the source of truth.** Tighten pauses and fillers; never change what someone meant. Every claim on screen traces to a timecode.
2. **Sensitive claims get a person's sign-off.** Graphics draw the guest's words and add no facts. On health, legal or money topics, a qualified person approves the claims before publishing. A drawing that is not measured data says so on screen.
3. **Sound first.** On a podcast the audio is the product, and the transcript, the cuts and the timing are all built on it.
4. **Write before you render.** The moment list, script lock and storyboard are free. Paid steps run only after the text they depend on is settled.
5. **Gates, not surprises.** The producer approves at each ★.
6. **Three kinds of check.** Automated QC measures formats, loudness and layout. An independent review, by a fresh agent or person who hasn't seen your conclusions, catches what you can no longer see. **A person's ears are the third, and no metric replaces them.** One real voice passed every measurement and sounded warped within seconds. Try any new check on a known fault before trusting it.
7. **Everything regenerable.** Cuts, picture, sound and compositions come from data files and tools. Fix the source, never the output. The one exception: if the producer edits a project in the HyperFrames app, that project is the source from then on, so don't rebuild it.
8. **Never invent a name or a logo.** No name goes on screen until the producer confirms it, and the show's mark is set in type.

## The stages

```
 A. Ingest ─► B. Find the moments ★ ─► C. Clean the sound ★ ─► D. Lock the script ★ ─► E. Storyboard and look ★
                                                                                            │
 J. Publish ★ ◄─ I. Master + QC ◄─ H. Review + preview ★ ◄─ G. Edit ◄─ F. Assets (quoted) ◄─┘
```

Read the reference for a stage when you reach it. They hold the commands, the checks and the mistakes already paid for.

| Stage | What happens | Read |
|---|---|---|
| A Ingest | One 1920×1080 file at the camera's frame rate; measure the sound; list what is wrong | [sound-and-script.md](references/sound-and-script.md) |
| B Moments ★ | A ranked shortlist: a question people ask → a belief → a turn → an answer they can repeat | same |
| C Sound ★ | Boost, isolate, and pick the voice treatment **by ear** with `voice_test.py` | same |
| D Script ★ | Reconcile transcripts, align, write captions; a speaker of the language reads them while listening | same |
| E Storyboard ★ | Header with claims and open questions, then one block per beat. **Ask which look** | [storyboard-and-assets.md](references/storyboard-and-assets.md) |
| F Assets | Quote, then stills, music, effects | same |
| G Edit | The cut and the camera, then the chosen look's build | [full-episode.md](references/full-episode.md), and the look's skill |
| H Review ★ | `check`, frames read as a stranger would, independent review, preview | [review-and-delivery.md](references/review-and-delivery.md) |
| I Master | `master_clip.py`, −14 LUFS, true peak ≤ −1 dBTP, format checks | same |
| J Publish ★ | Sign-offs, thumbnail, subtitles, description | same |

Data files (`show.json`, `paper.json`, `cards.json`, `captions.json`, `edl.json`, `shots.json`) are described in [references/file-formats.md](references/file-formats.md).

### No recording yet

A topic or a script goes through [references/scripted-show.md](references/scripted-show.md): script, casting from free previews, `el.py tts`, then `scripted_source.py`, which makes the recording the stages above expect. Stage D is the script itself, and stages A to C drop away.

### An episode and a clip are the same pipeline

A **clip** is a one-chapter `paper.json` with `"clip": true` and `"from": "../../full"`. It reuses the episode's audio, transcript and face tracking, so once the whole recording is processed, a clip costs nothing new. `init_show.py --clip EP02/C01_name` makes one, and every look builds it the same way. Only the whole recording needs isolation: a clip with no episode behind it can isolate just its own range (`edl.py`, in sound-and-script.md).

## Choosing the look ★

The look is a separate skill, and there is **no default**. Before building any episode or clip, ask the producer, and record the answer in that episode's `REVIEW.md`.

| Skill | Idea | Cutout | Status |
|---|---|---|---|
| `podcast-motion-studio-cut` | Real footage, typographic label cards. Quiet and trustworthy | No | Built on a real episode |
| `podcast-motion-pop-studio` | Speakers cut out on flat colour, a painted TV set. Friendly and lively | Yes | Built on a real episode |
| `podcast-motion-caption-first` | Clean footage, large captions, one big moment. Cheapest, strongest for clips | No | Test frames only |
| `podcast-motion-whiteboard` | Footage beside a board that draws what the guest says | No | Test frames only |
| `podcast-motion-morning-show` | Lower thirds and a topic strip, a format viewers know | No | Test frames only |
| `podcast-motion-animatic` | Pencil-sketched storyboard panels in stepped motion, under the real voice. Also for audio-only shows | No | Test frames only |
| `podcast-motion-photo-card` | The Animatic's card beside the speaker, with full-colour pictures. An editorial explainer | No | One scripted film rendered |
| `podcast-motion-chalkboard` | The Animatic's card beside the speaker, in chalk on a green board. A teaching feel | No | One scripted film rendered |

Each show's `STYLES.md` records which looks it has approved or ruled out, and why. Offer the looks it has approved. A look no one has approved for this show goes on real frames first (every build takes `--frames`), and the producer decides before any long render. **Update `STYLES.md` either way,** including the reason when a look is rejected.

Rules for every look:
- **Faces stay natural.** No halftone, illustration or anything that stylises a real person's face: the guest's credibility is the point of the show. Characters who are already drawn are different, when the producer asks for them.
- **Type stays live.** Text never goes in a generated image, so it stays sharp and correct and can be changed.
- **Show it before building it.** Test frames take minutes; a finished film in a rejected look costs a full round.
- **Avoid** dark voids, glow, and cream paper with serifs, unless the story asks for it and the producer says so. A sci-fi talk earned a navy blueprint.

HyperFrames does the rendering. For anything hand-built, read the `hyperframes` skill first, then `hyperframes-core`; `hyperframes-animation` and `hyperframes-audio` cover motion and mixing. Those are HyperFrames' own skills: `npx hyperframes skills` installs them. A one-off visual, such as a dial or a chart for one claim, is hand-built this way as its own sub-composition: it belongs to that episode, so it isn't a card kind.

## What has and hasn't been proven

Be straight with the producer about this. Run end to end on one real episode: a 30-minute, one-camera, two-person talk in Thai at 1920×1080, 25 fps, with the host on the left of frame and the guest on the right. Also run on one scripted film: 2 minutes, two drawn hosts, ElevenLabs voices, Thai, 16:9. **Lengths between the two, other languages, frame rates and three-person shows are not proven.** The cut and the sound stages should carry over; the shot planner assumes two people on one camera, one each side. Publishing (stage J) is a plan that hasn't been run.

## Checklists

**Before any paid call:** quote shown · approved · a `show.json` exists for the ledger.

**Before building:** look asked and recorded · `STYLES.md` read.

**Before a render:** `check` green · frames read as a stranger would · phone sheet read · claims match the storyboard · no half-cut faces · frame 0 is not empty · end card holds at least 2 s.

**Before publishing:** names and titles confirmed · claims approved · captions proofread by a speaker of the language · a person has listened to the finished film, not only samples · QC green · frames read from the final file.

**Every hand-off:** independent review run and acted on · `REVIEW.md` says what was measured, what wasn't, and the weakest shot.
