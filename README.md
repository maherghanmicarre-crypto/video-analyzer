# video-analyzer — a Claude Skill

Lets Claude "watch" and analyze videos across **image + text + audio**. Claude can't play video directly, so this skill extracts
**key frames (image)**, **on-screen text via OCR (text)**, and a **speech transcript + audio profile (audio)**, merges them into one timeline, and Claude analyzes it.

يخلي Claude يشوف الفيديوهات ويحللها بالصورة والنص والصوت: صور مفصلية، النص اللي يظهر في الشاشة (OCR)، ونص الكلام مع تحليل الصوت، وبعدها يحلل كل شي مع بعضو.

## Install

**Claude.ai / Claude app:** Settings → Capabilities → Skills → upload the `video-analyzer` folder as a `.zip`.

**Claude Code:**
```bash
git clone https://github.com/<maherghanmicarre-crypto>/video-analyzer ~/.claude/skills/video-analyzer
```

## Requirements
- `ffmpeg` (required) and Python 3.8+
- OCR: `tesseract` + language packs (e.g. `tesseract-ocr-ara tesseract-ocr-fra`)
- Speech: `pip install faster-whisper` (downloads a model on first run)
- Optional: `numpy` for the loudness timeline

## Usage
Upload a video and ask anything: "Summarize this video", "What's said at 2:30?",
"شنوة صاير في الفيديو هذا؟", "Résume cette vidéo".

## How it works
One command runs everything: `python3 scripts/analyze_video.py video.mp4 --out work`

1. `extract_frames.py` — metadata, scene-change + evenly-spaced frames, audio, embedded subtitles
2. `ocr_frames.py` — on-screen text per frame (Arabic/French/English), de-duplicated
3. `audio_profile.py` — loudness, silences, sound segments, loudest moments
4. `transcribe.py` — speech-to-text (faster-whisper / openai-whisper)
5. `build_report.py` — merges all channels into `report.md`
6. Claude reads the report, views the frames, and writes the analysis

## Limitations
- Claude sees sampled frames, not continuous motion; very fast events can be missed.
- Claude cannot hear: audio understanding comes from the transcript and a loudness/silence profile (it can't identify music or sounds).
- OCR and transcription can make mistakes; each step is skipped with a clear message if its tool is missing.
- Long videos are sampled coarsely; ask for a specific time range to zoom in.

## License
MIT
