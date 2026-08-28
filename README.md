# sc2wav — SoundCloud → WAV

Download SoundCloud tracks, playlists, and user pages as **WAV** files.

### 👉 Simplest way (no terminal, no commands)

You need **[Python 3.9+](https://www.python.org/downloads/)** installed once
(on Windows, tick *"Add Python to PATH"* during install). Then just **double-click**:

- **macOS / Linux:** `Start sc2wav (Mac-Linux).command`
- **Windows:** `Start sc2wav (Windows).bat`

The first run sets everything up (about a minute); after that it's quick. It
opens a page in your browser — paste a SoundCloud link and click **Download**.

**Saving to your USB:** in Chrome or Edge, click **📁 Save to my USB / a folder…**
and pick your USB drive — WAVs are written straight there. In other browsers the
button doesn't appear and files go to your Downloads folder to drag over (or turn
on your browser's *"Ask where to save each file"* setting to choose the USB each
time). Close the window to stop.

> On macOS, the first time you may need to right-click the `.command` file →
> **Open** to get past the security prompt.

### 👉 All in your browser — GitHub Codespace (nothing installed locally)

Prefer to run it entirely in the cloud? A [Codespace](https://github.com/features/codespaces)
runs this repo on GitHub's servers, in your browser — no Python or anything else
on your own machine.

1. On this repo's GitHub page: **Code ▾ → Codespaces → Create codespace on
   `<branch>`**.
2. Wait for it to build (it installs everything automatically — about a minute).
3. In the Terminal at the bottom, run:
   ```bash
   python webapp.py
   ```
4. A prompt pops up — click **Open in Browser** (or use the **PORTS** tab, port
   5000). Paste a SoundCloud link and click **Download**. In Chrome/Edge you can
   click **📁 Save to my USB / a folder…** to write straight to your USB;
   otherwise the WAV saves to your Downloads folder to drag over.

The download reaches your own computer — including the folder/USB you pick —
because the page runs in your browser, even though the work happens in the cloud. Codespaces include a
[free monthly quota](https://docs.github.com/billing/managing-billing-for-github-codespaces/about-billing-for-github-codespaces);
stop the Codespace when you're done so it doesn't use hours.

Other ways to use it — a [hosted web app](#2-host-it-on-the-web-no-local-machine-needed),
the [command line](#5-command-line-options) — are covered below.

Under the hood it wraps two well-established tools:
**[yt-dlp](https://github.com/yt-dlp/yt-dlp)** (fetches the audio) and
**[ffmpeg](https://ffmpeg.org/)** (decodes it to WAV — installed automatically).

> ⚠️ **Please only download audio you have the right to.** Many SoundCloud
> artists enable downloads or release under permissive licenses — respect their
> wishes and [SoundCloud's Terms of Use](https://soundcloud.com/terms-of-use).

---

## 1. Install

You need **Python 3.9+**. Then install the dependencies:

```bash
pip install -r requirements.txt
```

(Optional but recommended — use a virtual environment:)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**That's it — ffmpeg is handled for you.** A static ffmpeg build ships with the
`imageio-ffmpeg` dependency and is used automatically, so there's no separate
install step.

<details>
<summary>Optional: use a system ffmpeg instead</summary>

If you'd rather use a system ffmpeg (slightly faster startup), install it and
it'll be preferred automatically:

| OS | Command |
|----|---------|
| macOS (Homebrew) | `brew install ffmpeg` |
| Windows (winget) | `winget install Gyan.FFmpeg` |
| Debian / Ubuntu  | `sudo apt install ffmpeg` |
| Fedora           | `sudo dnf install ffmpeg` |

You can also point sc2wav at a specific binary with `--ffmpeg PATH`.
</details>

---

## 2. Host it on the web (no local machine needed)

Deploy once and get a URL you can open from anywhere — the server has ffmpeg
built in, so there's nothing to install or run locally.

### Easiest: Render (free tier, deploys from GitHub)

1. Push this repo to GitHub (already done if you're reading this there).
2. Go to [Render](https://render.com) → **New → Blueprint**.
3. Connect this repository. Render reads [`render.yaml`](render.yaml) and builds
   the [`Dockerfile`](Dockerfile) automatically.
4. *(Recommended)* Set an environment variable **`SC2WAV_ACCESS_CODE`** to any
   password, so only you can use the site. Leave it blank for open public access.
5. Click **Apply**. In a few minutes you get a URL like
   `https://sc2wav.onrender.com` — open it, paste a link, download WAVs.

> On the free tier the app sleeps after inactivity and takes ~30s to wake on the
> first request. Very long playlists may exceed the platform's request timeout.

### Any Docker host (Fly.io, Railway, a VPS, etc.)

The included [`Dockerfile`](Dockerfile) runs anywhere containers do:

```bash
docker build -t sc2wav .
docker run -p 8000:8000 -e SC2WAV_ACCESS_CODE=yourpassword sc2wav
# then open http://localhost:8000
```

On Fly.io: `fly launch` (it detects the Dockerfile), then
`fly secrets set SC2WAV_ACCESS_CODE=yourpassword`.
On Railway: **New → Deploy from GitHub repo** — it builds the Dockerfile; add the
same variable under **Variables**.

**Access code:** when `SC2WAV_ACCESS_CODE` is set, the site asks for a password
(any username, that value as the password). Since a hosted downloader is a public
URL, setting one is strongly recommended.

**Health check:** `GET /healthz` returns `{"status":"ok"}` for uptime monitors.

---

## 3. Or run the web UI locally

Prefer to keep it on your own machine? Start the server:

```bash
python webapp.py
```

It prints a local address (default <http://127.0.0.1:5000>). Open it, paste a
SoundCloud link, and click **Download**. A playlist comes back as a single
`.zip` of WAVs. Change the port with `python webapp.py --port 8000`.

---

## 4. Use the command line

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

## 5. Command-line options

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
