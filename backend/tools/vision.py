import os
import tempfile
from PIL import Image
import pyautogui
from screeninfo import get_monitors
import easyocr
from tool_decorator import tool

reader = easyocr.Reader(['en'], gpu=True)

@tool("Reads what's currently on the user's screen. Use this to see what the user is looking at")
def capture_screens(primary_monitor_only: bool):
    result = []

    def extract_text(img: Image.Image):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            img.save(f.name)
            image_path = f.name
        try:
            detections = reader.readtext(image_path)
            return "\n".join([text for _, text, _ in detections])
        finally:
            os.remove(image_path)
    
    if primary_monitor_only:
        screenshot = pyautogui.screenshot(allScreens=False)
        text = extract_text(screenshot)
        return [{"Monitor": "Primary", "text": text.strip()}]

    monitors = get_monitors()
    x_offset = min(m.x for m in monitors)
    y_offset = min(m.y for m in monitors)

    for i, monitor in enumerate(monitors):
        region = (monitor.x - x_offset, monitor.y - y_offset, monitor.width, monitor.height)
        screenshot = pyautogui.screenshot(allScreens=True, region=region)

        text = extract_text(screenshot)

        result.append({
            "Monitor": f"Monitor {i} ({monitor.name if hasattr(monitor, 'name') else 'unknown'})",
            "text": text.strip()
        })

    return result
