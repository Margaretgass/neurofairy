# Stage 2 — Voice capture, desktop Fairy, and the shared flower timer

> **By the end of this stage** you can optionally dictate a brain dump with a free,
> local `whisper.cpp` model; a small Fairy floats above your Mac desktop; clicking her
> opens a NeuroFairy-styled popup with your timer, to-do list, and working AI chat; and
> the cottage and desktop popup control the same persistent flower timer.

**Sessions:** 9 · **Time:** ~8–10 weeks at 8–10 hours per week

This replaces the old Stage 2 timer plan **and absorbs the useful Python desktop work from
the old Stage 3**. Do not build the old Swift prototype. Do not follow the old Stage 3 in
parallel with this document.

---

## What already works

Before adding anything, be precise about the current repository:

| Part | Current truth |
|---|---|
| Cottage UI | `uiux/ui/` is a working browser prototype served by FastAPI |
| AI chat | `POST /api/chat` calls the local Ollama model through LangChain |
| Task service | Python task functions, SQLite storage, tests, and an MCP server exist |
| Brain dump | Typing works; microphone capture and transcription do not exist yet |
| Flower timer | The browser prototype works against `localStorage`; it is not shared with Python or the desktop |
| Desktop Fairy | The UI design exists, but there is no Python desktop implementation yet |
| Database | `~/.fairy/fairy.db` stores real tasks |

That means this stage is an **integration stage**, not a restart.

---

## What you'll learn

| Concept | Where |
|---|---|
| Building and running a local C++ AI tool | Session 1 |
| Calling a command-line program safely from Python | Session 2 |
| Browser microphone APIs, uploads, and editable transcripts | Session 3 |
| PySide6 event loops, transparent windows, and macOS activation policy | Session 4 |
| Embedding a web interface in a native desktop popup | Session 5 |
| Sharing task and chat services through HTTP APIs | Session 6 |
| Pure functions, frozen dataclasses, and state machines | Session 7 |
| SQLite transactions and one authoritative timer | Session 8 |
| Keeping two user interfaces synchronized | Session 9 |

---

## The build order

Build these in this exact order:

1. Optional local voice-to-text for brain dumps
2. Floating desktop Fairy and popup shell
3. Real popup tasks and AI chat
4. Pure Python flower rules
5. One persistent focus service
6. Cottage and popup connected to that service

Do not start by wiring the timer into both interfaces. First prove each boundary separately.
That keeps failures small enough to understand.

---

## The architecture you are building

```text
                         ┌──────────────────────────┐
                         │  Local Ollama model      │
                         │  qwen2.5:3b              │
                         └────────────▲─────────────┘
                                      │ LangChain
┌────────────────────┐      HTTP      │      ┌────────────────────────┐
│ Cottage browser UI │◄───────────────┼─────►│ FastAPI local service  │
│ uiux/ui/            │                │      │ src/fairy/web_app.py   │
└─────────┬──────────┘                │      └───────────┬────────────┘
          │                           │                  │
          │ /api/transcriptions      │                  ├── tasks service
          │ /api/tasks               │                  ├── chat service
          │ /api/chat                │                  ├── focus service
          │ /api/focus               │                  └── transcription service
          │                           │                         │
┌─────────▼──────────┐      HTTP      │                         ▼
│ PySide6 Fairy      │◄───────────────┘              ┌────────────────────┐
│ + web popup        │                               │ whisper.cpp CLI    │
└─────────┬──────────┘                               │ local base.en model│
          │                                          └────────────────────┘
          │
          └──────────────────────────────┐
                                         ▼
                              ┌──────────────────────┐
                              │ ~/.fairy/fairy.db   │
                              │ tasks · focus ·     │
                              │ garden              │
                              └──────────────────────┘
```

### One rule for shared state

> The cottage and desktop popup never write timer state independently.
> They send commands to FastAPI, and FastAPI changes one SQLite-backed timer.

Both interfaces may calculate a smooth display countdown between server refreshes. Only the
server is allowed to award focus credit, change phases, or add a flower.

### Sources of truth

| Concern | Source of truth |
|---|---|
| Visual language | `uiux/specs/DESIGN.md` |
| Flower behavior | `uiux/specs/bloom-timer-v1.md` and `uiux/ui/bloom-engine.js` |
| Existing browser screens | `uiux/ui/` |
| Tasks | `src/fairy/servers/tasks.py` and SQLite |
| AI reply | `src/fairy/neurofairy_chat.py` |
| Transcription | local `whisper.cpp` through `src/fairy/transcription.py` |
| Shared focus state | `src/fairy/focus.py` and SQLite |

---

## Non-negotiable behavior

### Voice privacy

- Voice is optional. Typing must always continue to work.
- Recording starts only after the user presses the microphone button.
- The UI clearly shows **Recording**, **Transcribing**, **Ready**, or **Error**.
- The transcript is inserted into the text box for editing.
- Transcription never submits, saves, or sends the text automatically.
- Temporary audio is deleted after success or failure.
- No audio or transcript is sent to OpenAI or another cloud transcription service.
- The first setup downloads a local model; after that, transcription works offline.

### Desktop Fairy

- Use Python and PySide6. Do not use the old Swift prototype.
- Use `uiux/assets/fairy-full.png`; do not copy art from the old repository.
- Fairy is approximately 88–140 logical pixels tall.
- Fairy stays on top, is draggable, and does not steal keyboard focus.
- Under 5 pixels of pointer movement counts as a click; over 5 counts as a drag.
- Hover waits briefly, then shows only the next task and shared remaining time.
- Click opens the popup. Closing the popup does not pause focus or exit Fairy.
- Saved position is clamped onto an available monitor after display changes.

### Flower timer

- One flower is exactly four completed 25-minute focus blocks.
- Three required 5-minute breaks separate those blocks.
- Short sessions contribute to the same plant.
- Break and paused time give no focus credit.
- A late tick advances at most one phase.
- A backwards clock gives no credit.
- One plant can be awarded once, even if the UI refreshes repeatedly.
- The cottage and popup always show the same plant and phase.

---

## Before Session 1 — protect your current work

The old guide starts every session with `git pull`. That is unsafe when files are staged or
modified. Start with inspection instead:

```bash
cd ~/code/fairy
git status --short --branch
```

If the output shows modified or staged files, stop and decide whether to commit or stash
them before pulling. Never use `git reset --hard` to make the warning disappear.

When the tree is clean:

```bash
cd ~/code/fairy
git pull --ff-only
uv sync
```

`--ff-only` refuses to invent a merge commit. If it fails, read the message before doing
anything else.

### Current verification baseline

When this roadmap was written, the existing repository had this baseline:

```text
pytest: 8 passed
ruff format --check: 21 files already formatted
ruff check: 2 pre-existing E501 line-length findings
```

The existing Ruff findings are in `src/fairy/prompts.py` and `src/fairy/web_app.py`. They
are not caused by Stage 2. Early sessions therefore run focused Ruff checks on the files
they change. Before the final whole-repository check, wrap those two existing long lines
without changing their text or behavior.

---

## Session 1 — Install and prove `whisper.cpp`

### ▶ Start this session

```bash
cd ~/code/fairy
git status --short --branch
```

**Goal:** prove local transcription works from the terminal before connecting it to Python
or the UI.

`whisper.cpp` is a native local implementation of Whisper. Its official quick start builds
`whisper-cli` with CMake and downloads a GGML model. The CLI expects supported audio input;
converting recordings to 16-bit, 16 kHz, mono WAV gives the most predictable boundary.

Official references:

- [`whisper.cpp` quick start](https://github.com/ggml-org/whisper.cpp/blob/master/README.md)
- [GGML model list and sizes](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md)
- [`whisper-cli` options](https://github.com/ggml-org/whisper.cpp/blob/master/examples/cli/README.md)

### Install the build and audio tools

```bash
brew install cmake ffmpeg
```

Check them:

```bash
cmake --version
ffmpeg -version
```

### Build outside the repository

Keep third-party source, binaries, and model files out of Git:

```bash
mkdir -p ~/.fairy
git clone https://github.com/ggml-org/whisper.cpp.git ~/.fairy/whisper.cpp
cmake -S ~/.fairy/whisper.cpp -B ~/.fairy/whisper.cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build ~/.fairy/whisper.cpp/build --config Release -j
```

Download the English `base.en` model:

```bash
mkdir -p ~/.fairy/models
sh ~/.fairy/whisper.cpp/models/download-ggml-model.sh base.en ~/.fairy/models
```

`base.en` is the Stage 2 default: it is much smaller than `small.en` and fast enough for
short brain dumps. Accuracy can be compared with `small.en` later without changing Python
or JavaScript.

### ✔ Check yourself

```bash
~/.fairy/whisper.cpp/build/bin/whisper-cli \
  -m ~/.fairy/models/ggml-base.en.bin \
  -f ~/.fairy/whisper.cpp/samples/jfk.wav \
  -nt -np
```

### Expected output

You should see an English transcript of the sample speech. Diagnostic model-loading lines
may appear on stderr; the transcript is the important part.

Then verify the files:

```bash
test -x ~/.fairy/whisper.cpp/build/bin/whisper-cli && echo "CLI ready"
test -f ~/.fairy/models/ggml-base.en.bin && echo "Model ready"
```

Expected:

```text
CLI ready
Model ready
```

### ⚠ If it breaks

| Error | Cause and next check |
|---|---|
| `brew: command not found` | Install Homebrew first, then reopen Terminal |
| `cmake: command not found` | `brew install cmake` did not finish or the shell needs reopening |
| `model not found` | Confirm the exact file with `ls ~/.fairy/models/` |
| `failed to open audio file` | Use the supplied `samples/jfk.wav` exactly as shown |
| Transcription is slow | Confirm `uname -m` prints `arm64`; optimize only after correctness |

### Full-file checkpoint

No Fairy repository file changes in this session. The complete external result is:

```text
~/.fairy/
├── models/
│   └── ggml-base.en.bin
└── whisper.cpp/
    └── build/bin/whisper-cli
```

### ■ Finish this session

Do not commit `whisper.cpp`, its build directory, or the model. They intentionally live
outside the repository.

---

## Session 2 — Put a safe Python boundary around `whisper.cpp`

### ▶ Start this session

```bash
cd ~/code/fairy
git status --short --branch
uv sync
```

**Goal:** turn an audio file into editable text through one tested Python function.

### Files

```text
Create: src/fairy/transcription.py
Create: tests/test_transcription.py
```

### Interface

```python
def transcribe_audio(
    source_path: Path,
    config: WhisperCppConfig | None = None,
) -> str:
    """Convert local audio to WAV, transcribe it locally, and return clean text."""
```

`WhisperCppConfig` contains:

```python
cli_path: Path
model_path: Path
ffmpeg_path: str = "ffmpeg"
language: str = "en"
```

Defaults:

```text
CLI:   ~/.fairy/whisper.cpp/build/bin/whisper-cli
Model: ~/.fairy/models/ggml-base.en.bin
```

Environment overrides:

```text
FAIRY_WHISPER_CLI
FAIRY_WHISPER_MODEL
FAIRY_FFMPEG
```

### Required implementation behavior

1. Reject a missing audio file before starting a subprocess.
2. Reject a missing CLI or model with a specific setup message.
3. Create a private temporary directory.
4. Run `ffmpeg` with an argument list—not `shell=True`—to produce PCM 16-bit, 16 kHz,
   mono WAV.
5. Run `whisper-cli` with `-nt -np -otxt -of`.
6. Read the generated `.txt` file.
7. Normalize repeated whitespace while preserving punctuation.
8. Reject an empty transcript with a friendly error.
9. Let the temporary directory delete both WAV and transcript in success and error paths.
10. Never log raw audio or transcript text.

Expected command shape:

```python
[
    str(config.cli_path),
    "-m", str(config.model_path),
    "-f", str(wav_path),
    "-l", config.language,
    "-nt", "-np", "-otxt",
    "-of", str(output_prefix),
]
```

### Tests to write first

`tests/test_transcription.py` must prove:

- the converter receives `-ar 16000 -ac 1 -c:a pcm_s16le`;
- the Whisper command contains separate arguments and never uses a shell;
- surrounding and repeated whitespace is cleaned;
- missing CLI gives `TranscriptionUnavailable`;
- missing model gives `TranscriptionUnavailable`;
- missing audio gives `FileNotFoundError`;
- an empty transcript gives `TranscriptionFailed`;
- tests use a fake process runner and never need a microphone or model.

### ✔ Check yourself

```bash
cd ~/code/fairy
uv run pytest tests/test_transcription.py -v
```

Expected:

```text
8 passed
```

Run one real transcription:

```bash
cd ~/code/fairy
uv run python -c "
from pathlib import Path
from fairy.transcription import transcribe_audio
print(transcribe_audio(Path.home() / '.fairy/whisper.cpp/samples/jfk.wav'))
"
```

### Expected output

An English sentence from the sample file, with no timestamp prefixes.

### ⚠ If it breaks

| Error | Cause |
|---|---|
| `TranscriptionUnavailable: whisper-cli is not installed` | Session 1 binary path is wrong |
| `TranscriptionUnavailable: model is not installed` | Model download is missing or named differently |
| `FileNotFoundError: ffmpeg` | Install `ffmpeg` and reopen the terminal |
| `.txt` output missing | Check `-otxt` and that `-of` has no extension |
| Tests invoke real Whisper | The process runner was not injected at the boundary |

### Full-file checkpoint

At the end of this session, read both files from their first line to their last line:

```bash
sed -n '1,260p' src/fairy/transcription.py
sed -n '1,320p' tests/test_transcription.py
```

There must be no `TODO`, `pass`, `shell=True`, API key, network upload, or microphone call
in either file.

### ■ Finish this session

```bash
cd ~/code/fairy
uv run ruff check src/fairy/transcription.py tests/test_transcription.py
uv run ruff format --check src/fairy/transcription.py tests/test_transcription.py
uv run pytest tests/test_transcription.py
git diff --check
```

Commit only these files:

```bash
git add src/fairy/transcription.py tests/test_transcription.py
git commit -m "feat: add local whisper cpp transcription service"
```

---

## Session 3 — Add optional voice to the brain dump

### ▶ Start this session

```bash
cd ~/code/fairy
git status --short --branch
uv sync
```

**Goal:** press a microphone, speak, stop, edit the transcript, and decide whether to save
or send it.

### Files

```text
Modify: pyproject.toml
Modify: src/fairy/web_app.py
Modify: uiux/ui/index.html
Create: uiux/ui/voice-capture.js
Create: uiux/ui/voice-capture.css
Create: tests/test_transcription_api.py
```

Add multipart upload support:

```bash
cd ~/code/fairy
uv add python-multipart
```

### API contract

```http
POST /api/transcriptions
Content-Type: multipart/form-data
field: audio
```

Success:

```json
{"transcript": "Call the dentist and email my professor."}
```

Failures:

| Status | Meaning |
|---|---|
| `400` | Unsupported or empty audio |
| `413` | Upload is larger than 20 MiB |
| `503` | `whisper.cpp`, model, or `ffmpeg` is unavailable |
| `422` | FastAPI did not receive an `audio` field |
| `500` | Transcription failed unexpectedly |

The endpoint must:

- accept only known audio content types;
- read at most 20 MiB plus one byte;
- save with a server-created temporary name;
- call `transcribe_audio` in a worker thread;
- delete the upload in a `finally` block;
- return a generic client error without leaking subprocess stderr.

### Browser behavior

Load `voice-capture.css` and `voice-capture.js` after the existing NeuroFairy files.
`voice-capture.js` progressively enhances text composers; it does not replace typing.

The microphone control follows this state machine:

```text
idle ──press──► recording ──press──► transcribing ──success──► ready
  ▲                 │                       │
  └──── error ◄─────┴───────────────────────┘
```

Rules:

- First press requests microphone permission.
- Second press stops recording.
- Browser sends the Blob only to `/api/transcriptions` on `127.0.0.1`.
- Returned text is inserted at the cursor.
- Existing typed text is preserved.
- The form is not submitted.
- Microphone tracks stop before transcription begins.
- A rejected permission leaves the text field usable and focused.
- Only one recorder can run at a time.
- An `aria-live="polite"` status announces state changes.

macOS requires a microphone usage description once Fairy is packaged as an application.
Apple documents this requirement under
[`NSMicrophoneUsageDescription`](https://developer.apple.com/documentation/BundleResources/Information-Property-List/NSMicrophoneUsageDescription).
During this browser-first session, the browser owns the permission prompt.

### Tests to write first

`tests/test_transcription_api.py` must cover:

- a valid upload returns `200` and a transcript;
- empty input returns `400`;
- an upload over 20 MiB returns `413`;
- unavailable local tooling returns `503`;
- the uploaded temporary file is gone after success;
- the uploaded temporary file is gone after failure.

Monkeypatch `fairy.web_app.transcribe_audio`. API tests must not start Whisper.

### ✔ Check yourself

Terminal 1:

```bash
cd ~/code/fairy
uv run uvicorn fairy.web_app:app --reload
```

Terminal 2:

```bash
curl -s http://127.0.0.1:8000/api/health
```

Expected:

```json
{"status":"ok"}
```

Open `http://127.0.0.1:8000/`, then check:

1. Typing still works without touching the microphone.
2. Press microphone and allow access.
3. Speak one short brain dump.
4. Press stop.
5. Status changes to Transcribing, then Ready.
6. Text appears in the composer.
7. Edit it before pressing Save or Send.
8. Deny permission once and confirm typing still works.

### Expected output

```text
Recording…
Transcribing locally…
Ready — edit anything before saving.
```

No request to an external transcription host should appear in browser Network tools.

### ⚠ If it breaks

| Symptom | Cause |
|---|---|
| `Form data requires python-multipart` | Run `uv add python-multipart` and restart Uvicorn |
| `MediaRecorder is not defined` | Unsupported browser; keep typing available and show the fallback message |
| Permission repeatedly denied | macOS System Settings → Privacy & Security → Microphone |
| `503` response | Re-run Session 1 file checks |
| Text submits immediately | The microphone button is missing `type="button"` |
| Old typing disappears | Transcript insertion replaced rather than merged with field value |

### Full-file checkpoint

Read every changed file in full:

```bash
sed -n '1,260p' src/fairy/web_app.py
sed -n '1,360p' uiux/ui/voice-capture.js
sed -n '1,240p' uiux/ui/voice-capture.css
sed -n '1,260p' uiux/ui/index.html
sed -n '1,360p' tests/test_transcription_api.py
```

Use this checklist:

- [ ] JavaScript contains no cloud URL.
- [ ] Transcript insertion never calls `form.requestSubmit()`.
- [ ] Every media track is stopped.
- [ ] Python removes temporary files in `finally`.
- [ ] Upload size is enforced before transcription.
- [ ] Tests replace the transcriber with a fake.

### ■ Finish this session

```bash
cd ~/code/fairy
uv run ruff check src/fairy/web_app.py tests/test_transcription_api.py
uv run ruff format --check src/fairy/web_app.py tests/test_transcription_api.py
uv run pytest tests/test_transcription.py tests/test_transcription_api.py
git diff --check
```

```bash
git add pyproject.toml uv.lock src/fairy/web_app.py \
  uiux/ui/index.html uiux/ui/voice-capture.js uiux/ui/voice-capture.css \
  tests/test_transcription_api.py
git commit -m "feat: add optional local voice capture"
```

---

## Session 4 — Put Fairy on the desktop

### ▶ Start this session

```bash
cd ~/code/fairy
git status --short --branch
uv sync
```

**Goal:** a native Python Fairy floats quietly, can be dragged, and never steals focus.

### Install the desktop dependencies

```bash
cd ~/code/fairy
uv add PySide6 "pyobjc-framework-Cocoa; sys_platform == 'darwin'"
```

### Files

```text
Create: src/fairy/desktop/__init__.py
Create: src/fairy/desktop/geometry.py
Create: src/fairy/desktop/floating_fairy.py
Create: src/fairy/desktop/app.py
Create: tests/test_desktop_geometry.py
Modify: pyproject.toml
```

Add the command:

```toml
[project.scripts]
fairy-tasks = "fairy.servers.tasks_server:main"
fairy-desktop = "fairy.desktop.app:main"
```

### Separate pure geometry from Qt

`geometry.py` owns two testable functions:

```python
def clamp_position(
    x: int,
    y: int,
    width: int,
    height: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
) -> tuple[int, int]:
    """Return a top-left position fully inside an available screen."""


def snap_x(x: int, width: int, left: int, right: int) -> int:
    """Return the nearer left- or right-edge x coordinate."""
```

Tests cover left, right, top, bottom, an oversized saved coordinate, and both snap edges.

### Native behavior

`floating_fairy.py` must:

- load `uiux/assets/fairy-full.png` through a repository-relative `Path`;
- scale it to 120 logical pixels high initially;
- use `FramelessWindowHint`, `WindowStaysOnTopHint`,
  `WindowDoesNotAcceptFocus`, and `Qt.Tool`;
- enable `WA_TranslucentBackground` and `WA_ShowWithoutActivating`;
- set macOS activation policy to `NSApplicationActivationPolicyAccessory`;
- distinguish click from drag with a 5-point Manhattan threshold;
- snap to the nearer horizontal screen edge;
- start in the bottom-right corner on first launch;
- emit a `clicked` signal rather than deciding what the popup does;
- show the hover peek only after 650 ms;
- hide the peek when dragging or leaving.

For this session, do not add the saved-position restore path yet. Keep the first pass deliberately simple: the fairy starts in the bottom-right corner and is dragged only by the user.

A good first-pass scaffold is:

```python
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QWidget

from fairy.desktop.geometry import clamp_position, snap_x


class FloatingFairy(QWidget):
    def __init__(self):
        super().__init__()
        # set window flags, translucency, and accessory behavior
        # load fairy image from uiux/assets/fairy-full.png
        # size the image to roughly 120 logical px high
        # set an initial position in the bottom-right corner
        # keep drag state and pointer tracking for click-vs-drag detection
        pass

    def mousePressEvent(self, event):
        # store start position and mouse press point
        pass

    def mouseMoveEvent(self, event):
        # if the drag threshold is crossed, move the window
        pass

    def mouseReleaseEvent(self, event):
        # if it was a drag, snap to the nearer edge
        # if it was a click, emit a clicked signal
        pass

    def move_to_screen_edge(self):
        # compute the current screen bounds and desired x/y
        # call snap_x(x, width, left, right)
        # clamp to the active screen rectangle
        pass


def main():
    app = QApplication([])
    fairy = FloatingFairy()
    fairy.show()
    app.exec()
```

This scaffold is intentionally minimalist. It keeps the app behavior obvious, makes the drag rules visible, and avoids premature persistence or restore code. The first version should be easy to reason about and test before layering on saved state or richer UI.

The hover peek contains only:

```text
Next: one visible task
25:00 left
```

It is sample text in this session. Real data arrives after the shared APIs exist.

### Why the accessory policy matters

Qt window flags describe the window, but macOS also decides whether the process behaves
like a normal foreground application. Accessory policy removes the extra Dock/Cmd-Tab app
presence while allowing the popup itself to become interactive when explicitly opened.

### ✔ Check yourself

```bash
cd ~/code/fairy
uv sync
uv run fairy-desktop
```

Verify all eight:

1. Fairy has no opaque rectangle.
2. Fairy stays above VS Code.
3. Typing in VS Code continues while Fairy is visible.
4. Fairy is absent from `Cmd+Tab`.
5. A small pointer wobble still counts as a click.
6. A real drag moves Fairy.
7. Release snaps to the nearest edge.
8. Quit and reopen restores a visible position.

### Expected output

The terminal remains occupied by the Qt event loop and prints no traceback. The visible
result is the output for this session.

### ⚠ If it breaks

| Symptom | Cause |
|---|---|
| White rectangle | Translucent background is missing or art lost alpha |
| Fairy steals focus | Accessory policy ran too late or the Fairy window accepts focus |
| Image missing | Use `uiux/assets/fairy-full.png`, not an old Swift asset path |
| Fairy jumps on click | Move begins before the 5-point threshold |
| Fairy disappears after monitor change | Restore code did not clamp to current screens |
| `AppKit` import error | Conditional PyObjC dependency did not install |

### Full-file checkpoint

```bash
sed -n '1,220p' src/fairy/desktop/geometry.py
sed -n '1,420p' src/fairy/desktop/floating_fairy.py
sed -n '1,260p' src/fairy/desktop/app.py
sed -n '1,300p' tests/test_desktop_geometry.py
```

Nothing in these files may import or reference Swift. `geometry.py` and its tests may not
import PySide6.

### ■ Finish this session

```bash
cd ~/code/fairy
uv run ruff check src/fairy/desktop tests/test_desktop_geometry.py
uv run ruff format --check src/fairy/desktop tests/test_desktop_geometry.py
uv run pytest tests/test_desktop_geometry.py
git diff --check
```

```bash
git add pyproject.toml uv.lock src/fairy/desktop tests/test_desktop_geometry.py
git commit -m "feat: add floating Python desktop fairy"
```

---

## Session 5 — Open the NeuroFairy popup

### ▶ Start this session

```bash
cd ~/code/fairy
git status --short --branch
uv sync
```

**Goal:** clicking Fairy opens a compact, focusable popup that visually belongs to the
cottage.

### Why the popup is web-based

The repository already contains the approved HTML/CSS visual system and a browser UI that
talks to FastAPI. Re-creating those controls in native Qt would create two design systems
and two sets of interaction bugs.

Use:

- native PySide6 for floating-window and macOS behavior;
- `QWebEngineView` for the popup content;
- the existing FastAPI service for data and AI.

This is still a real desktop application. The native shell owns the windows; the embedded
page owns the compact content.

### Files

```text
Create: src/fairy/desktop/popup.py
Create: uiux/ui/popup.html
Create: uiux/ui/popup.css
Create: uiux/ui/popup.js
Modify: src/fairy/desktop/app.py
```

### Popup layout

Follow `uiux/specs/DESIGN.md`:

```text
┌────────────────────────────────┐  320 logical px wide
│ ADHD Fairy                ⌂  × │  44 px header
├────────────────────────────────┤
│ Growing together        01:42 │
│ [ plant ]  35 / 100 min       │
│ [ Start / Pause / Resume ]     │
├────────────────────────────────┤
│ [ Tasks ] [ Chat ]             │
│                                │
│ selected panel scrolls         │
│                                │
├────────────────────────────────┤
│ pinned input / composer        │
└────────────────────────────────┘
```

The timer summary always stays above the Tasks/Chat switcher. This preserves quick timer
access without squeezing three equal tabs into a narrow panel.

### `PopupWindow` contract

```python
PopupWindow.__init__(parent: QWidget | None = None) -> None
PopupWindow.show_next_to(fairy_geometry: QRect) -> None
PopupWindow.toggle_next_to(fairy_geometry: QRect) -> None
```

It must:

- be 320 px wide and at most 560 px tall;
- clamp its frame to the active monitor's available area;
- load `http://127.0.0.1:8000/popup.html`;
- display a friendly local-service error page if the URL is unavailable;
- accept keyboard focus only after the user clicks Fairy;
- hide on close instead of destroying the timer, chat, or Fairy process;
- leave the floating Fairy visible while open.

`popup.html` uses the existing fonts and color tokens:

```text
Surface       #FAF6EE
Soft surface  #F5EFE5
Ink           #35214F
Muted ink     #665672
Lavender      #DED0ED
Primary       #594071
Outline       #705584
Progress      #9AB58D
```

No glass effect, giant dashboard card, emoji collectible, or duplicate decorative Fairy.

### ✔ Check yourself

Terminal 1:

```bash
cd ~/code/fairy
uv run uvicorn fairy.web_app:app --reload
```

Terminal 2:

```bash
cd ~/code/fairy
uv run fairy-desktop
```

Click Fairy. Verify:

1. Popup opens next to her.
2. Popup is fully on-screen near every edge.
3. Text controls accept focus.
4. Fairy itself still does not steal focus when popup is closed.
5. Close hides popup but does not exit Fairy.
6. Reopen shows the same page without a second popup window.

### Expected output

The popup displays a styled timer shell plus Tasks and Chat sections. Data may still be
sample data in this session.

### ⚠ If it breaks

| Symptom | Cause |
|---|---|
| Blank popup | FastAPI is not running or the wrong URL was loaded |
| `QWebEngineView` import error | Run `uv sync`; PySide6 Addons were not installed |
| Popup opens off-screen | Clamp its final frame, not only its desired origin |
| Popup cannot type | It inherited Fairy's no-focus flags |
| Two popups appear | Click creates a new instance instead of toggling one instance |

### Full-file checkpoint

```bash
sed -n '1,320p' src/fairy/desktop/popup.py
sed -n '1,320p' src/fairy/desktop/app.py
sed -n '1,320p' uiux/ui/popup.html
sed -n '1,420p' uiux/ui/popup.css
sed -n '1,420p' uiux/ui/popup.js
```

Search for accidental old-stack references:

```bash
rg -n "Swift|SwiftUI|Xcode|ADHD_Fairy_Final_Handoff" \
  src/fairy/desktop uiux/ui/popup.*
```

Expected: no matches.

### ■ Finish this session

```bash
cd ~/code/fairy
uv run ruff check src/fairy/desktop
uv run ruff format --check src/fairy/desktop
uv run pytest
git diff --check
```

```bash
git add src/fairy/desktop/app.py src/fairy/desktop/popup.py \
  uiux/ui/popup.html uiux/ui/popup.css uiux/ui/popup.js
git commit -m "feat: add desktop fairy popup shell"
```

---

## Session 6 — Connect popup tasks and AI chat

### ▶ Start this session

```bash
cd ~/code/fairy
git status --short --branch
uv sync
```

**Goal:** replace popup sample content with the existing real task service and AI chat.

### Files

```text
Modify: src/fairy/web_app.py
Modify: uiux/ui/popup.js
Modify: uiux/ui/popup.html
Modify: uiux/ui/popup.css
Create: tests/test_web_api.py
```

### Task API contracts

```http
GET    /api/tasks
POST   /api/tasks
POST   /api/tasks/{task_id}/complete
DELETE /api/tasks/{task_id}
```

Create request:

```json
{"title": "Email my professor", "category": "Optional"}
```

Task response:

```json
{
  "id": 1,
  "title": "Email my professor",
  "category": "Optional",
  "done": false,
  "created_at": "2026-09-20T14:00:00+00:00",
  "completed_at": null
}
```

Reuse `fairy.servers.store` and `fairy.servers.tasks`. Do not write a second task engine.
Convert unknown IDs to `404`, invalid categories to `422`, and empty titles to `422`.

### Chat contract

The popup reuses the existing endpoint:

```http
POST /api/chat
{"message": "I am stuck starting this assignment."}
```

```json
{"reply": "Open the assignment and read only the first question."}
```

### Popup behavior

Tasks:

- load unfinished tasks when the Tasks panel opens;
- add a task with one line and default `Optional` category;
- explicitly complete a task with its checkbox;
- do not turn a chat message into a task automatically;
- show one recommended next visible action, not an overwhelming backlog;
- show loading, empty, and retry states.

Chat:

- preserve the user's message in the transcript immediately;
- disable Send while awaiting a reply;
- keep unsent composer text if a request fails;
- show a retryable connection message;
- keep the transcript for the life of the desktop process;
- never claim a reply is saved to Inbox unless the user explicitly saves it.

### Tests to write first

`tests/test_web_api.py` covers:

- `GET /api/tasks` hides completed tasks;
- `POST /api/tasks` creates an Optional task;
- invalid task category returns `422`;
- completing an unknown task returns `404`;
- deleting an unknown task returns `404`;
- blank chat returns the existing gentle response;
- chat failures return the existing non-shaming fallback.

Use a temporary SQLite database by monkeypatching `store.DB_PATH`. Mock the AI reply; do
not call Ollama in HTTP unit tests.

### ✔ Check yourself

```bash
cd ~/code/fairy
uv run pytest tests/test_tasks.py tests/test_web_api.py -v
```

Then manually:

1. Start FastAPI and Fairy.
2. Open Tasks.
3. Add `popup test task`.
4. Close and reopen the popup; the task remains.
5. Complete it; it disappears from the unfinished list.
6. Open Chat and send a real message.
7. Confirm the local Ollama reply appears.

Database proof:

```bash
sqlite3 ~/.fairy/fairy.db \
  "SELECT id, title, category, done FROM tasks ORDER BY id DESC LIMIT 3;"
```

### Expected output

```text
popup test task|Optional|1
```

The exact ID varies. `done` should be `1` after completion.

### ⚠ If it breaks

| Symptom | Cause |
|---|---|
| Tasks disappear after reopening | Popup stored them only in JavaScript memory |
| Browser tasks and popup tasks differ | Cottage prototype still uses sample/local state; do not silently claim they are unified yet |
| Chat spins forever | `finally` did not re-enable Send after a failed fetch |
| Ollama fallback always appears | Confirm Ollama is running and `qwen2.5:3b` exists |
| `database is locked` | Preserve WAL mode and keep transactions short |

### Full-file checkpoint

```bash
sed -n '1,380p' src/fairy/web_app.py
sed -n '1,520p' uiux/ui/popup.js
sed -n '1,360p' uiux/ui/popup.html
sed -n '1,520p' uiux/ui/popup.css
sed -n '1,420p' tests/test_web_api.py
```

Confirm there is only one task implementation:

```bash
rg -n "def add_task|def complete_task|def delete_task" src/fairy
```

The domain functions should remain in `src/fairy/servers/tasks.py`; HTTP routes may call
them but must not reproduce their SQL.

### ■ Finish this session

```bash
cd ~/code/fairy
uv run ruff check src/fairy/web_app.py tests/test_web_api.py
uv run ruff format --check src/fairy/web_app.py tests/test_web_api.py
uv run pytest tests/test_tasks.py tests/test_web_api.py
git diff --check
```

```bash
git add src/fairy/web_app.py uiux/ui/popup.html uiux/ui/popup.css \
  uiux/ui/popup.js tests/test_web_api.py
git commit -m "feat: connect popup tasks and local ai chat"
```

---

## Session 7 — Port the authoritative flower rules to pure Python

### ▶ Start this session

```bash
cd ~/code/fairy
git status --short --branch
uv sync
```

**Goal:** reproduce the tested browser flower behavior in a pure Python state machine.

Read before typing:

```bash
cd ~/code/fairy
sed -n '1,260p' uiux/specs/bloom-timer-v1.md
sed -n '1,260p' uiux/ui/bloom-engine.js
```

### Files

```text
Create: src/fairy/domain/bloom.py
Confirm: src/fairy/domain/__init__.py
Create: tests/test_bloom.py
```

### Constants

```python
MINUTE_MS = 60_000
BLOCK_MS = 25 * MINUTE_MS
BREAK_MS = 5 * MINUTE_MS
TARGET_MS = 4 * BLOCK_MS
SPECIES = ("Daisy", "Lavender", "Rose", "Sunflower", "Bluebell")
```

### State

```python
class Phase(StrEnum):
    READY = "ready"
    FOCUS = "focus"
    BREAK = "break"
    PAUSED_FOCUS = "pausedFocus"
    PAUSED_BREAK = "pausedBreak"
    BLOOMED = "bloomed"


@dataclass(frozen=True)
class Plant:
    id: str
    species: str
    focus_ms: int = 0
    planted_at_ms: int = 0
    bloomed_at_ms: int | None = None


@dataclass(frozen=True)
class BloomState:
    plant: Plant
    phase: Phase = Phase.READY
    remaining_ms: int = BLOCK_MS
    anchor_ms: int = 0
    collection: tuple[Plant, ...] = ()
```

### Pure interface

```python
create(plant_id, pick, now_ms, collection=()) -> BloomState
stage(state) -> str
tick(state, now_ms) -> BloomState
start(state, now_ms, minutes=25) -> BloomState
pause(state, now_ms) -> BloomState
resume(state, now_ms) -> BloomState
next_plant(state, plant_id, pick, now_ms) -> BloomState
```

No function in this file may import SQLite, FastAPI, PySide6, `time`, Ollama, or
`whisper.cpp`. Time is a number passed by the caller.

### Thirteen required tests

Port the existing Stage 2 tests and verify:

1. Species is selected once from the supplied pick.
2. Ten minutes is saved but does not make a flower.
3. Ten plus fifteen minutes completes block one.
4. Break time does not grow the plant.
5. A new block requires an explicit start.
6. Paused time is excluded.
7. Resume still respects the current block cap.
8. A very late tick advances one phase only.
9. A paused break is frozen.
10. A backwards clock gives no credit.
11. Four focus blocks make exactly one flower.
12. Blooming is idempotent.
13. The next plant retains the collection.

### ✔ Check yourself

First run, before `bloom.py` exists:

```bash
cd ~/code/fairy
uv run pytest tests/test_bloom.py
```

Expected first failure:

```text
ModuleNotFoundError: No module named 'fairy.domain.bloom'
```

After implementing the engine:

```bash
uv run pytest tests/test_bloom.py -v
```

Expected:

```text
13 passed
```

The suite should finish in far less than a second because it never waits for real time.

### Expected output

All thirteen named flower behaviors pass. No test sleeps, opens SQLite, starts FastAPI, or
waits for a real focus interval.

### ⚠ If it breaks

| Failing behavior | Most likely cause |
|---|---|
| Backwards clock | Missing `max(0, now_ms - anchor_ms)` |
| Late tick | Missing `min(elapsed, remaining_ms)` |
| Duplicate flower | Missing collection ID guard |
| Four blocks take 120 minutes | You required an unnecessary fourth break |
| State mutates unexpectedly | Missing `frozen=True`, tuple collection, or `replace()` |

### Full-file checkpoint

```bash
sed -n '1,420p' src/fairy/domain/bloom.py
sed -n '1,520p' tests/test_bloom.py
```

Compare behavior names against the JavaScript source:

```bash
rg -n "MINUTE_MS|BLOCK_MS|BREAK_MS|TARGET_MS|class Phase|def (create|stage|tick|start|pause|resume|next_plant)" \
  src/fairy/domain/bloom.py
```

### ■ Finish this session

```bash
cd ~/code/fairy
uv run ruff check src/fairy/domain tests/test_bloom.py
uv run ruff format --check src/fairy/domain tests/test_bloom.py
uv run pytest tests/test_bloom.py
git diff --check
```

```bash
git add src/fairy/domain/__init__.py src/fairy/domain/bloom.py tests/test_bloom.py
git commit -m "feat: port authoritative flower timer to Python"
```

---

## Session 8 — Create one persistent focus service

### ▶ Start this session

```bash
cd ~/code/fairy
git status --short --branch
uv sync
```

**Goal:** make SQLite and FastAPI the single authority for the timer and garden.

### Files

```text
Modify: src/fairy/servers/store.py
Create: src/fairy/focus.py
Modify: src/fairy/web_app.py
Create: tests/test_focus.py
Extend: tests/test_web_api.py
```

### Schema

Add to `SCHEMA`:

```sql
CREATE TABLE IF NOT EXISTS focus_state (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    plant_id      TEXT    NOT NULL,
    species       TEXT    NOT NULL,
    focus_ms      INTEGER NOT NULL DEFAULT 0,
    planted_at_ms INTEGER NOT NULL,
    phase         TEXT    NOT NULL,
    remaining_ms  INTEGER NOT NULL,
    anchor_ms     INTEGER NOT NULL,
    revision      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS garden (
    plant_id      TEXT PRIMARY KEY,
    species       TEXT    NOT NULL,
    focus_ms      INTEGER NOT NULL,
    planted_at_ms INTEGER NOT NULL,
    bloomed_at_ms INTEGER NOT NULL
);
```

`CHECK (id = 1)` makes a second active timer impossible. `revision` prevents a stale write
from silently replacing a newer action.

### Focus service boundary

```python
@dataclass(frozen=True)
class StoredFocus:
    state: BloomState
    revision: int

current(conn: sqlite3.Connection, now_ms: int) -> StoredFocus
apply_action(conn: sqlite3.Connection, action: Literal["start", "pause", "resume", "next"], now_ms: int, minutes: int | None = None) -> StoredFocus
as_dict(stored: StoredFocus) -> dict[str, object]
```

Public operations begin a short `BEGIN IMMEDIATE` transaction, load one row, tick once,
apply at most one user action, save once, and commit when `store.session()` exits.

Do not accept complete timer state from the browser or desktop. Clients may say **start**,
**pause**, **resume**, or **next**. The service decides the resulting state.

### HTTP contracts

```http
GET  /api/focus
POST /api/focus/start    {"minutes": 25}
POST /api/focus/pause
POST /api/focus/resume
POST /api/focus/next
```

Response:

```json
{
  "phase": "focus",
  "remaining_ms": 1498000,
  "revision": 4,
  "stage": "Sprout",
  "plant": {
    "id": "5f79a087-c6ad-4690-9fe8-9206c22259b9",
    "species": "Lavender",
    "focus_ms": 602000,
    "planted_at_ms": 1789912800000,
    "bloomed_at_ms": null
  },
  "collection": []
}
```

Use `time.time_ns() // 1_000_000` only at the FastAPI boundary. Never read the clock in
`domain/bloom.py`.

### Tests to write first

`tests/test_focus.py` must prove:

- first load creates and persists one plant;
- second load returns the same plant and species;
- start survives closing and reopening SQLite;
- current state ticks elapsed focus before returning;
- pause credits elapsed focus once;
- concurrent stale revision cannot overwrite a newer revision;
- a bloom inserts exactly one garden row;
- `next` preserves every garden row;
- every test uses `tmp_path` and explicit `now_ms`.

HTTP tests prove every route returns the expected state and no route accepts arbitrary
client-supplied `focus_ms`, species, or collection.

### ✔ Check yourself

```bash
cd ~/code/fairy
uv run pytest tests/test_bloom.py tests/test_focus.py tests/test_web_api.py -v
```

Manual check:

```bash
curl -s http://127.0.0.1:8000/api/focus | python -m json.tool
curl -s -X POST http://127.0.0.1:8000/api/focus/start \
  -H 'Content-Type: application/json' \
  -d '{"minutes":10}' | python -m json.tool
```

Database check:

```bash
sqlite3 ~/.fairy/fairy.db \
  "SELECT plant_id, species, phase, focus_ms, remaining_ms, revision FROM focus_state;"
```

### Expected output

One row only. Phase is `focus` after the start command. `remaining_ms` begins near 600000
for a ten-minute session and revision increases.

### ⚠ If it breaks

| Error | Cause |
|---|---|
| `no such table: focus_state` | Updated `SCHEMA` did not run through `store.connect()` |
| Two active rows | Missing `CHECK (id = 1)` or IDs other than 1 are used |
| Flower appears twice | Garden insert is not keyed by `plant_id` |
| Timer loses time after restart | State was not ticked from persisted `anchor_ms` |
| Clients overwrite each other | Whole state is being accepted from clients or revision guard is absent |

Do not delete `~/.fairy/fairy.db` as a routine migration strategy; it contains real tasks.
`CREATE TABLE IF NOT EXISTS` safely adds these new tables.

### Full-file checkpoint

```bash
sed -n '1,340p' src/fairy/servers/store.py
sed -n '1,520p' src/fairy/focus.py
sed -n '1,520p' src/fairy/web_app.py
sed -n '1,520p' tests/test_focus.py
sed -n '1,520p' tests/test_web_api.py
```

Search for forbidden clock reads in the pure layer:

```bash
rg -n "import time|datetime\.now|time\.time" src/fairy/domain
```

Expected: no matches.

### ■ Finish this session

```bash
cd ~/code/fairy
uv run ruff check src/fairy tests/test_focus.py tests/test_web_api.py
uv run ruff format --check src/fairy tests/test_focus.py tests/test_web_api.py
uv run pytest
git diff --check
```

```bash
git add src/fairy/servers/store.py src/fairy/focus.py src/fairy/web_app.py \
  tests/test_focus.py tests/test_web_api.py
git commit -m "feat: add authoritative shared focus service"
```

---

## Session 9 — Connect the cottage and popup to the same timer

### ▶ Start this session

```bash
cd ~/code/fairy
git status --short --branch
uv sync
```

**Goal:** starting, pausing, or resuming from either surface updates the other surface and
can never award duplicate progress.

### Files

```text
Create: uiux/ui/focus-api.js
Modify: uiux/ui/index.html
Modify: uiux/ui/bloom-ui.js
Modify: uiux/ui/popup.js
Create: src/fairy/desktop/local_server.py
Modify: src/fairy/desktop/app.py
Create: tests/test_local_server.py
```

### Browser adapter

`focus-api.js` exposes one small boundary:

```javascript
window.FairyFocus = {
    current: () => request('/api/focus'),
    start: minutes => request('/api/focus/start', { minutes }),
    pause: () => request('/api/focus/pause'),
    resume: () => request('/api/focus/resume'),
    next: () => request('/api/focus/next'),
};
```

The request helper must:

- send JSON only for commands that need it;
- throw an error containing the response status;
- never place complete timer state in a request;
- never fall back to `localStorage` as an authority.

### Cottage migration

Keep `uiux/ui/bloom-engine.js` for smooth local projection and regression comparison. Change
`bloom-ui.js` so:

1. initial state comes from `GET /api/focus`;
2. button actions call `FairyFocus`;
3. returned server state replaces the local projection;
4. the visible clock projects forward locally each second;
5. the browser reconciles with the server every 15 seconds;
6. focus/phase transitions reconcile immediately;
7. returning to the tab reconciles on `visibilitychange`;
8. browser `localStorage` is no longer read or written for timer authority;
9. loading and retry states do not erase the last known display;
10. an API failure never grants focus credit.

### Popup migration

`popup.js` uses the same `FairyFocus` contract or an equivalent local helper against the
same routes. It must show:

- current phase;
- remaining selected-session or break time;
- cumulative `focus_ms / 100 minutes`;
- plant species and growth stage;
- the appropriate Start, Focus 10, Pause, Resume, or Plant another seed controls.

The popup refreshes when it opens, reconciles every 15 seconds while visible, and stops
polling while hidden. Closing it never sends Pause.

### Start the local service with Fairy

`local_server.py` owns one job: make sure `http://127.0.0.1:8000/api/health` is available.

Behavior:

1. Probe health first.
2. If a compatible Fairy server is already running, use it.
3. Otherwise start `python -m uvicorn fairy.web_app:app --host 127.0.0.1 --port 8000` with
   `QProcess`.
4. Poll health for a bounded startup period.
5. Open the popup only after health succeeds.
6. If this process started Uvicorn, terminate it cleanly when Fairy quits.
7. Never kill an existing process that Fairy did not start.

### Integration checks

Run FastAPI and Fairy, then perform this exact sequence:

| Step | Action | Cottage should show | Popup should show |
|---|---|---|---|
| 1 | Open both | same plant/species | same plant/species |
| 2 | Start 10 min in cottage | focus near 10:00 | focus near 10:00 within 15 s |
| 3 | Pause in popup | pausedFocus | pausedFocus |
| 4 | Resume in cottage | focus | focus |
| 5 | Close popup | timer continues | hidden |
| 6 | Reopen popup | current shared time | current shared time |
| 7 | Quit/relaunch Fairy | timer survives | timer survives |

### ✔ Check yourself

Automated:

```bash
cd ~/code/fairy
uv run ruff check .
uv run ruff format --check .
uv run pytest
node --check uiux/ui/focus-api.js
node --check uiux/ui/bloom-ui.js
node --check uiux/ui/popup.js
git diff --check
```

Manual API proof:

```bash
curl -s http://127.0.0.1:8000/api/focus | python -m json.tool
```

Browser proof:

1. Open cottage Focus.
2. Open the desktop popup.
3. Compare plant ID, species, phase, and approximate remaining time.
4. Perform the integration table above.
5. Inspect browser storage and confirm timer progress no longer depends on a garden value
   in `localStorage`.

Database proof:

```bash
sqlite3 ~/.fairy/fairy.db "SELECT COUNT(*) FROM focus_state;"
sqlite3 ~/.fairy/fairy.db "SELECT COUNT(*), COUNT(DISTINCT plant_id) FROM garden;"
```

Expected first result:

```text
1
```

For the garden query, both counts must always match.

### Expected output

Both interfaces show the same plant ID, species, phase, growth total, and countdown within
the 15-second reconciliation window. Starting or pausing from one surface becomes visible
on the other without reloading, and the database still contains exactly one active timer.

### ⚠ If it breaks

| Symptom | Cause |
|---|---|
| Cottage and popup have different plants | One surface still initializes from `localStorage` |
| Time jumps every second | Server is queried every tick instead of local projection plus reconciliation |
| Closing popup pauses timer | Hide/close handler incorrectly sends Pause |
| Duplicate flowers | Client awards flowers or server insert is not idempotent |
| Popup opens before server | Health readiness gate is missing |
| Quitting Fairy kills another dev server | Ownership of the spawned process is not tracked |

### Full-file checkpoint

Read the final integration files in full:

```bash
sed -n '1,320p' uiux/ui/focus-api.js
sed -n '1,620p' uiux/ui/bloom-ui.js
sed -n '1,620p' uiux/ui/popup.js
sed -n '1,320p' src/fairy/desktop/local_server.py
sed -n '1,380p' src/fairy/desktop/app.py
sed -n '1,360p' tests/test_local_server.py
```

Run authority searches:

```bash
rg -n "localStorage.*garden|saved\.garden|persistBloom" uiux/ui
rg -n "fetch\(.*/api/focus|FairyFocus" uiux/ui
rg -n "INSERT INTO garden|UPDATE focus_state" src/fairy
```

Expected:

- no production read/write of a local garden timer;
- both surfaces call `/api/focus`;
- database timer writes live only in `src/fairy/focus.py`.

### ■ Finish this session

```bash
cd ~/code/fairy
uv run ruff check .
uv run ruff format --check .
uv run pytest
node --check uiux/ui/focus-api.js
node --check uiux/ui/bloom-ui.js
node --check uiux/ui/popup.js
git diff --check
```

Review exactly what will be committed:

```bash
git status --short
git diff --stat
```

Then stage only Stage 2 integration files—not every modified file in the repository:

```bash
git add uiux/ui/focus-api.js uiux/ui/index.html uiux/ui/bloom-ui.js \
  uiux/ui/popup.js src/fairy/desktop/local_server.py \
  src/fairy/desktop/app.py tests/test_local_server.py
git commit -m "feat: share flower timer across cottage and desktop"
```

---

## ✅ Stage 2 complete

**You built:**

- optional local voice-to-text with `whisper.cpp`;
- editable brain-dump transcripts with no cloud transcription;
- a floating Python/PySide6 desktop Fairy;
- a NeuroFairy-styled popup with timer, tasks, and local AI chat;
- a pure and tested flower state machine;
- one persistent SQLite focus service;
- one timer shared by the cottage and desktop popup.

**You learned:**

- how a native C++ AI executable can sit behind a Python interface;
- why subprocess argument lists are safer than shell commands;
- how browser media permission and multipart upload work;
- how a native shell and web UI can cooperate without duplicating design work;
- why pure domain code makes timers testable without waiting;
- how a service boundary prevents two interfaces from corrupting shared state;
- why local projection plus periodic reconciliation is better than a database query every
  second.

### Final product checklist

- [ ] Typing works even if voice setup is missing.
- [ ] Voice is opt-in, local, editable, and never auto-submits.
- [ ] Temporary audio is deleted.
- [ ] Fairy floats, drags, snaps, restores, and does not steal focus.
- [ ] Popup opens from Fairy and remains usable near every screen edge.
- [ ] Popup tasks use the real SQLite task service.
- [ ] Popup chat uses the already-working local Ollama connection.
- [ ] Cottage and popup show the same timer and plant.
- [ ] Four focus blocks award exactly one flower.
- [ ] Paused and break time give no credit.
- [ ] Closing a window does not pause the timer.
- [ ] Restarting the app preserves focus state.
- [ ] Full test suite passes.
- [ ] JavaScript syntax checks pass.
- [ ] No Swift or old handoff asset path was introduced.

### Final verification command

```bash
cd ~/code/fairy
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
node --check uiux/ui/voice-capture.js
node --check uiux/ui/focus-api.js
node --check uiux/ui/bloom-ui.js
node --check uiux/ui/popup.js
git diff --check
git status --short --branch
```

### Expected final output

```text
All checks passed!
Every collected test reports PASSED.
```

`git status` should list only changes you intentionally made. Do not use `git add -A` to
hide uncertainty.

---

## What happens to the old Stage 3?

This Stage 2 now contains the floating desktop Fairy, hover behavior, popup, tasks, chat,
and shared timer. Following the old `stage-3-desktop-fairy.md` afterward would duplicate
work and reintroduce the old direct-database assumptions.

After completing this stage, pause and revise the course index before continuing. The next
stage should begin with integrations or agent behavior—not another desktop Fairy build.

### One recommended next action

Complete **Session 1 only**: install `cmake` and `ffmpeg`, build `whisper.cpp`, download
`base.en`, and prove the supplied sample transcribes. Do not touch the UI until that command
works.
