# Worked example: a 2-minute Thai film with drawn hosts

The files behind one approved film, kept as examples rather than templates: about Project Hail Mary, hosted by anime versions of the producer's two characters, on a navy blueprint. The portraits and voice takes aren't here, so copy what's useful and replace the rest.

| File | What it shows |
|---|---|
| `script.json` | The script, line by line |
| `make_cards.py` | Cards and `paper.json` written from the voice's timing, so a new take moves everything with it |
| `hosts.json` | Two drawn hosts: placement, frames, holes in the hair |
| `paint_mouth.py` | A mouth frame painted for free, when an edit wouldn't open it |
| `deck.py` | A drawn set, with stars and lights that change on each drawing |
| `draw_art.py` | A sun flipbook, a walking character, a solid ship and a nebula, all from code |
| `moves.py` | Moves written for this story: goes in `tools/animatic_moves.py` |

The order, from the show's folder, with `$C` the clip and `$EX` this folder:

```bash
python3 $EX/draw_art.py $C/assets_src/panels
python3 $EX/paint_mouth.py assets/cast/frozen_v2.png assets/cast/frozen_v2_mouth.png 1186 926 104 46
cp $EX/deck.py tools/deck.py; cp $EX/moves.py tools/animatic_moves.py; cp $EX/hosts.json $C/hosts.json
python3 tools/deck.py
python3 $S/scripted_source.py $C --tempo 1.005
python3 $EX/make_cards.py $C
python3 $S/full_edit.py $C --render
python3 scripts/build.py $C --ratio 16x9 --frames
```

Rebuilt this way from clean folders, the frames matched the approved film to about 1 level in 255. The shot and title fixes came after that film, so a rebuild today cuts on the card edges and differs there.

**What a fresh review found on the finished film, and hasn't been fixed in this script:** line 23 asks what the audience thought and line 24 answers with a critics' score. The puppet's strings stop short of Rocky. Grace, the lead, is never drawn. Don't copy those.
