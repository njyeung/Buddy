import base64
import os
import tempfile
from PIL import Image
from openai import OpenAI
import pyautogui
from screeninfo import get_monitors
from config import MASTER_MODEL
from tool_decorator import tool

client = OpenAI(api_key=os.environ.get("OPENAI"))

@tool("Uses the vision sub-agent to help answer a visual question. Pass in what the user wants to know.")
def ask_about_screen(query: str, primary_monitor_only: bool = True):

    def encode_image_base64(path: str) -> tuple[str, str]:
        ext = os.path.splitext(path)[-1].lower()
        mime = "jpeg" if ext in [".jpg", ".jpeg"] else "png"  # GPT accepts jpeg or png
        with open(path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode("utf-8")
        return b64, mime

    def resize_image(image: Image.Image, target_width: int = 1024) -> Image.Image:
        width, height = image.size
        if width <= target_width:
            return image  # Skip resizing if already small enough

        # Preserve aspect ratio
        scale = target_width / width
        new_size = (target_width, int(height * scale))
        return image.resize(new_size, Image.Resampling.LANCZOS)

    def capture_image():
        if primary_monitor_only:
            return pyautogui.screenshot(allScreens=False)
        else:
            monitors = get_monitors()
            x_offset = min(m.x for m in monitors)
            y_offset = min(m.y for m in monitors)
            width = max(m.x + m.width for m in monitors) - x_offset
            height = max(m.y + m.height for m in monitors) - y_offset
            return pyautogui.screenshot(region=(x_offset, y_offset, width, height))

    img = capture_image()
    img = resize_image(img)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        img.save(tmp.name)
        image_path = tmp.name

    VISION_SYSTEM_PROMPT = """You are a specialized vision sub-agent. Your job is to help the main assistant understand what is currently visible on the user's screen.

    You are given:
    - A user query asking something about the screen
    - A screenshot of the user's screen

    Your task is to:
    1. Answer the user's query as helpfully as possible, using both visual and textual clues in the picture.
    2. Summarize the overall picture: What content is visible, What apps or windows are open, and any relevant visual features.

    Output your response as if you're preparing the **main assistant** to continue helping the user without needing to reach out to you again. Imagine the main LLM can't see the image — you're its eyes.

    Keep your response **detailed but concise** (under 150 words), and format with **clear sections** if helpful (e.g., "Query Answer:", "Screen Summary:").

    Do not ask follow-up questions. Assume the main LLM will handle conversation next.
    """

    try:
        # Send image and user query to GPT vision
        base64_img, mime = encode_image_base64(image_path)

        response = client.chat.completions.create(
            model=MASTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": VISION_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": query},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{mime};base64,{base64_img}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )

        answer = response.choices[0].message.content.strip()

        return answer
    
    finally:
        os.remove(image_path)
