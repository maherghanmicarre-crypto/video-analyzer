#!/usr/bin/env python3
"""Describe the audio track without speech recognition: loudness, silences, sound segments, peaks."""
import argparse, json, os, re, subprocess, sys, wave


def fmt(t):
    t = int(round(t)); return f"{t // 60:02d}:{t % 60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--out", default="audio_profile.json")
    ap.add_argument("--silence-db", type=float, default=-35)
    ap.add_argument("--min-silence", type=float, default=0.8)
    a = ap.parse_args()

    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.audio, "-af",
                        f"silencedetect=noise={a.silence_db}dB:d={a.min_silence},volumedetect",
                        "-f", "null", "-"], capture_output=True, text=True)
    err = r.stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    mean = re.search(r"mean_volume: (-?[0-9.]+) dB", err)
    peak = re.search(r"max_volume: (-?[0-9.]+) dB", err)

    with wave.open(a.audio) as w:
        rate, n = w.getframerate(), w.getnframes()
        dur = n / rate
        raw = w.readframes(n)

    silences = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else dur
        silences.append((max(s, 0), min(e, dur)))
    sound, cur = [], 0.0
    for s, e in silences:
        if s - cur > 0.3: sound.append((cur, s))
        cur = e
    if dur - cur > 0.3: sound.append((cur, dur))
    silent_total = sum(e - s for s, e in silences)

    # coarse loudness timeline (RMS dBFS per window)
    timeline, peaks = [], []
    try:
        import numpy as np
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        win = int(rate * max(1.0, dur / 60))  # <= ~60 points
        for i in range(0, len(x), win):
            seg = x[i:i + win]
            rms = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0
            db = 20 * np.log10(rms) if rms > 1e-6 else -90.0
            timeline.append({"time": fmt(i / rate), "time_sec": round(i / rate, 1), "rms_db": round(db, 1)})
        if timeline:
            top = sorted(timeline, key=lambda p: p["rms_db"], reverse=True)[:5]
            peaks = sorted(top, key=lambda p: p["time_sec"])
    except ImportError:
        pass

    prof = {
        "duration": fmt(dur), "duration_sec": round(dur, 2),
        "mean_volume_db": float(mean.group(1)) if mean else None,
        "peak_volume_db": float(peak.group(1)) if peak else None,
        "silent_percent": round(100 * silent_total / dur, 1) if dur else 0,
        "sound_segments": [{"from": fmt(s), "to": fmt(e)} for s, e in sound],
        "silence_segments": [{"from": fmt(s), "to": fmt(e)} for s, e in silences],
        "loudest_moments": peaks,
        "loudness_timeline": timeline,
        "note": "This describes loudness and silence only. It cannot tell speech from music; "
                "use the transcript for speech content.",
    }
    json.dump(prof, open(a.out, "w"), indent=2)
    print(f"Audio {prof['duration']} | mean {prof['mean_volume_db']} dB | silent {prof['silent_percent']}% "
          f"| sound segments: {len(sound)} -> {a.out}")


if __name__ == "__main__":
    main()
