# podcast-motion-skills

Claude Code skills that turn a raw recorded podcast or talk show into a finished episode and short clips. They cover the sound, the transcript, the edit, the on-screen graphics, subtitles, and mastering, and you choose how the film looks.

| Skill | What it does | Needs a cutout | Status |
|---|---|---|---|
| `podcast-playbook` | The method: sound, transcript, cut, review, master, publish | | Run end to end on one real episode, except publishing |
| `podcast-motion-studio-cut` | Real footage with typographic label cards. Quiet and trustworthy | No | Built on a real episode |
| `podcast-motion-pop-studio` | Speakers cut out on flat colour, a painted TV set. Lively | Yes | Built on a real episode |
| `podcast-motion-caption-first` | Clean footage, large captions, one big moment. Cheapest | No | Test frames only |
| `podcast-motion-whiteboard` | Footage beside a board that draws what the guest says | No | Test frames only |
| `podcast-motion-morning-show` | Lower thirds and a topic strip, a format viewers know | No | Test frames only |
| `podcast-motion-animatic` | Pencil-sketched storyboard panels in stepped motion, under the real voice. Also for audio-only shows | No | Test frames only |

## Install

```bash
git clone https://github.com/ohmdob/podcast-motion-skills.git
cd podcast-motion-skills
./install.sh
```

`install.sh` links the skills into `$CLAUDE_CONFIG_DIR/skills`, or `~/.claude/skills` if that isn't set, so every Claude Code session can use them and `git pull` updates them. It also makes a private `.env` from `.env.example`. `./install.sh --uninstall` removes only those links.

**Don't move the skills apart.** The looks use the scripts in `podcast-playbook`, so keep the folders side by side.

### Use Claude Opus 5.5

These skills are written and tested for **Claude Opus 5.5**. Start Claude Code with it:

```bash
claude --model claude-opus-5-5
```

or pick it with `/model` in a session. Each skill also sets `model: claude-opus-5-5`, so the turn it runs in uses that model even if the session is on another one.

### What else you need

```bash
python3 .claude/skills/podcast-playbook/scripts/doctor.py
```

`doctor.py` says what's installed, which keys are set, and what each step will use. It's free and never prints a key.

- **Required:** `ffmpeg`, Python 3 with `numpy` and `pillow`, Node.js. [HyperFrames](https://hyperframes.heygen.com) runs through `npx`, and `npx hyperframes skills` installs its own skills, which these point to for anything hand-built.
- **macOS, with the Xcode command line tools.** Every look needs face tracking from Apple Vision, compiled with `swiftc`, so the looks don't build on other systems.
- **For Pop Studio:** `uv`, which runs the person matte.
- **Optional:** the [Codex CLI](https://github.com/openai/codex), for pictures when Ideogram isn't available.

## Keys

Put keys in `.env`. It's ignored by git, so it never reaches the repo.

```
COMFY-API=
ELEVENLABS-API=
```

**Either one is optional, and so is having both.**

| Key | Used for | Without it |
|---|---|---|
| `ELEVENLABS-API` | Voice isolation, transcript, word timing, music, effects | Ordinary denoise, any `.srt` or `npx hyperframes transcribe`, and the bundled music and effects |
| `COMFY-API` | Pictures from Ideogram 4.5 on [Comfy Cloud](https://cloud.comfy.org). Get the key at [platform.comfy.org](https://platform.comfy.org/login) | The skill asks which alternative you want: Codex imagegen, your own photographs, or none |

To use a ComfyUI you run yourself instead of Comfy Cloud, add `COMFY-HOST=http://your-machine:8188`.

The names hold a hyphen, so a shell can't `source` this file; the tools read it themselves. A show's folder can have its own `.env`, and a blank line there falls back to this one.

**Paid calls never run by surprise.** A paid command only quotes unless given `--yes`, nothing retries by itself, and every call gets a row in the show's `data/ledger.md`.

## Use

In Claude Code, describe the job. For example:

```
I've got a 30-minute recording at ~/shows/my-show/1080p/ep02.mp4. Take it through the playbook.
Find the best clips in this episode and make a Short from the first one.
Clean the audio on this recording. Let me hear the options before you mix anything.
Build this episode in the whiteboard look and show me test frames first.
```

You can also call a skill directly with `/podcast-playbook` or `/podcast-motion-whiteboard`.

The skill stops for you at each decision: which moments, which voice treatment by ear, which look, and the final preview. **There is no default look.** It asks each time, and each show's `STYLES.md` records what it has approved or ruled out.

### The steps, if you want to run them yourself

From this repo's folder, so the paths stay right after the `cd`:

```bash
REPO="$PWD"; S="$REPO/.claude/skills/podcast-playbook/scripts"
python3 $S/init_show.py ~/shows/my-show --name "My Show" --mark "MY SHOW" --lang tha
python3 $S/init_show.py ~/shows/my-show --episode EP02
cd ~/shows/my-show
F=episodes/EP02/full

# sound and words (no ElevenLabs key: see references/sound-and-script.md)
ffmpeg -i 1080p/ep02.mp4 -vn -ac 1 -ar 48000 -af "volume=30dB,alimiter=limit=0.89:attack=5:release=50" -c:a pcm_s16le $F/audio/boost.wav
python3 $S/el.py isolate $F/audio/boost.wav $F/audio/isolated.mp3         # quotes; add --yes to spend
python3 $S/el.py scribe  $F/audio/isolated.mp3 $F/audio/scribe.json
python3 $S/transcript.py rows $F/audio/scribe.json --md transcripts/EP02.md --rows $F/build/pass1.json --take 0:speaker_0=H,speaker_1=G
swiftc -O $S/faces.swift -o /tmp/faces && /tmp/faces 1080p/ep02.mp4 $F/build/faces.jsonl

# write paper.json and cards.json, then the cut
python3 $S/full_edit.py $F
python3 $S/full_edit.py $F --render

# a look, with test frames first
python3 "$REPO/.claude/skills/podcast-motion-whiteboard/scripts/build.py" $F --ratio both --frames

# render and master
(cd $F/variant_whiteboard && HF_SEGMENTED_CAPTURE=true npx hyperframes render --quality delivery --resume -o ../build/renders/full.mp4)
python3 $S/master_clip.py $F/build/renders/full.mp4 outputs/EP02.mp4 --audio $F/variant_whiteboard/assets/mix.wav
```

Each skill's `SKILL.md` and `references/` hold the detail, including the mistakes already paid for.

## What is proven

This has been run on **one** real episode: a 30-minute, one-camera, two-person talk in Thai, 1920×1080, 25 fps, with the host on the left and the guest on the right.

- **Other languages, frame rates and three-person shows are not proven.** The cut and sound stages should carry over; the shot planner assumes two people on one camera, one each side.
- **Caption-First, Whiteboard, Morning Show and Animatic are candidates.** They have been checked on real frames, and have not been rendered at full length or approved by a producer.
- **Publishing is a plan.** It hasn't been run.

`scripts/selftest.py` checks the promises around money and keys offline.

## Licences

- **Fonts** in `assets/fonts` (Mitr, Noto Sans Thai, Itim) are under the SIL Open Font License.
- **The matting model** (Peter Lin's [RobustVideoMatting](https://github.com/PeterL1n/RobustVideoMatting), GPL-3.0) isn't in this repo. It downloads on first use and is checked against a pinned hash.
- **The music and effects** in `assets/` were generated with ElevenLabs. Check their terms for your own use, and replace them with your show's own when you can.
