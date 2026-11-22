---
videomd: 1
name: 1-video-76236
description: 'Nine fruits overview; Love: heart; Joy: sun Made with (inferred): code / template render 100%'
source:
  file: 1-Video-76236.mp4
  sha256: b20a4cfb823755293e92ef152a560fd303f79c9d733f75acf593a7993b21ff5d
  duration: 56.8
  size: 720x1280
  fps: 30.0
  aspect: '9:16'
shots: 13
lang: en
made_mix:
  code_render: 1.0
confidence: 0.945
readers:
- tools
- agent
open_questions: 2
generator:
  name: rea-video
  version: 0.1.0
---

# 1-Video-76236.mp4

**Verdict** (inferred): code / template render 100%; audio: voice + music 89.1BPM (to confirm, leaning stock library music) + 10 sound effects
**Narrative**: #01 Nine fruits over… → #02 Love: heart → #03 Joy: sun → #04 Peace: dove → #05 Patience: rotati… → #06 Kindness: smilin… → #07 Goodness: hands → #08 Transition gap → #09 Faithfulness: ha… → #10 Gentleness: feat… → #11 Self-control: fi… → #12 Connected grid p… → #13 call to action
**Made with** (inferred, by duration): code / template render 100%
**Remake**: code render / screen capture 13 shots → 1 code project

## Next steps

- Remake: Capsule Cinema does the generation, assembly and checks. `rea-video remake <this dir>` hands over to it, does what can be done automatically and keeps the original elsewhere; `remake/status.md` says per shot what is left. Add incoming clips to `remake/mine.json` and run it again
- Code-rendered shots are best rebuilt in an HTML video framework (such as HyperFrames) from the rhythm and key frames in `video/rhythm.md`; `rea-video code-remake <this dir>` only makes a quick draft for particles / data-visualisation pictures

## Open questions

- No AI listened to the soundtrack (the review covered the picture only): real voice versus TTS is inferred from the waveform; the effects were found on the separ…
- music source to confirm: most likely stock library music (52%); how to check is under “Sound”

## Map

Read this page first; for detail, open only the file you need. Each line is `path | ~tokens | what is in it · when to read it`; paths are relative to this directory.

```videomd-map
video/timeline.md | 1088 | Timeline: one line per shot · what a stretch says, which shots need review, how a shot was made
video/moments.md | 85 | Special moments · reveals, twists, climaxes, goofs: times, key frames, clips
video/content.md | 281 | Content and structure · what it says, the narrative line, structure, the script
video/cast.md | 109 | Cast, scenes and props · reference images for characters, first-frame prompts
video/sound.md | 688 | Sound · voice, music, sound effects, beats and sources
video/rhythm.md | 587 | Rhythm and key frames · when cuts and transitions happen, shot lengths, the change curve, key frames of each shot
video/look.md | 75 | Camera, lighting and editing · for filmed shots: framing, camera, lighting, kit
video/packaging.md | 81 | Packaging · subtitles, styled text, stickers, picture-in-picture: timing and style
video/remake.md | 6640 | Remake plan · generation units, shoots, code builds, real material to collect, acting and emotion
video/shots/*.md | 469 | Per-shot detail, tokens per file on average · checking one shot: what is seen, the inference and its basis, prompts, frames
breakdown.json | 52483 | Full raw data · for programs; a model rarely needs it
shots/ | - | contact sheet, first and last frame of each shot · checking by eye
storyboard.jpg | - | storyboard of the whole video · the whole video at a glance
stems/ | - | voice, music and effects stems · listening, remaking the sound
sfx/ | - | a clip of each sound effect · finding matching effects
packaging/ | - | subtitle files, packaging timeline, sticker frames · remaking subtitles and packaging
frames/ | - | picture scenes: full-size frames, the drawn layer cut out and sampled, measurements · remaking rendered pictures
audio.png | - | waveform and beat chart · seeing the rhythm
```

## How to read

- One shot per line: `#<n> start-end (s) | key value | …`. A key ending in `~` is the tools' inference; keys without it are visible on screen or measured directly.
- `story` job in the story and the point · `seen` what is on screen · `act` acting (emotion, strength, face) · `camera` camera move · `overlay` overlays · `made~` how it was made (inferred) · `material~` where the material came from (inferred) · `remake` remake route · `flag` needs a second look
- Full detail for a shot is in `video/shots/<n>.md` (e.g. `video/shots/07.md`).
- What is “seen” can be checked against the frames; what is “inferred” is the tools' and image readers' judgement, with the basis in each shot file. When they disagree, trust the frames.
