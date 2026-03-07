import os
import json
import asyncio
from playwright.async_api import async_playwright
import sys

# Import GeminiClient from the parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from gemini_mas import GeminiClient
except ImportError:
    GeminiClient = None

async def capture_and_analyze(url, prompt):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
            # Give it a bit more time for animations/images
            await page.wait_for_timeout(2000)
        except Exception as e:
            await browser.close()
            return f"Failed to load {url}: {str(e)}"
            
        screenshot_path = os.path.expanduser(f"~/gemini_agents/workspace/screenshot_{abs(hash(url))}.png")
        await page.screenshot(path=screenshot_path, full_page=True)
        await browser.close()
        
        if GeminiClient:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key: return "Screenshot saved, but GEMINI_API_KEY missing for analysis."
            client = GeminiClient(api_key, model="gemini-1.5-pro")
            analysis_prompt = prompt or "Analyze this web page screenshot. Critique the design, layout, color scheme, and typography. Identify any UI bugs, alignment issues, or areas that look unfinished. Provide a strict, bulleted list of necessary CSS/code fixes."
            
            analysis = client.generate(analysis_prompt, images=[screenshot_path])
            return f"VISUAL VERIFICATION REPORT for {url}:\n\n{analysis}\n\n(Screenshot saved to {screenshot_path})"
        else:
            return f"Screenshot saved to {screenshot_path}. Cannot analyze without GeminiClient."

def execute(payload):
    """
    Atlas Tool: Visually verifies a webpage and provides a design critique.
    Payload: {
        "url": "http://localhost:3000",
        "prompt": "Optional specific question about the UI" 
    }
    """
    try:
        if isinstance(payload, str):
            data = json.loads(payload)
        else:
            data = payload
            
        url = data.get("url")
        prompt = data.get("prompt", "")
        
        if not url: return "Error: 'url' is required."
        
        # Run the async playwright function in the current event loop
        # Because we might be inside an async loop already, we need a safe way to run this
        import nest_asyncio
        nest_asyncio.apply()
        
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(capture_and_analyze(url, prompt))
        return result

    except Exception as e:
        return f"Visual Verification Error: {str(e)}"
