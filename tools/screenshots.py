"""Drives the real UI with Playwright + Edge and a fake microphone to produce docs/screenshots/.
Start the server first (python main.py). Needs: pip install playwright."""
import pathlib, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
S = ROOT / "samples"
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
mic = str(S / "attempt1.wav").replace("\\", "/")

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EDGE, args=[
        "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
        f"--use-file-for-fake-audio-capture={mic}%noloop"])
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, permissions=["microphone"])
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:8000/")
    page.wait_for_selector("#status .chip")
    page.screenshot(path=OUT / "01-setup.png")

    page.set_input_files("#resume", str(S / "resume.txt"))
    page.fill("#jd", (S / "jd.txt").read_text())
    page.click("#make-q")
    page.wait_for_selector(".q", timeout=120000)
    page.locator("#questions").screenshot(path=OUT / "02-questions.png")

    page.locator(".q button", has_text="Practise").first.click()
    page.wait_for_selector("#practice:not([hidden])")
    page.locator("#practice").screenshot(path=OUT / "03-practice.png")

    page.click("#rec")                     # fake mic plays attempt1.wav once
    page.wait_for_timeout(36000)
    page.click("#rec")
    page.wait_for_selector("#review:not([hidden]) .checks", timeout=180000)
    page.wait_for_timeout(500)
    page.screenshot(path=OUT / "04-feedback-attempt1.png", full_page=True)

    page.locator("details summary").nth(1).click()
    page.locator(".check").nth(1).screenshot(path=OUT / "05-filler-evidence.png")

    page.set_input_files("#file", str(S / "attempt2.wav"))   # second attempt by upload
    page.wait_for_selector(".compare-hero", timeout=180000)
    page.wait_for_timeout(500)
    page.locator(".compare-hero").screenshot(path=OUT / "06-compare-hero.png")
    page.screenshot(path=OUT / "07-full-review.png", full_page=True)

    page.click("#suggest-btn")
    page.wait_for_selector(".suggest, #suggest-box .notice", timeout=120000)
    page.locator("#suggest-box").screenshot(path=OUT / "08-suggestion.png")

    m = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    mp = m.new_page()
    mp.goto("http://127.0.0.1:8000/")
    mp.wait_for_selector("#status .chip")
    mp.screenshot(path=OUT / "09-mobile-setup.png", full_page=True)
    mp.set_input_files("#resume", str(S / "resume.txt"))
    mp.click("#make-q")
    mp.wait_for_selector(".q", timeout=120000)
    mp.locator(".q button", has_text="Practise").first.click()
    mp.set_input_files("#file", str(S / "attempt2.wav"))
    mp.wait_for_selector("#review .checks", timeout=180000)
    mp.screenshot(path=OUT / "10-mobile-review.png", full_page=True)
    print("mobile scrollWidth", mp.evaluate("document.documentElement.scrollWidth"), "of 390")
    print("desktop scrollWidth", page.evaluate("document.documentElement.scrollWidth"))
    print("page errors:", errors)
    b.close()
