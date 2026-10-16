#!/usr/bin/env python3
"""One-shot pipeline: frames + OCR + audio profile + transcript + merged report.md.
Each optional step is skipped gracefully (with a clear message) if its tool is missing."""
import argparse, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def step(name, cmd, required=False):
    print(f"\n=== {name} ===", flush=True)
    r = subprocess.run([sys.executable] + cmd, capture_output=True, text=True)
    print((r.stdout + r.stderr).strip())
    if r.returncode != 0:
        if required: sys.exit(f"{name} failed.")
        print(f"[skipped] {name} unavailable - continue without it and tell the user.")
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", default="va_work")
    ap.add_argument("--max-frames", type=int, default=24)
    ap.add_argument("--start", type=float)
    ap.add_argument("--end", type=float)
    ap.add_argument("--language", help="speech language code, e.g. ar, fr, en")
    ap.add_argument("--whisper-model", default="base")
    ap.add_argument("--ocr-lang", default="ara+fra+eng")
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--no-transcribe", action="store_true")
    a = ap.parse_args()

    ex = [os.path.join(HERE, "extract_frames.py"), a.video, "--out", a.out, "--max-frames", str(a.max_frames)]
    if a.start is not None: ex += ["--start", str(a.start)]
    if a.end is not None: ex += ["--end", str(a.end)]
    step("1/5 Frames, metadata, audio", ex, required=True)

    if not a.no_ocr:
        step("2/5 On-screen text (OCR)", [os.path.join(HERE, "ocr_frames.py"), a.video, "--work", a.out, "--lang", a.ocr_lang])

    audio = os.path.join(a.out, "audio.wav")
    if os.path.isfile(audio):
        step("3/5 Audio profile", [os.path.join(HERE, "audio_profile.py"), audio, "--out", os.path.join(a.out, "audio_profile.json")])
        has_subs = os.path.isfile(os.path.join(a.out, "subtitles.srt"))
        if has_subs:
            print("\n=== 4/5 Transcript ===\nEmbedded subtitles found - using them.")
        elif not a.no_transcribe:
            t = [os.path.join(HERE, "transcribe.py"), audio, "--out", os.path.join(a.out, "transcript.txt"), "--model", a.whisper_model]
            if a.language: t += ["--language", a.language]
            step("4/5 Transcript (speech-to-text)", t)
    else:
        print("\n(no audio track: skipping audio profile and transcript)")

    step("5/5 Merged report", [os.path.join(HERE, "build_report.py"), "--work", a.out], required=True)
    print(f"\nDONE. Read {os.path.join(a.out, 'report.md')} and view the frames it lists.")


if __name__ == "__main__":
    main()
