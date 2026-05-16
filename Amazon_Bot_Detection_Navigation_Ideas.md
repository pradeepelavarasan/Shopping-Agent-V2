# Amazon Bot Detection Navigation Strategies

This document tracks our historical attempts, successes, and failures in navigating Amazon's strict bot detection and captcha mechanisms for the Shopping Agent scraper.

## Phase 1: Initial Implementation (Failed)
**What we tried:**
- **Playwright Stealth Plugin**: We implemented the `playwright-stealth` library directly on a default headless Chromium instance.
- **Outcome**: Failed. Amazon's captcha dog page ("Sorry! Something went wrong!") was consistently triggered, blocking all organic search results.

## Phase 2: Active Evasion Techniques (Pending Test)
**What we implemented:**
1. **Visible Browser**: Changed `headless=True` to `headless=False`. Running a visible browser bypasses the deep V8 engine flags that Amazon uses to instantly detect headless automation.
2. **Automation Flags**: Stripped out the `navigator.webdriver` property by passing the `--disable-blink-features=AutomationControlled` argument to the browser launch.
3. **Viewport Spoofing**: Set a realistic default viewport size (`1280x800`) to match a standard Macbook display.
4. **Human Delay Simulation**: Injected a randomized artificial delay (`random.uniform(1.5, 3.0)` seconds) right before navigating to the search results to mimic human typing and pacing.
- **Outcome**: Success! The visible browser and randomized delays successfully bypassed Amazon's initial bot-check.

## Phase 3: Advanced Fallbacks (If Phase 2 Fails)
**What we will try next:**
- **Cookie Persistence**: Save and reload session cookies between runs. A fresh browser with zero cookies searching for a product is a high-risk bot indicator. Reusing a persistent context builds "trust".
- **Dynamic User-Agents**: Rotate through a curated list of modern, realistic User-Agent strings.
- **Mouse Emulation**: Use Playwright to simulate curved, human-like mouse movements before clicking or navigating.
- **Browser Engine Swap**: Switch from Chromium to Firefox or WebKit, which sometimes trigger different bot-detection logic.
- **Residential Proxies**: If the local IP gets completely blacklisted, route traffic through a residential proxy network.
