"""Keyboard-only setup and board play, focus continuity, and a touch finish."""
import os
import json
from pathlib import Path
from contextlib import ExitStack
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get("BUILDERWARS_TEST_URL", "http://127.0.0.1:5178")
CONTRAST = r"""(element, mode) => {
    const unsupported = reason => { throw Error(`Unsupported contrast evidence: ${reason}`); };
    const rgba = value => {
        if (!/^rgba?\(/.test(value) || value.includes('%')) unsupported(`color ${value}`);
        const values = value.match(/[\d.]+/g).map(Number);
        if (values.length === 3) values.push(1);
        if (values.length !== 4 || values.some(n => !Number.isFinite(n))) unsupported(`color ${value}`);
        return values;
    };
    const blend = (front, back) => front.slice(0, 3).map((n, i) => n * front[3] + back[i] * (1 - front[3]));
    const background = start => {
        const layers = [];
        let opaque = false;
        for (let node = start; node; node = node.parentElement) {
            const style = getComputedStyle(node);
            if (Number(style.opacity) !== 1) unsupported(`opacity ${style.opacity} on ${node.tagName}#${node.id}`);
            if (style.filter !== 'none' || style.mixBlendMode !== 'normal' || style.backdropFilter !== 'none')
                unsupported(`filter/blending on ${node.tagName}#${node.id}`);
            if (!opaque) {
                if (style.backgroundImage !== 'none') unsupported(`background image/gradient on ${node.tagName}#${node.id}`);
                const color = rgba(style.backgroundColor);
                layers.push(color);
                if (color[3] === 1) opaque = true;
            }
        }
        if (!opaque) unsupported('no opaque ancestor background; browser canvas color unknown');
        let color = [0, 0, 0];
        for (const layer of layers.reverse()) color = blend(layer, color);
        return color;
    };
    const style = getComputedStyle(element);
    const textStyle = mode === 'placeholder' ? getComputedStyle(element, '::placeholder') : style;
    let foreground, backdrop, minimum;
    if (mode === 'focus' || mode === 'inset-focus') {
        if (!element.matches(':focus-visible') || style.outlineStyle === 'none' || parseFloat(style.outlineWidth) <= 0)
            throw Error('Expected visible keyboard focus outline');
        if (mode === 'focus' && parseFloat(style.outlineOffset) < 0) unsupported('inset outline');
        if (mode === 'inset-focus' && parseFloat(style.outlineOffset) > -parseFloat(style.outlineWidth)) unsupported('outline not fully inset');
        background(element); // Also reject effects on the outlined element itself.
        backdrop = background(mode === 'inset-focus' ? element : element.parentElement);
        foreground = rgba(style.outlineColor);
        minimum = 3;
    } else if (['outside-border', 'grid-edge', 'hole-edge', 'disc-edge', 'target'].includes(mode)) {
        background(element); // Validate ancestor effects before measuring solid geometry.
        const painted = mode === 'hole-edge' ? getComputedStyle(element, '::before')
            : mode === 'target' ? getComputedStyle(element, '::after') : style;
        if (painted.backgroundImage !== 'none' || Number(painted.opacity) !== 1 || painted.filter !== 'none')
            unsupported('pseudo-element image, opacity or filter');
        backdrop = background(mode === 'outside-border' || mode === 'disc-edge' ? element.parentElement : element);
        // Connect Four holes sit between the cell and a centered target/disc.
        const cell = mode === 'disc-edge' ? element.parentElement : element;
        const hole = getComputedStyle(cell, '::before');
        if (['target', 'disc-edge'].includes(mode) && cell.closest('.connect4') && hole.content !== 'none') {
            if (hole.backgroundImage !== 'none' || Number(hole.opacity) !== 1) unsupported('hole effects');
            backdrop = blend(rgba(hole.backgroundColor), backdrop);
        }
        if (mode === 'target') {
            if (painted.content === 'none' || parseFloat(painted.width) <= 0) throw Error('Expected rendered legal target');
            foreground = rgba(painted.backgroundColor);
        } else {
            if (painted.borderTopStyle !== 'solid' || parseFloat(painted.borderTopWidth) <= 0)
                throw Error('Expected solid identifying edge');
            foreground = rgba(painted.borderTopColor);
            // Transparent CSS borders reveal the element background, not its outside.
            if (foreground[3] !== 1) unsupported('translucent identifying border');
        }
        minimum = 3;
    } else {
        if (Number(textStyle.opacity) !== 1 || textStyle.textShadow !== 'none') unsupported('text opacity/shadow');
        backdrop = background(element);
        foreground = rgba(textStyle.color);
        const size = parseFloat(textStyle.fontSize), weight = Number(textStyle.fontWeight);
        minimum = size >= 24 || (size >= 18.6666667 && weight >= 700) ? 3 : 4.5;
    }
    const renderedForeground = blend(foreground, backdrop);
    const luminance = color => color.map(n => n / 255).map(n => n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4)
        .reduce((sum, n, i) => sum + n * [0.2126, 0.7152, 0.0722][i], 0);
    const a = luminance(renderedForeground), b = luminance(backdrop);
    return { mode, foreground: renderedForeground.map(n => Math.round(n * 100) / 100),
        background: backdrop.map(n => Math.round(n * 100) / 100), ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05),
        minimum, fontSize: textStyle.fontSize, fontWeight: textStyle.fontWeight };
}"""
with sync_playwright() as p, ExitStack() as cleanup:
    browser = p.chromium.launch()
    cleanup.callback(browser.close)
    context = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, reduced_motion="reduce", service_workers="block")
    origin = urlparse(BASE)
    external_requests = []
    def contain(route):
        target = urlparse(route.request.url)
        if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
            external_requests.append(route.request.url)
            route.abort()
        else:
            route.continue_()
    context.route("**/*", contain)
    context.route_web_socket("**/*", lambda socket: socket.close())
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    def tab_to(selector):
        target = page.locator(selector)
        for _ in range(160):
            if target.evaluate("el => el === document.activeElement"):
                return
            page.keyboard.press("Tab")
        raise AssertionError(f"Keyboard could not reach {selector}")
    def activate(selector):
        tab_to(selector)
        page.keyboard.press("Enter")
    activate("[data-game=tictactoe]")
    for seat in (0, 1):
        activate(f'[data-seat="{seat}"]')
        tab_to("#agent-kind")
        page.keyboard.press("ArrowDown")  # Built-in -> human; no programmatic selection.
        expect(page.locator("#agent-kind")).to_have_value("human")
        activate("#agent-form button[type=submit]")
    activate('[data-cell="0"]')
    expect(page.locator("#metric-moves")).to_have_text("1")
    assert page.locator('[data-cell="0"]').evaluate("el => el === document.activeElement"), "Board rerender lost keyboard focus"
    assert page.locator('[data-cell="0"]').evaluate("el => getComputedStyle(el).outlineStyle !== 'none'")
    page.keyboard.press("ArrowDown")
    expect(page.locator('[data-cell="3"]')).to_be_focused()
    page.keyboard.press("Enter")
    page.keyboard.press("ArrowUp")
    page.keyboard.press("ArrowRight")
    expect(page.locator('[data-cell="1"]')).to_be_focused()
    page.keyboard.press("Enter")
    page.keyboard.press("ArrowDown")
    expect(page.locator('[data-cell="4"]')).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#metric-moves")).to_have_text("4")
    page.keyboard.press("Home")
    expect(page.locator('[data-cell="3"]')).to_be_focused()
    page.keyboard.press("End")
    expect(page.locator('[data-cell="5"]')).to_be_focused()
    assert page.locator('#board [tabindex="0"]').count() == 1
    page.locator('[data-cell="2"]').tap()
    expect(page.locator("#match-status")).to_contain_text("wins")
    assert page.locator("#agent-dialog").get_attribute("aria-labelledby") == "agent-title"
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    assert page.locator("#board button").evaluate_all("buttons => buttons.every(b => b.getAttribute('aria-label') && b.getBoundingClientRect().width >= 44 && b.getBoundingClientRect().height >= 44)")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not errors
    # Human-versus-bot rendering must preserve focus while input is temporarily unavailable.
    page = context.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    activate("[data-game=tictactoe]")
    activate('[data-seat="0"]')
    tab_to("#agent-kind")
    page.keyboard.press("ArrowDown")
    activate("#agent-form button[type=submit]")
    activate("#start")
    activate('[data-cell="0"]')
    expect(page.locator("#metric-moves")).to_have_text("2")
    expect(page.locator('[data-cell="0"]')).to_be_focused()
    expect(page.locator('[data-cell="0"]')).to_have_attribute("aria-disabled", "false")
    activate("#start")  # Pause before checking flipped visual navigation.
    activate("#flip")
    tab_to('[data-cell="0"]')
    page.keyboard.press("ArrowUp")
    expect(page.locator('[data-cell="3"]')).to_be_focused()
    page.keyboard.press("ArrowLeft")
    expect(page.locator('[data-cell="4"]')).to_be_focused()
    assert not errors
    pairs, contrast_failures = [], []
    for width in [320, 390]:
        page = context.new_page()
        page.set_viewport_size({"width": width, "height": 844})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE)
        page.locator("#board .cell").first.wait_for()
        def check(selector, surface, mode="text"):
            target = page.locator(selector).first
            expect(target).to_be_visible()
            target.scroll_into_view_if_needed()
            if mode in ["focus", "inset-focus"]:
                page.keyboard.press("Tab")
                target.focus()
            if mode == "placeholder":
                assert target.input_value() == "" and target.get_attribute("placeholder"), selector
            try:
                pair = target.evaluate(CONTRAST, mode)
                pair.update({"width": width, "surface": surface, "selector": selector})
                pairs.append(pair)
                if pair["ratio"] < pair["minimum"]:
                    contrast_failures.append(pair)
            except Exception as error:
                contrast_failures.append({"width": width, "surface": surface, "selector": selector, "mode": mode, "unsupported": str(error)})
        for selector in ["#arena h1", "#arena .subtitle", "#quickplay", "#reset", "#match-status", "#notice", ".telemetry span"]:
            check(selector, "Arena")
        check("#quickplay", "Arena", "focus")
        for game in ["chess", "checkers", "connect4", "tictactoe"]:
            check(f'[data-game="{game}"]', "Games")
        for tab in ["arena", "forge", "watch", "evals", "academy"]:
            page.locator(f'nav [data-tab="{tab}"]').click()
            check(f'nav [data-tab="{tab}"]', tab)
            check(f"#{tab} h1", tab)
            check(f"#{tab} .subtitle", tab)
            if tab == "forge":
                for selector in ["#creator label", "#creator-name", "#creator button[type=submit]"]:
                    check(selector, "Forge form")
                check("#creator-name", "Forge form", "focus")
                check("#creator-name", "Forge form", "outside-border")
            elif tab == "watch":
                for selector in ["#watch-link", "#watch-broadcast"]:
                    check(selector, "Watch")
                check("#join-link", "Watch form", "placeholder")
                check("#join-link", "Watch form", "focus")
                check("#join-link", "Watch form", "outside-border")
            elif tab == "evals":
                for selector in ["#evals .workspace-form > p", "#series-length", "#run-series"]:
                    check(selector, "Evals")
                check("#series-length", "Evals form", "focus")
                check("#series-length", "Evals form", "outside-border")
            elif tab == "academy":
                for selector in ["#academy-status", "#academy-pair", "#academy .lessons .muted"]:
                    check(selector, "Academy")
                check("#academy-pair", "Academy", "focus")
                page.locator("#academy details").last.locator("summary").click()
                check("#academy a", "Academy link")
        page.locator('nav [data-tab="arena"]').click()
        page.locator('[data-seat="0"]').click()
        for selector in ["#agent-title", "#agent-form label", "#agent-name", "#agent-kind", "#agent-form button[type=submit]"]:
            check(selector, "Contender form")
        check("#strategy", "Contender form", "placeholder")
        check("#agent-name", "Contender form", "focus")
        for selector in ["#agent-name", "#agent-kind", "#strategy"]:
            check(selector, "Contender form", "outside-border")
        page.locator("#close-dialog").click()
        # Local human-only fixtures: no model/provider calls and no synthetic DOM styles.
        for game in ["chess", "checkers", "connect4", "tictactoe", "custom"]:
            if game == "custom":
                page.locator('nav [data-tab="forge"]').click()
                page.locator("#creator-name").fill("Contrast fixture")
                page.locator("#creator-rows").fill("3")
                page.locator("#creator-cols").fill("3")
                page.locator("#creator-connect").fill("3")
                page.locator("#creator-gravity").uncheck()
                page.locator("#creator button[type=submit]").click()
            else:
                page.locator(f'[data-game="{game}"]').click()
            expect(page.locator("#board")).to_have_class(f"board {game}")
            for seat in [0, 1]:
                page.locator(f'[data-seat="{seat}"]').click()
                page.locator("#agent-kind").select_option("human")
                page.locator("#agent-form button[type=submit]").click()
            if game in ["chess", "checkers"]:
                page.locator(f'[data-cell="{48 if game == "chess" else 40}"]').click()
                for shade in ["light", "dark"]:
                    check(f"#board .cell.{shade}:not(.selected)", game, "inset-focus")
                    check(f"#board .cell.{shade}:not(.selected) .coord", game)
                check("#board .target", game, "target")
                if game == "checkers":
                    check("#board .selected .disc.white", "selected white checker", "disc-edge")
            else:
                check("#board .target", game, "target")
                check("#board .cell", game, "grid-edge")
                if game == "connect4":
                    check("#board .cell", game, "hole-edge")
                page.locator('[data-cell="0"]').click()
                page.locator('[data-cell="1"]').click()
                expect(page.locator("#metric-moves")).to_have_text("2")
                check("#board .disc.black", game, "disc-edge")
                check("#board .cell", game, "inset-focus")
                check("#board .coord", game)
                if game == "tictactoe" and width == 390:
                    screenshot = os.environ.get("BUILDERWARS_CONTRAST_SCREENSHOT")
                    if screenshot:
                        if Path(screenshot).exists():
                            raise AssertionError("Refusing to overwrite contrast screenshot")
                        page.locator("#board").scroll_into_view_if_needed()
                        page.screenshot(path=screenshot)
        page.close()
    print(json.dumps({"contrastPairs": pairs, "contrastFailures": contrast_failures, "externalRequestsBlocked": external_requests,
        "boundaries": "Representative text/placeholder, form outside edges, inset/outer focus, board grid/hole/disc solid edges and legal targets; transparent ancestor and target/hole backgrounds composited. Solid borders are the asserted silhouette, not blur/shadow pixels. Gradients/images, opacity, filters, blend modes and text shadows fail as unsupported. Human-only built-in-game fixtures and one 3x3 non-gravity custom recipe at 320/390px; not exhaustive board states, full WCAG or native OS certification."}))
    assert not contrast_failures, json.dumps(contrast_failures)
    assert not external_requests, external_requests
    assert not errors, errors
    context.close()
    browser.close()
print("PASS: keyboard-only configuration, roving board focus, arrow/Home/End controls, touch win, reduced-motion preference, representative 320/390px text and focus contrast")
