import os
from pathlib import Path
from dotenv import load_dotenv
import ctypes


# Load Environment Variables from local .env file
load_dotenv()

# =====================================================================
# WINDOWS OS ARCHITECTURE CONFIGURATION
# =====================================================================
# Enforce native system DPI awareness to guarantee high-resolution 
# screenshot coordinate pixel perfection on high-DPI/4K displays.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception as e:
        print(f"[-] Warning: Failed to enforce hardware DPI awareness: {e}")

# =====================================================================
# DYNAMIC PATH MATRIX & BOOTSTRAPPING
# =====================================================================
# 1. Dynamically locate the absolute root directory of this project repo
# Assumes this config file resides at '[PROJECT_ROOT]/src/config.py'
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 2. Setup and bootstrap the local screenshot workspace cache directory
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Deliverables DIR
DELIVERABLES_DIR = str(PROJECT_ROOT / "deliverables")
Path(DELIVERABLES_DIR).mkdir(parents=True, exist_ok=True)

# 3. Define the explicit runtime temporary screen capture file path string
TEMP_IMG = str(SCREENSHOTS_DIR / "current_screen.png")

# 4. Resolve the user's Desktop directory safely (Handling OneDrive vs Standard setups)
DESKTOP_PATH = Path.home() / "OneDrive" / "Desktop"
if not DESKTOP_PATH.exists():
    DESKTOP_PATH = Path.home() / "Desktop" # Resilient native fallback strategy

# 5. Bootstrap and export the targeted runtime saving directory space
SAVE_DIR = str(DESKTOP_PATH / "tjm-project")
Path(SAVE_DIR).mkdir(parents=True, exist_ok=True)

# =====================================================================
# CREDENTIAL ENVIROMENT MANAGEMENT & CONFIG STRINGS
# =====================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")

# Driver Resolution: Prioritize .env parameter; Fallback to local root path directory
DRIVER_PATH = os.getenv("EDGE_DRIVER_PATH")
if not DRIVER_PATH:
    DRIVER_PATH = str(PROJECT_ROOT / "drivers" / "msedgedriver.exe")

# Target icon identification boundary string
TARGET_LABEL = "Notepad"