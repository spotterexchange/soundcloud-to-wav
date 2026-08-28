# sc2wav — SoundCloud → WAV

Download SoundCloud tracks, playlists, and user pages as **WAV** files — for
example, straight onto a USB drive. Use it two ways:

- 🖥️ **Web UI** — paste a link in your browser and click Download (`webapp.py`)
- ⌨️ **Command line** — for scripting and batch jobs (`sc2wav.py`)

Both are thin, friendly wrappers around two well-established tools:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — fetches the audio from SoundCloud
- **[ffmpeg](https://ffmpeg.org/)** — decodes it to WAV

> ⚠️ **Please only download audio you have the right to.** Many SoundCloud
> artists enable downloads or release under permissive licenses — respect their
> wishes and [SoundCloud's Terms of Use](https://soundcloud.com/terms-of-use).

---

## 1. Install

You need **Python 3.9+**, **ffmpeg**, and the Python dependency.

### a) Install ffmpeg

| OS | Command |
|----|---------|
| macOS (Homebrew) | `brew install ffmpeg` |
| Windows (winget) | `winget install Gyan.FFmpeg` |
| Windows (choco)  | `choco install ffmpeg` |
| Debian / Ubuntu  | `sudo apt install ffmpeg` |
| Fedora           | `sudo dnf install ffmpeg` |

Check it's on your PATH:

```bash
ffmpeg -version
```

If it isn't, you can point sc2wav at it directly with `--ffmpeg`.

### b) Install the Python dependency

```bash
pip install -r requirements.txt
```

(Optional but recommended — use a virtual environment:)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2. Use the web UI (easiest)

Start the server:

```bash
python webapp.py
```

It prints a local address (default <http://127.0.0.1:5000>). Open it in your
browser, paste a SoundCloud link, and click **Download**. The WAV lands in your
browser's Downloads folder — drag it onto your USB drive from there. A playlist
comes back as a single `.zip` of WAVs.

Options: `python webapp.py --port 8000` to change the port. The server binds to
localhost only and is intended to run on your own machine.

---

## 3. Use the command line

Basic — download a single track into the current folder:

```bash
python sc2wav.py https://soundcloud.com/artist/track-name
```

Download onto a USB drive (`-o` / `--output` sets the destination):

```bash
# macOS / Linux — USB usually mounts under /Volumes or /media
python sc2wav.py -o /Volumes/MY_USB/Music https://soundcloud.com/artist/track-name

# Windows — use the drive letter
python sc2wav.py -o D:\Music https://soundcloud.com/artist/track-name
```

Download a whole playlist / set or a user's tracks:

```bash
python sc2wav.py -o /Volumes/MY_USB/Music https://soundcloud.com/artist/sets/my-playlist
python sc2wav.py -o /Volumes/MY_USB/Music https://soundcloud.com/artist
```

Download many URLs from a file (one URL per line, `#` for comments):

```bash
python sc2wav.py -o D:\Music --batch tracks.txt
```

Skip tracks you already grabbed on future runs (keeps a record of track IDs):

```bash
python sc2wav.py -o /Volumes/MY_USB/Music --archive archive.txt https://soundcloud.com/artist
```

### Finding your USB path

- **Windows:** open *This PC* — the drive shows as a letter like `E:\`.
- **macOS:** drives mount under `/Volumes/` — run `ls /Volumes` to see the name.
- **Linux:** usually under `/media/<you>/<label>` or `/mnt/...` — run `lsblk` or `df -h`.

---

## 4. Command-line options

| Option | What it does |
|--------|--------------|
| `-o`, `--output DIR` | Where to save the WAV files (default: current folder) |
| `--batch FILE` | Read URLs from a text file, one per line |
| `--naming TEMPLATE` | Filename [output template](https://github.com/yt-dlp/yt-dlp#output-template) (default: `%(uploader)s - %(title)s.%(ext)s`) |
| `--archive FILE` | Record downloaded IDs so re-runs skip existing tracks |
| `--overwrite` | Re-download and overwrite existing files |
| `--ffmpeg PATH` | Path to ffmpeg if it isn't on your PATH |
| `-q`, `--quiet` | Suppress progress output |
| `-h`, `--help` | Show full help |

---

## Notes

- **WAV files are large** (uncompressed — roughly 10 MB per minute of audio).
  A full playlist can fill a small USB drive quickly. sc2wav warns you when the
  target has little free space.
- Filenames are made Windows/FAT-safe automatically so they work on typical USB
  drives.
- If a track in a playlist fails, sc2wav logs it and keeps going with the rest.
- yt-dlp changes often to keep up with SoundCloud. If downloads start failing,
  update it: `pip install -U yt-dlp`.

## License

MIT — see [LICENSE](LICENSE).
