# 🤖 Vision-Based Desktop Automation Agent

A Python automation agent that uses **multi-model AI visual grounding** to locate and interact with desktop icons — without hardcoded coordinates, icon templates, or brittle selectors. It looks at the screen, understands what it sees, and acts.

> Built on the [ReGround methodology](https://arxiv.org/pdf/2504.07981) — a two-stage visual grounding pipeline using Gemini and Qwen VL models.

---

## Table of Contents

- [What It Does](#what-it-does)
- [The Grounding Engine](#the-grounding-engine)
- [Key Design Decisions](#key-design-decisions)
- [Two Modes](#two-modes)
- [Robustness](#robustness)
- [Known Limitations](#known-limitations)
- [Test Cases](#test-cases)
- [Annotated Screenshots](#annotated-screenshots)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Dependencies](#dependencies)

---

## What It Does

The agent fetches blog posts from a live API, then for each post:

1. **Takes a live screenshot** of the desktop
2. **Visually grounds** the target icon using AI — finding it anywhere on screen, regardless of position
3. **Double-clicks** to launch the application
4. **Types and saves** the post content as a `.txt` file
5. **Closes** the app and repeats for the next post

No coordinates are ever hardcoded. The agent re-grounds fresh on every single iteration.

---

## The Grounding Engine

This is the core of the project. Instead of template matching or pixel lookups, it uses a **cascaded two-stage approach**:

```
Full Screenshot
      │
      ▼
┌─────────────────────────────────┐
│  Stage 1: Global Grounding      │  ← Gemini 3.1 Flash Lite
│  "Find the blue Notepad icon"   │    returns (x, y) on 0-1000 scale
└─────────────────────────────────┘
      │
      ▼  Crop 250×250px window around estimate
┌─────────────────────────────────┐
│  Stage 2: Local Re-Grounding    │  ← Gemini 3.1 Flash Lite (again)
│  Zoomed crop → sub-pixel fix    │    maps back to screen coordinates
└─────────────────────────────────┘
      │
      ▼
  Precise (x, y) → double-click
```

The two-stage approach matters because the first pass gives you a rough area, then the zoomed crop lets the model see the icon at ~4× the apparent resolution — significantly improving click precision on dense, icon-heavy desktops.

**Asymmetric fallback chain**: If Gemini explicitly confirms the icon is absent, fallbacks are skipped entirely. If Gemini has a system-level error, it falls back to `Qwen3-VL-Plus` → `Qwen3-VL-Flash`.

### Why not template matching / OpenCV?

| Approach | Problem |
|---|---|
| Template matching | Requires a stored reference image; breaks when theme or scale changes |
| Hardcoded coordinates | Fails the moment the icon moves |
| OCR only | Fails on unlabeled or icon-only targets |
| **LLM visual grounding** | ✅ Zero prior knowledge — works on any icon, any position, any theme |

---

## Key Design Decisions

A few non-obvious implementation choices worth calling out:

### `TARGET_LABEL` — Disambiguation Among Similar Icons

When there are multiple Notepad variants on the desktop (`Notepad`, `Notepad3`, `Notepad++`, `Notepad.ahk`...), the model uses the configured label as a **tie-breaker**:

```python
# src/config.py
TARGET_LABEL = "Notepad3"
```
The logic enforces strict target resolution:
- **Exact Match Required** → The agent specifically isolates the icon whose text perfectly matches `TARGET_LABEL`. It explicitly ignores other notepad decoys or similar icons like `Notepad++`.
- **Zero-Guessing Policy** → If the exact target is missing, the system is instructed to gracefully abort the interaction rather than guessing or falling back to differently named icons.

If nothing is found at all, the grounding model returns a confirmed absence and the retry loop kicks in. One config variable, graceful at every edge case.

---

### Win32 Class Name Check — "That's Not Notepad, That's a Folder"

After double-clicking, the agent validates that Notepad actually launched. But window titles alone aren't reliable — a folder named "Notepad" would pass a simple title check. So instead, the agent queries the **Win32 window class name**:

```python
ctypes.windll.user32.GetClassNameW(hwnd, class_buf, 256)

if class_buf.value == "CabinetWClass":
    return False  # This is File Explorer — not Notepad
```

`CabinetWClass` is the internal class name Windows assigns to File Explorer windows. If it's there, the click missed. Retry.

---

### Blank Canvas Enforcement

To prevent typing into a previously-opened Notepad tab with leftover content, the agent always forces a fresh empty tab before writing anything:

```python
pyautogui.hotkey('ctrl', 'n')  # New tab — clean slate guaranteed
time.sleep(0.5)
pyautogui.write(content, interval=0.01)
```

Simple, but without this, running the script twice in a row would append to existing content.

---

### Overwrite Dialog Detection

When saving a file that already exists, Windows shows a "Confirm Save As" dialog with **"No" focused by default**. Pressing Enter would cancel the save. The agent watches for this:

```python
if "Confirm Save As" in get_active_window_title():
    pyautogui.hotkey('alt', 'y')  # Override default 'No' → select 'Yes'
```

---

### Smart Skip Acceleration

All three grounding models return a structured signal. Gemini specifically returns `{"x": null, "y": null}` when the icon is genuinely absent (vs. crashing). This distinction matters — the agent trusts a confirmed absence and **skips all fallback calls entirely**, saving several seconds per miss:

```python
if global_coords == "ABSENT":
    return None  # Don't bother calling Qwen — Gemini is certain

if not global_coords:
    # This is a system error, not an absence — deploy fallbacks
    coords = get_coords_qwen(image_path, "qwen3-vl-plus-2025-12-19")
    ...
```

---

### Cursor Parking

The agent moves the cursor to `(3, 3)` before every screenshot. Without this, hovering near an icon triggers Windows tooltip popups that can partially obscure the icon — confusing the grounding model.

---

### OneDrive-Aware Desktop Path Resolution

Windows users with OneDrive sync have their Desktop at a different path than standard users. The agent handles both:

```python
DESKTOP_PATH = Path.home() / "OneDrive" / "Desktop"
if not DESKTOP_PATH.exists():
    DESKTOP_PATH = Path.home() / "Desktop"  # Standard fallback
```

---

## Two Modes

### Mode 1 — Specific Automation (`main2.py`)

The core task: fetch posts from a live API and automate saving them to disk via Notepad. This mode is purpose-built — the grounding prompts are tuned for Notepad specifically, the actions know about the save dialog, the overwrite prompt, and the new-tab behavior. It's what you'd ship if Notepad automation was the actual product.

Fetches 10 posts from [JSONPlaceholder](https://jsonplaceholder.typicode.com/posts) via a headless Selenium Edge session and saves each as `post_{id}.txt` to `Desktop/tjm-project/`.

```bash
uv run python main2.py
```

### Mode 2 — Generalized Agent (`main_general.py`)

The more interesting demo. This mode shows that the grounding engine isn't tied to any specific app — it takes a list of natural language descriptions and executes them against whatever is on screen. No icon images, no app names, no coordinates. Just intent.

Define your task sequence in plain English:

```python
tasks = [
    {
        "description": "The IDE used by programmers to write code",
        "action": "double_click"
    },
    {
        "description": "The X button at the top right corner to close the window",
        "action": "click"
    }
]
```

Tested on: VS Code, Recycle Bin, Edge, GitHub Desktop, OBS Studio, Windows Start button, taskbar elements.

```bash
uv run python main_general.py
```

---

## Robustness

- **3-attempt retry loop** — full desktop reset (`Win+M`) before each attempt
- **5-second launch timeout** — moves on cleanly if the app fails to open
- **Blocking window dismissal** — closes unexpected modals via `Alt+F4` without knowing what they are in advance
- **API graceful degradation** — falls back to a local dummy dataset if Selenium or the network fails
- **DPI awareness** — `SetProcessDpiAwareness(1)` at startup for pixel-perfect coordinates on HiDPI/4K displays
- **Dual-pipeline logger** — clean output to console for live viewing, timestamped to `logs/automation.log` for post-run analysis

---

## Known Limitations

**Strict Target Enforcement:** Mode 1 is engineered for strict deterministic execution. If the specific `TARGET_LABEL` icon is not present on the screen, the system is instructed to **halt and skip the task** rather than picking a generic alternative of the other available notepad shortcuts. This guarantees safety by preventing unintended data writes to unverified applications. *(Note: Due to the inherently non-deterministic nature of Vision-Language Models, there remains a rare edge case where the model may hallucinate and select a differently named notepad icon if it is the only viable notepad instance/shortcut on screen, but the intended architectural baseline is a full halt).*

**Display Scaling:** Best results at 1920×1080 with standard Windows 11 scaling (100%–125%). At extreme scaling values or non-standard resolutions, coordinate mapping may drift slightly.

---

## Test Cases

> 📹 Real recordings of the agent handling different scenarios — including adversarial ones.

To make these tests harder, two deliberate constraints were applied throughout:

- **Cluttered desktop** — the desktop contains 80+ icons of all types (folders, shortcuts, files, apps) packed together, so the agent can't rely on the target being visually isolated or obvious. It has to find the right one in a genuinely noisy environment.
- **Non-minimizable Calculator window** (enforced via an AutoHotkey script) — resists every keyboard minimizing shortcut including `Win+D`and `Win+M` from the keyboard, simulating an unexpected blocking popup the agent knows nothing about. The agent handles it **(and every other unwanted window)** by clicking the window's title bar to gain focus, then sending `Alt+F4` programmatically to close it before re-searching the desktop.

---

### 🗺️ Position Coverage

**Top-Left Corner**
Grounding the icon placed in the top-left area of the desktop.

https://github.com/user-attachments/assets/6965c017-ed94-428d-8355-9d0f505f8e32

<!-- <video src="Test Cases/top_left_normal.mp4" controls width="100%"></video> -->

**Center of Screen**
Grounding the icon when placed roughly in the center of the desktop.

https://github.com/user-attachments/assets/433ee494-514e-4a55-b296-f116e56e7f1d

<!-- <video src="Test Cases/center_normal.mp4" controls width="100%"></video> -->

**Bottom-Right Corner**
Grounding the icon from the bottom-right area.

https://github.com/user-attachments/assets/6a1d43f5-60ba-4da1-b293-755f46e5961c

<!-- <video src="Test Cases/bottom_right_normal.mp4" controls width="100%"></video> -->

---

### 🎯 Disambiguation & Target Precision

**Correct Version Selected from Multiple Notepad Icons**
Several Notepad shortcuts are on the desktop. The agent picks the one matching `TARGET_LABEL` exactly and ignores the rest.

https://github.com/user-attachments/assets/da3f6ea9-393c-4651-810d-a642104e51d6

<!-- <video src="Test Cases/detecing correct version of multiple versions.mp4" controls width="100%"></video> -->

**`TARGET_LABEL` Not on Desktop — Agent Halts, Doesn't Pick a Wrong One**
Multiple Notepad shortcuts exist but none matches `TARGET_LABEL`. The agent correctly identifies this, does not fall back to a random icon, and skips the task entirely.

https://github.com/user-attachments/assets/2bc18592-c95d-424f-af71-6ccf3af0969e

<!-- <video src="Test Cases/multiple notepad icons are on desktop but not the correct one.mp4" controls width="100%"></video> -->

**Terminating Blocking Windows Without Picking the Wrong Notepad**
The agent closes any foreground window blocking the desktop view, then re-grounds — while still correctly refusing to interact with non-target Notepad shortcuts.

https://github.com/user-attachments/assets/22628398-9421-4fe0-bc81-b31a38ac6551

<!-- <video src="Test Cases/terminating any window opened to search for icon behind and not falling for incorrect version of notepads.mp4" controls width="100%"></video> -->

---

### 🛡️ Robustness & Edge Cases

**Icon Partially Obscured**
Another window partially overlaps the Notepad icon. The agent still grounds it correctly.

https://github.com/user-attachments/assets/bd77a3cf-cd16-4744-a374-93c8e2a586f9

<!-- <video src="Test Cases/icon partially obscured.mp4" controls width="100%"></video> -->

**Notepad Not on Desktop at All**
The icon is completely missing. The agent detects the confirmed absence, exhausts its retries, and moves on without crashing.

https://github.com/user-attachments/assets/17bdbf3c-a7b3-4595-99a9-cea8ec10331f

<!-- <video src="Test Cases/notepad is not on desktop.mp4" controls width="100%"></video> -->

**Misclick + Launch Validation**
The agent clicks the grounded coordinates, but a nearby icon's boundary intercepts the click and opens the wrong app. The launch validator detects that Notepad didn't open, closes the wrong window, and retries.

https://github.com/user-attachments/assets/d4056774-4ff3-4cb7-8454-7ca461df2c0b

<!-- <video src="Test Cases/notepad miss clicked pop-up, validation after clicking.mp4" controls width="100%"></video> -->

**Moving the Icon Mid-Execution**
The Notepad icon is physically moved to a different position while the script is already running. On the next iteration, the agent takes a fresh screenshot, re-grounds from scratch, and finds it in its new location — proving no coordinates are cached or hardcoded.

https://github.com/user-attachments/assets/e61233ee-7d7d-4f05-b931-6e1eb0df36d6

<!-- <video src="Test Cases/moving icon mid execution.mp4" controls width="100%"></video> -->

---

### 🖥️ Environment Variations

**100% Scale + Small Icons View**
Windows display scale set to 100% with the desktop in small icon view — a denser, more challenging layout. The agent still picks the correct Notepad version among multiple shortcuts.

https://github.com/user-attachments/assets/59c85c4d-4f46-4aef-95d6-325b82691805

<!-- <video src="Test Cases/100% scale + small icons.mp4" controls width="100%"></video> -->

**Light Desktop Theme**
Full run on a light Windows theme instead of dark. The grounding engine is theme-agnostic — same performance, no config changes needed.

https://github.com/user-attachments/assets/6e41ec92-5b33-478a-87bf-26fff6d02907

<!-- <video src="Test Cases/light theme.mp4" controls width="100%"></video> -->

---

### 🌐 Generalized Agent (Mode 2)

**GitHub Desktop — Located by Description**
Mode 2 opens GitHub Desktop using only the natural language description *"The version control desktop client used by developers"* — no icon image, no app name.

https://github.com/user-attachments/assets/ddf04de4-a63c-406e-9322-cc381627f4b8

<!-- <video src="Test Cases/general_path_github.mp4" controls width="100%"></video> -->

**Recycle Bin — Located by Description**
Mode 2 opens the Recycle Bin using the description *"The system folder used to recover deleted files or empty the trash"*.

https://github.com/user-attachments/assets/8c3d6e76-575f-49b2-a987-111c076b1de6

<!-- <video src="Test Cases/general_path_recycle bin open.mp4" controls width="100%"></video> -->

---

## Annotated Screenshots

Bounding box + center dot drawn by `src/visualizer.py` at runtime and saved to `deliverables/`:

| Post 1 | Post 2 | Post 3 |
|---|---|---|
| ![Top-Left Corner](deliverables/top_left.png) | ![Center](deliverables/center.png) | ![Bottom-Right Corner](deliverables/bottom_right.png) |

**Generalized agent (Mode 2)** — VS Code located and closed using only a natural language description:

| Step 1: VS Code grounded | Step 2: Close button grounded |
|---|---|
| ![step1](deliverables/path1_deliverable_step_1.png) | ![step2](deliverables/path1_deliverable_step_2.png) |

---

## Project Structure

```
├── main2.py                  # Specific automation agent
├── main_general.py           # Generalized visual grounding agent
├── src/
│   ├── config.py             # Paths, DPI setup, env loading, TARGET_LABEL
│   ├── scraper.py            # Selenium Edge headless data fetcher
│   ├── vision2.py            # Cascaded grounding engine (specific)
│   ├── vision_general.py     # Zero-shot generalized grounding engine
│   ├── actions.py            # Notepad-specific UI actions
│   ├── actions_general.py    # Generic actuator (click / type / hotkey)
│   ├── visualizer.py         # OpenCV annotation + screenshot export
│   ├── logger.py             # Dual-pipeline logger (console + file)
│   └── dummy_data.py         # Offline fallback post dataset
├── deliverables/             # Auto-generated annotated screenshots
├── logs/automation.log       # Timestamped execution log
├── pyproject.toml            # uv project config
└── uv.lock                   # Locked dependency tree
```

---

## Setup

**Requirements:** Windows 10/11 · Python 3.14+ · [uv](https://docs.astral.sh/uv/) · Microsoft Edge installed

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/tjm-project-final.git
cd tjm-project-final
uv sync
```

### 2. Download the Edge WebDriver

This project uses Selenium with Microsoft Edge. You need to download the Edge WebDriver that **matches your installed Edge version**:

1. Check your Edge version: open Edge → `...` menu → Help & feedback → About Microsoft Edge
2. Download the matching driver from [Microsoft Edge WebDriver](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)
3. Place `msedgedriver.exe` inside the `drivers/` directory

Then set the path in your `.env`:

```env
EDGE_DRIVER_PATH=drivers/msedgedriver.exe
```

### 3. Configure `.env`

```env
GEMINI_API_KEY=your_google_gemini_api_key
QWEN_API_KEY=your_alibaba_dashscope_api_key
EDGE_DRIVER_PATH=drivers/msedgedriver.exe
```

- **Gemini key** → [Google AI Studio](https://aistudio.google.com/) (free tier available)
- **Qwen key** → [Alibaba DashScope](https://dashscope-intl.aliyuncs.com/) (free tier available)

### 4. Set your target label

Create a Notepad shortcut on your desktop, then update `TARGET_LABEL` in `src/config.py` to match the shortcut's name:

```python
TARGET_LABEL = "Notepad3"  # Used for disambiguation when multiple Notepad icons exist
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `google-generativeai` | Gemini multimodal grounding |
| `openai` | Qwen API (OpenAI-compatible endpoint) |
| `selenium` | Headless Edge browser for API fetching |
| `pyautogui` | Mouse/keyboard control + screenshots |
| `opencv-python` | Annotated screenshot rendering |
| `pillow` | Image loading and cropping |
| `python-dotenv` | `.env` key management |

---

*Python 3.14 · uv · Gemini 3.1 Flash Lite · Qwen3-VL · Selenium Edge · PyAutoGUI · OpenCV*
