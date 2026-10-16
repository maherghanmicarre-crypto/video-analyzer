#!/usr/bin/env python3
"""Extract metadata, key frames, audio and subtitles from a video using ffmpeg."""
import argparse, json, os, re, shutil, subprocess, sys


def run(cmd, check=True):
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def fmt(t):
    t = int(round(t))
    h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def probe(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", path])
    data = json.loads(r.stdout)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        sys.exit("No video stream found in this file.")
    fps = 0.0
    try:
        n, d = v.get("avg_frame_rate", "0/1").split("/")
        fps = float(n) / float(d) if float(d) else 0.0
    except Exception:
        pass
    dur = float(data["format"].get("duration") or v.get("duration") or 0)
    return {
        "file": os.path.basename(path),
        "duration_sec": round(dur, 2),
        "duration": fmt(dur),
        "width": v.get("width"), "height": v.get("height"),
        "fps": round(fps, 2),
        "video_codec": v.get("codec_name"),
        "has_audio": any(s["codec_type"] == "audio" for s in data["streams"]),
        "subtitle_tracks": sum(1 for s in data["streams"] if s["codec_type"] == "subtitle"),
    }


def scene_times(path, start, end, threshold):
    cmd = ["ffmpeg", "-hide_banner", "-nostats"]
    if start: cmd += ["-ss", str(start)]
    if end: cmd += ["-to", str(end)]
    cmd += ["-i", path, "-vf", f"select='gt(scene,{threshold})',showinfo",
            "-an", "-f", "null", "-"]
    r = run(cmd, check=False)
    ts = [float(m) + (start or 0) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    return sorted(set(round(t, 2) for t in ts))


def pick_times(duration, start, end, n, mode, path, threshold):
    lo, hi = start or 0.0, end or duration
    span = max(hi - lo, 0.01)
    uniform = [lo + span * (i + 0.5) / n for i in range(n)]
    if mode == "uniform":
        return uniform
    scenes = [t for t in scene_times(path, start, end, threshold) if lo <= t < hi]
    if len(scenes) > n:  # subsample evenly
        step = len(scenes) / n
        scenes = [scenes[int(i * step)] for i in range(n)]
    times = list(scenes)
    # top up with uniform frames far from existing picks
    min_gap = span / (n * 2)
    while len(times) < n and min_gap > 0.01:
        for u in uniform:
            if len(times) >= n:
                break
            if all(abs(u - t) > min_gap for t in times):
                times.append(u)
        min_gap /= 2
    return sorted(times)[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", default="va_work")
    ap.add_argument("--max-frames", type=int, default=24)
    ap.add_argument("--mode", choices=["hybrid", "scene", "uniform"], default="hybrid")
    ap.add_argument("--scene-threshold", type=float, default=0.3)
    ap.add_argument("--start", type=float, default=None)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--width", type=int, default=768)
    a = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found. Install ffmpeg (e.g. apt install ffmpeg / brew install ffmpeg).")
    if not os.path.isfile(a.video):
        sys.exit(f"File not found: {a.video}")

    meta = probe(a.video)
    frames_dir = os.path.join(a.out, "frames")
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir, exist_ok=True)

    mode = "hybrid" if a.mode == "scene" else a.mode
    times = pick_times(meta["duration_sec"], a.start, a.end, a.max_frames,
                       mode, a.video, a.scene_threshold)

    frames = []
    for i, t in enumerate(times, 1):
        name = f"frame_{i:03d}_t{int(t // 60):02d}m{int(t % 60):02d}s.jpg"
        p = os.path.join(frames_dir, name)
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t:.2f}",
             "-i", a.video, "-frames:v", "1", "-vf", f"scale={a.width}:-2", "-q:v", "3", p],
            check=False)
        if os.path.isfile(p):
            frames.append({"file": p, "time_sec": round(t, 2), "time": fmt(t)})

    # audio
    audio_path = None
    if meta["has_audio"]:
        audio_path = os.path.join(a.out, "audio.wav")
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
        if a.start: cmd += ["-ss", str(a.start)]
        if a.end: cmd += ["-to", str(a.end)]
        cmd += ["-i", a.video, "-vn", "-ac", "1", "-ar", "16000", audio_path]
        run(cmd, check=False)
        if not os.path.isfile(audio_path):
            audio_path = None

    # embedded subtitles
    subs_path = None
    if meta["subtitle_tracks"]:
        subs_path = os.path.join(a.out, "subtitles.srt")
        r = run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", a.video,
                 "-map", "0:s:0", subs_path], check=False)
        if r.returncode != 0 or not os.path.isfile(subs_path):
            subs_path = None

    manifest = {"metadata": meta, "range": {"start": a.start, "end": a.end},
                "frames": frames, "audio": audio_path, "subtitles": subs_path}
    with open(os.path.join(a.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Video: {meta['file']} | {meta['duration']} | {meta['width']}x{meta['height']} | {meta['fps']} fps")
    print(f"Frames: {len(frames)} -> {frames_dir}")
    print(f"Audio: {audio_path or ('none' if not meta['has_audio'] else 'extraction failed')}")
    print(f"Subtitles: {subs_path or 'none'}")
    print(f"Manifest: {os.path.join(a.out, 'manifest.json')}")


if __name__ == "__main__":
    main()
