#!/usr/bin/env python3
"""sc2wav — download SoundCloud tracks and save them as WAV files.

Wraps yt-dlp (for fetching) and ffmpeg (for decoding to WAV) behind a small,
friendly command-line interface. Point it at a track, playlist, or user URL
and it writes ``Artist - Title.wav`` files into the folder you choose — for
example, a USB drive.

Only download audio you have the right to download. Many SoundCloud artists
enable downloads or release under permissive licenses; respect their wishes
and SoundCloud's Terms of Use.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:  # pragma: no cover - handled at runtime
    sys.stderr.write(
        "error: the 'yt-dlp' package is not installed.\n"
        "       install the requirements first:  pip install -r requirements.txt\n"
    )
    raise SystemExit(1)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def find_ffmpeg() -> str | None:
    """Return the path to an ffmpeg binary, or None if it isn't on PATH."""
    return shutil.which("ffmpeg")


def looks_like_soundcloud(url: str) -> bool:
    """Cheap sanity check so a typo'd URL fails fast with a clear message."""
    lowered = url.lower()
    return "soundcloud.com" in lowered or lowered.startswith("scsearch")


def human_readable(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}GB"


# --------------------------------------------------------------------------- #
# core
# --------------------------------------------------------------------------- #
def build_options(
    output_dir: Path,
    ffmpeg_location: str | None,
    naming: str,
    archive: Path | None,
    overwrite: bool,
    quiet: bool,
) -> dict:
    """Assemble the yt-dlp options dictionary."""
    outtmpl = str(output_dir / naming)

    postprocessors = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "wav",
        },
        # Best-effort metadata; WAV carries limited tags but this preserves
        # what it can and is harmless otherwise.
        {"key": "FFmpegMetadata"},
    ]

    opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": postprocessors,
        "ignoreerrors": True,          # keep going if one track in a set fails
        "noplaylist": False,           # allow playlists / user pages
        "quiet": quiet,
        "no_warnings": quiet,
        "overwrites": overwrite,
        "restrictfilenames": False,
        "windowsfilenames": True,      # keep names portable for USB/FAT drives
        "retries": 5,
        "fragment_retries": 5,
    }

    if ffmpeg_location:
        opts["ffmpeg_location"] = ffmpeg_location
    if archive is not None:
        # Records completed IDs so re-runs skip what you already have.
        opts["download_archive"] = str(archive)

    return opts


def download(urls: list[str], opts: dict) -> int:
    """Run the download. Returns a process-style exit code (0 == success)."""
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.download(urls)


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="sc2wav",
        description="Download SoundCloud tracks and save them as WAV files.",
        epilog=(
            "examples:\n"
            "  sc2wav https://soundcloud.com/artist/track\n"
            "  sc2wav -o /media/usb/music https://soundcloud.com/artist/sets/playlist\n"
            "  sc2wav -o D:\\Music --batch tracks.txt\n\n"
            "Only download audio you are permitted to. Respect artists and "
            "SoundCloud's Terms of Use."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="one or more SoundCloud URLs (track, playlist/set, or user page)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=".",
        help="output directory — e.g. your USB drive (default: current folder)",
    )
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="read URLs from a file, one per line (# starts a comment)",
    )
    parser.add_argument(
        "--naming",
        default="%(uploader)s - %(title)s.%(ext)s",
        help="yt-dlp output template (default: '%%(uploader)s - %%(title)s.%%(ext)s')",
    )
    parser.add_argument(
        "--archive",
        metavar="FILE",
        help="track downloaded IDs in FILE so re-runs skip existing tracks",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="re-download and overwrite files that already exist",
    )
    parser.add_argument(
        "--ffmpeg",
        metavar="PATH",
        help="path to the ffmpeg binary or its folder (if not on PATH)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="suppress yt-dlp progress output",
    )
    return parser.parse_args(argv)


def collect_urls(args: argparse.Namespace) -> list[str]:
    urls = list(args.urls)
    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.is_file():
            sys.stderr.write(f"error: batch file not found: {batch_path}\n")
            raise SystemExit(1)
        for line in batch_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    urls = collect_urls(args)

    if not urls:
        sys.stderr.write(
            "error: no URLs given. Pass a SoundCloud URL or use --batch FILE.\n"
            "       try 'sc2wav --help' for usage.\n"
        )
        return 1

    bad = [u for u in urls if not looks_like_soundcloud(u)]
    if bad:
        sys.stderr.write(
            "error: these do not look like SoundCloud URLs:\n"
            + "".join(f"  {u}\n" for u in bad)
        )
        return 1

    # Resolve ffmpeg, which is required to produce WAV files.
    ffmpeg_location = args.ffmpeg or find_ffmpeg()
    if not ffmpeg_location:
        sys.stderr.write(
            "error: ffmpeg was not found on your PATH.\n"
            "       WAV conversion needs ffmpeg. Install it and retry:\n"
            "         macOS:    brew install ffmpeg\n"
            "         Windows:  winget install Gyan.FFmpeg\n"
            "         Debian:   sudo apt install ffmpeg\n"
            "       or pass its location with --ffmpeg PATH\n"
        )
        return 1

    output_dir = Path(args.output).expanduser()
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        sys.stderr.write(f"error: cannot create output directory {output_dir}: {exc}\n")
        return 1
    if not os.access(output_dir, os.W_OK):
        sys.stderr.write(f"error: output directory is not writable: {output_dir}\n")
        return 1

    # Warn about likely-tiny free space on the target (WAV is large & uncompressed).
    try:
        free = shutil.disk_usage(output_dir).free
        if free < 200 * 1024 * 1024:  # < 200 MB
            sys.stderr.write(
                f"warning: only {human_readable(free)} free on {output_dir} — "
                "WAV files are large and uncompressed.\n"
            )
    except OSError:
        pass

    archive = Path(args.archive).expanduser() if args.archive else None

    opts = build_options(
        output_dir=output_dir,
        ffmpeg_location=args.ffmpeg,  # only override when user supplied one
        naming=args.naming,
        archive=archive,
        overwrite=args.overwrite,
        quiet=args.quiet,
    )

    print(f"Downloading {len(urls)} item(s) as WAV into: {output_dir}")
    result = download(urls, opts)

    if result == 0:
        print("Done.")
    else:
        sys.stderr.write(
            "Finished with some errors — see the log above. "
            "Tracks that failed were skipped.\n"
        )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
