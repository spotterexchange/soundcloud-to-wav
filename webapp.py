#!/usr/bin/env python3
"""sc2wav web UI — paste a SoundCloud link in your browser, get a WAV back.

Runs a small local web server. Open the page it prints, paste a SoundCloud
track (or playlist) URL, and click Download; the server fetches the audio with
yt-dlp, converts it to WAV with ffmpeg, and streams the file back to your
browser's downloads. A playlist comes back as a single .zip of WAVs.

This is meant to run on your own machine and binds to localhost only.

Only download audio you have the right to. Respect artists and SoundCloud's
Terms of Use.
"""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    from flask import Flask, after_this_request, jsonify, render_template, request, send_file
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "error: Flask is not installed.\n"
        "       install the requirements first:  pip install -r requirements.txt\n"
    )
    raise SystemExit(1)

# Reuse the converter logic from the CLI module.
from sc2wav import build_options, find_ffmpeg, looks_like_soundcloud

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "error: yt-dlp is not installed.\n"
        "       install the requirements first:  pip install -r requirements.txt\n"
    )
    raise SystemExit(1)


app = Flask(__name__)
# WAV files can be large; allow a generous response. (This limits uploads, not
# downloads, but keep it explicit.)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


@app.get("/")
def index():
    ffmpeg_ok = find_ffmpeg() is not None
    return render_template("index.html", ffmpeg_ok=ffmpeg_ok)


@app.post("/download")
def download():
    data = request.get_json(silent=True) or request.form
    url = (data.get("url") or "").strip()

    if not url:
        return jsonify(error="Please paste a SoundCloud link."), 400
    if not looks_like_soundcloud(url):
        return jsonify(error="That doesn't look like a SoundCloud link."), 400

    ffmpeg_location = find_ffmpeg()
    if not ffmpeg_location:
        return (
            jsonify(
                error=(
                    "ffmpeg was not found on this machine. WAV conversion needs it. "
                    "Install ffmpeg (e.g. 'brew install ffmpeg', "
                    "'winget install Gyan.FFmpeg', or 'sudo apt install ffmpeg') "
                    "and restart this app."
                )
            ),
            500,
        )

    workdir = Path(tempfile.mkdtemp(prefix="sc2wav_"))

    @after_this_request
    def cleanup(response):
        shutil.rmtree(workdir, ignore_errors=True)
        return response

    opts = build_options(
        output_dir=workdir,
        ffmpeg_location=None,          # ffmpeg is on PATH; found above
        naming="%(uploader)s - %(title)s.%(ext)s",
        archive=None,
        overwrite=True,
        quiet=True,
    )
    # For the single-shot UI we want real errors surfaced, not swallowed.
    opts["ignoreerrors"] = False

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        msg = str(exc)
        # Trim yt-dlp's "please report this issue" boilerplate for readability.
        msg = msg.split(";")[0].replace("ERROR:", "").strip()
        return jsonify(error=f"Download failed: {msg}"), 502
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify(error=f"Unexpected error: {exc}"), 500

    wavs = sorted(workdir.glob("*.wav"))
    if not wavs:
        return jsonify(error="No audio was produced. The track may be private or unavailable."), 502

    if len(wavs) == 1:
        wav = wavs[0]
        return send_file(
            wav,
            mimetype="audio/wav",
            as_attachment=True,
            download_name=wav.name,
        )

    # Multiple tracks (a playlist/set) -> zip them up in memory.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as zf:
        for wav in wavs:
            zf.write(wav, arcname=wav.name)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="soundcloud-wav.zip",
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the sc2wav web UI.")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="port (default: 5000)")
    parser.add_argument("--debug", action="store_true", help="enable Flask debug mode")
    args = parser.parse_args()

    if not find_ffmpeg():
        sys.stderr.write(
            "warning: ffmpeg was not found on your PATH. The UI will load, but "
            "downloads will fail until ffmpeg is installed.\n"
        )

    url = f"http://{args.host}:{args.port}"
    print(f"sc2wav web UI running at  {url}")
    print("Open that address in your browser. Press Ctrl+C to stop.")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
