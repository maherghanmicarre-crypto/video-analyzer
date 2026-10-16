---
name: video-analyzer
description: Fully analyze video files across all three channels - images (key frames), on-screen text (OCR), and audio (speech transcript + sound profile). Use this skill whenever the user uploads or references a video (.mp4, .mov, .mkv, .webm, .avi, .m4v) and wants it watched, summarized, transcribed, explained, reviewed, translated, or analyzed in any way - even if they just say "look at this video", "what happens in this clip", "شوف الفيديو", "حللّي الفيديو" or "regarde cette vidéo". Claude cannot ingest video natively, so ALWAYS use this skill for any video input instead of saying videos are unsupported.
---

# Video Analyzer (image + text + audio)

Claude cannot play video directly. This skill converts a video into three channels Claude can read:

| Channel | What Claude gets | Tool |
|---|---|---|
| **Image** | Key frames (JPG) with timestamps, viewed with the `view` tool | ffmpeg |
| **Text** | On-screen text read from each frame (slides, captions, UI, signs) | tesseract OCR |
| **Audio** | Speech transcript (subtitles or speech-to-text) + loudness/silence profile | ffmpeg, faster-whisper |

Everything is merged into one `report.md` timeline.

## Requirements
- Required: `ffmpeg`, `ffprobe`, Python 3.8+
- OCR: `tesseract` (+ language packs, e.g. `tesseract-ocr-ara tesseract-ocr-fra`)
- Speech: `pip install faster-whisper --break-system-packages` (downloads a model on first run, needs network)
- Audio profile loudness timeline: `numpy` (optional)

Every optional step is skipped with a clear message if its tool is missing. Never claim you read text or heard speech if that step was skipped - say which channel is missing and what to install.

## Workflow

### 1. Find the video
Uploaded files are in `/mnt/user-data/uploads/`. `view` that directory if only a name was given.

### 2. Run the pipeline (one command)
```bash
python3 /mnt/skills/user/video-analyzer/scripts/analyze_video.py "<video>" --out /home/claude/va_work
```
(Adjust the skill path to where this skill is installed.)

Options:
- `--language ar|fr|en|...` speech language (better accuracy than auto-detect)
- `--max-frames N` default 24; ~12 for short clips, up to 40 for long/dense ones
- `--start S --end E` zoom into a time range in seconds
- `--ocr-lang ara+fra+eng` OCR languages (missing ones are dropped automatically)
- `--whisper-model small` better transcription than `base`
- `--no-ocr`, `--no-transcribe` to skip a channel

Individual scripts (`extract_frames.py`, `ocr_frames.py`, `audio_profile.py`, `transcribe.py`, `build_report.py`) can be run separately, e.g. to re-run only OCR.

### 3. Read the report, then view the frames
1. Read `/home/claude/va_work/report.md`: each timestamp has the frame path, on-screen text, speech in that interval, and audio level.
2. `view` every frame listed, in order (do not silently sample).
3. Cross-check the channels: does what is said match what is shown? Is on-screen text consistent with the OCR? Fix OCR errors using what you see in the image - the image wins over OCR.

### 4. Analyze
Answer exactly what the user asked. If they gave no question, provide:
- **Overview** - what the video is (2-3 sentences)
- **Timeline** - key moments with `mm:ss`, combining visuals, on-screen text and speech
- **Key details** - names, numbers, text shown, decisions, products
- **Audio notes** - speech vs silence vs background sound, notable loud moments
- **Takeaways / issues**

Reply in the user's language (Arabic dialects, French, English...).

### 5. Zoom in
For a specific moment, re-run with `--start/--end` and a higher `--max-frames`.

## Honesty rules
- Frames are sampled, not continuous: say "between 0:40 and 1:10 the frames show..." Fast actions and brief flashes can be missed.
- The audio profile measures loudness and silence only. It cannot tell music from speech or identify sounds. You cannot hear audio: describe sound only from the transcript and the profile, and say so.
- OCR and speech-to-text make mistakes (stylized fonts, small text, accents, noise, names). Flag uncertain parts.
- Label the source of each claim: seen in image, read on screen, said in audio.
- Do not identify real people from faces. Describe them; use names only if said in audio, shown on screen, or given by the user.
- Videos over ~30 min are sampled coarsely: tell the user and offer to focus on segments.
