#!/usr/bin/env python3
"""OCR on-screen text for each frame listed in manifest.json (uses the tesseract CLI).
Frames are re-extracted from the original video at full resolution for better accuracy."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile


def available_langs():
    r = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True)
    return set(l.strip() for l in r.stdout.splitlines()[1:] if l.strip())


def norm(t):
    return re.sub(r"\W+", " ", t.lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--work", default="va_work", help="dir containing manifest.json")
    ap.add_argument("--lang", default="ara+fra+eng",
                    help="tesseract languages; unavailable ones are dropped automatically")
    a = ap.parse_args()

    if not shutil.which("tesseract"):
        sys.exit("tesseract not found. Install it (apt install tesseract-ocr tesseract-ocr-ara tesseract-ocr-fra / "
                 "brew install tesseract). Continue without OCR and say so to the user.")

    have = available_langs()
    langs = [l for l in a.lang.split("+") if l in have] or ["eng"]
    missing = [l for l in a.lang.split("+") if l not in have]
    lang = "+".join(langs)

    mpath = os.path.join(a.work, "manifest.json")
    manifest = json.load(open(mpath))
    results, prev = [], ""
    tmp = tempfile.mkdtemp()
    for fr in manifest["frames"]:
        img = os.path.join(tmp, "f.png")
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", str(fr["time_sec"]),
                        "-i", a.video, "-frames:v", "1", "-vf", "scale='min(1920,iw)':-2,format=gray", img],
                       capture_output=True)
        text = ""
        if os.path.isfile(img):
            r = subprocess.run(["tesseract", img, "stdout", "-l", lang, "--psm", "11"],
                               capture_output=True, text=True)
            lines = [l.strip() for l in r.stdout.splitlines()]
            # drop noise: very short lines or lines with few letters/digits
            lines = [l for l in lines if len(l) >= 3 and sum(c.isalnum() for c in l) >= max(2, len(l) // 2)]
            text = "\n".join(lines)
        same = bool(text) and norm(text) == prev
        if text:
            prev = norm(text)
        results.append({"time": fr["time"], "time_sec": fr["time_sec"],
                        "text": "" if same else text, "same_as_previous": same})

    out = {"languages_used": lang, "languages_missing": missing, "frames": results}
    json.dump(out, open(os.path.join(a.work, "ocr.json"), "w"), indent=2, ensure_ascii=False)
    n = sum(1 for r in results if r["text"])
    print(f"OCR languages: {lang}" + (f" (missing: {','.join(missing)})" if missing else ""))
    print(f"Frames with new on-screen text: {n}/{len(results)} -> {os.path.join(a.work, 'ocr.json')}")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
