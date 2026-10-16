#!/usr/bin/env python3
"""Merge frames + on-screen text (OCR) + speech (transcript/subtitles) + audio profile into report.md."""
import argparse, json, os, re


def to_sec(s):
    p = [float(x.replace(",", ".")) for x in s.split(":")]
    return p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2]


def parse_transcript(path):
    segs = []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\[(\d+:\d+)-(\d+:\d+)\]\s*(.*)", line)
        if m: segs.append((to_sec(m.group(1)), to_sec(m.group(2)), m.group(3)))
    return segs


def parse_srt(path):
    segs, txt = [], open(path, encoding="utf-8", errors="ignore").read()
    for blk in re.split(r"\n\s*\n", txt.strip()):
        m = re.search(r"(\d+:\d+:\d+[,.]\d+)\s*-->\s*(\d+:\d+:\d+[,.]\d+)\s*\n(.*)", blk, re.S)
        if m:
            t = re.sub(r"<[^>]+>", "", m.group(3)).replace("\n", " ").strip()
            segs.append((to_sec(m.group(1)), to_sec(m.group(2)), t))
    return segs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="va_work")
    a = ap.parse_args()
    w = lambda n: os.path.join(a.work, n)

    man = json.load(open(w("manifest.json")))
    meta = man["metadata"]
    ocr = {f["time_sec"]: f for f in json.load(open(w("ocr.json")))["frames"]} if os.path.isfile(w("ocr.json")) else {}
    prof = json.load(open(w("audio_profile.json"))) if os.path.isfile(w("audio_profile.json")) else None
    speech, src = [], None
    if man.get("subtitles") and os.path.isfile(man["subtitles"]):
        speech, src = parse_srt(man["subtitles"]), "embedded subtitles"
    elif os.path.isfile(w("transcript.txt")):
        speech, src = parse_transcript(w("transcript.txt")), "speech-to-text"

    L = [f"# Video report: {meta['file']}", "",
         f"- Duration: {meta['duration']} | {meta['width']}x{meta['height']} | {meta['fps']} fps",
         f"- Audio track: {'yes' if meta['has_audio'] else 'no'}",
         f"- Speech source: {src or 'none (no transcript available)'}",
         f"- On-screen text (OCR): {'yes' if ocr else 'not run'}"]
    if prof:
        L.append(f"- Audio profile: mean {prof['mean_volume_db']} dB, {prof['silent_percent']}% silent, "
                 f"{len(prof['sound_segments'])} sound segment(s)")
    L += ["", "## Timeline (view each frame image, then read the text beside it)", ""]

    frames = man["frames"]
    for i, fr in enumerate(frames):
        t0 = fr["time_sec"]
        t1 = frames[i + 1]["time_sec"] if i + 1 < len(frames) else 1e9
        t0b = 0 if i == 0 else (frames[i - 1]["time_sec"] + t0) / 2
        t1b = 1e9 if i + 1 == len(frames) else (t0 + t1) / 2
        L.append(f"### {fr['time']}  —  `{fr['file']}`")
        o = ocr.get(t0)
        if o is not None:
            if o["text"]: L.append("**On-screen text:**\n```\n" + o["text"] + "\n```")
            elif o["same_as_previous"]: L.append("**On-screen text:** same as previous frame")
            else: L.append("**On-screen text:** none detected")
        said = [s for s in speech if s[1] > t0b and s[0] < t1b]
        if said:
            L.append("**Speech:**")
            L += [f"- [{int(s[0]//60):02d}:{int(s[0]%60):02d}] {s[2]}" for s in said]
        elif speech:
            L.append("**Speech:** none in this interval")
        if prof:
            tl = [p for p in prof["loudness_timeline"] if p["time_sec"] <= t0]
            if tl: L.append(f"**Audio level:** {tl[-1]['rms_db']} dB" + (" (near silence)" if tl[-1]["rms_db"] < -50 else ""))
        L.append("")

    open(w("report.md"), "w", encoding="utf-8").write("\n".join(L))
    print(f"Report -> {w('report.md')}")


if __name__ == "__main__":
    main()
