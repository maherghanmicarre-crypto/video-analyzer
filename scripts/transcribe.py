#!/usr/bin/env python3
"""Transcribe a WAV/audio file with faster-whisper or openai-whisper (whichever is installed)."""
import argparse, sys


def ts(t):
    t = int(t)
    return f"{t // 60:02d}:{t % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--out", default="transcript.txt")
    ap.add_argument("--language", default=None, help="e.g. ar, fr, en (default: auto-detect)")
    ap.add_argument("--model", default="base", help="tiny/base/small/medium/large-v3")
    a = ap.parse_args()

    segs, lang = [], None
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(a.model, device="cpu", compute_type="int8")
        it, info = model.transcribe(a.audio, language=a.language, vad_filter=True)
        segs = [(s.start, s.end, s.text.strip()) for s in it]
        lang = info.language
    except ImportError:
        try:
            import whisper
            model = whisper.load_model(a.model)
            r = model.transcribe(a.audio, language=a.language)
            segs = [(s["start"], s["end"], s["text"].strip()) for s in r["segments"]]
            lang = r.get("language")
        except ImportError:
            sys.exit("No speech-to-text engine installed.\n"
                     "Install one: pip install faster-whisper --break-system-packages\n"
                     "(needs network access to download the model on first run).\n"
                     "Continue with frames only and tell the user audio was not transcribed.")

    lines = [f"[{ts(s)}-{ts(e)}] {t}" for s, e, t in segs if t]
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(f"# language: {lang}\n" + "\n".join(lines) + "\n")
    print(f"Language: {lang} | Segments: {len(lines)} -> {a.out}")
    if not lines:
        print("No speech detected (silent, music only, or too noisy).")


if __name__ == "__main__":
    main()
