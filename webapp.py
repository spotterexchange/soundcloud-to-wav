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

import hmac
import io
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    from flask import (
        Flask,
        Response,
        after_this_request,
        jsonify,
        render_template,
        request,
        send_file,
    )
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

# Optional password protection for a publicly hosted instance. Set the
# SC2WAV_ACCESS_CODE environment variable and the site prompts for it (HTTP
# Basic auth — any username, that value as the password). Leave it unset for
# open access.
ACCESS_CODE = os.environ.get("SC2WAV_ACCESS_CODE", "").strip()


@app.before_request
def require_access_code():
    if not ACCESS_CODE or request.path == "/healthz":
        return None
    auth = request.authorization
    if auth is None or not hmac.compare_digest(auth.password or "", ACCESS_CODE):
        return Response(
            "Authentication required.",
            401,
            {"WWW-Authenticate": 'Basic realm="sc2wav"'},
        )
    return None


@app.get("/healthz")
def healthz():
    """Lightweight health check for hosting platforms."""
    return jsonify(status="ok", ffmpeg=find_ffmpeg() is not None)


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
        ffmpeg_location=ffmpeg_location,   # PATH or the bundled static binary
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
        raw = str(exc)
        low = raw.lower()
        if "drm" in low:
            friendly = (
                "This track is DRM-protected (a licensed / SoundCloud Go+ track), "
                "so it can't be downloaded. Try a track the artist has made freely "
                "available."
            )
        elif "not available" in low or "private" in low or "404" in low:
            friendly = "This track isn't available to download — it may be private or removed."
        elif "requested format" in low or "no video formats" in low:
            friendly = "No downloadable audio was found for that link."
        else:
            # Trim yt-dlp's "please report this issue" boilerplate for readability.
            friendly = "Download failed: " + raw.split(";")[0].replace("ERROR:", "").strip()
        return jsonify(error=friendly), 502
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
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 5000)),
        help="port (default: $PORT or 5000)",
    )
    parser.add_argument("--debug", action="store_true", help="enable Flask debug mode")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="don't open a browser window automatically",
    )
    args = parser.parse_args()

    if not find_ffmpeg():
        sys.stderr.write(
            "warning: ffmpeg was not found. Run 'pip install -r requirements.txt' "
            "so the bundled ffmpeg is available, or install ffmpeg system-wide.\n"
        )

    # In a GitHub Codespace the app must bind to all interfaces so the port can
    # be forwarded, there's no local browser to open, and the public address is
    # the forwarded URL rather than localhost.
    in_codespace = os.environ.get("CODESPACES") == "true"
    if in_codespace and args.host == "127.0.0.1":
        args.host = "0.0.0.0"

    if in_codespace:
        name = os.environ.get("CODESPACE_NAME", "")
        domain = os.environ.get(
            "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev"
        )
        forwarded = f"https://{name}-{args.port}.{domain}" if name else None
        print("sc2wav is running in this Codespace.")
        if forwarded:
            print(f"Open this URL in your browser:  {forwarded}")
        print(
            "If it doesn't open, use the PORTS tab, find port "
            f"{args.port}, and click the globe / 'Open in Browser'."
        )
        print("Press Ctrl+C here to stop.")
    else:
        url = f"http://{args.host}:{args.port}"
        print(f"sc2wav web UI running at  {url}")
        print("Your browser should open automatically. Press Ctrl+C here to stop.")

        # Pop the page open once the server is up, unless suppressed or the
        # Flask debug reloader is spawning the parent process.
        if not args.no_browser and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            import threading
            import webbrowser

            threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
