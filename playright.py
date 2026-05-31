from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    print("launching...")
    browser = p.chromium.launch(
        headless=True,
        executable_path="/usr/bin/chromium",
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    print("browser launched")
    page = browser.new_page()
    print("navigating...")
    page.goto("https://www.jpmorganchase.com/careers/explore-opportunities/programs/software-engineer-graduate-level-apprenticeship")
    page.wait_for_load_state("networkidle")
    content = page.content()
    print("closed" if "Applications are currently closed" in content else "open")
    browser.close()