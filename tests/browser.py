"""Exercise public room sharing using disposable browser state and synthetic names."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlsplit
import argparse
import base64
import json
import random
import re
import subprocess
import threading

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ROOM_A = 'lkcsb-seminar-room-1-1'
ROOM_B = 'lkcsb-seminar-room-1-2'


def encoded(room, names):
    return subprocess.check_output(
        ['node', '--input-type=module', '-e',
         "import lz from 'lz-string';let s='';for await(const c of process.stdin)s+=c;process.stdout.write(lz.compressToEncodedURIComponent(s));"],
        input=json.dumps({'r': room, 'd': names}).encode(), cwd=ROOT,
    ).decode()


class AppHandler(SimpleHTTPRequestHandler):
    rewrites = json.loads((ROOT / 'vercel.json').read_text())['rewrites']

    def do_GET(self):
        path = urlsplit(self.path).path
        if not Path(self.translate_path(path)).is_file():
            for rewrite in self.rewrites:
                if re.fullmatch(rewrite['source'], path):
                    self.path = rewrite['destination']
                    break
        try:
            super().do_GET()
        except ConnectionError:
            pass  # A closed disposable context may cancel an in-flight asset.

    def log_message(self, *_):
        pass


def run(base, output, cases):
    first = f'{base}/room/{ROOM_A}?s={quote(encoded(ROOM_A, {"1": "Test Alice"}))}&from=fixture#seats'
    second = f'{base}/room/{ROOM_A}?s={quote(encoded(ROOM_A, {"1": "Test Bob"}))}'
    other_room = f'{base}/room/{ROOM_B}?s={quote(encoded(ROOM_B, {"1": "Test Bob"}))}'
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for case in cases:
            width = 390 if case.endswith('mobile') else 1440
            context = browser.new_context(viewport={'width': width, 'height': 1000}, service_workers='block')
            context.set_default_timeout(10000)
            allowed = {urlsplit(base).netloc, 'smuseats.vercel.app', 'smuseats.hong-yi.me'}
            external = []

            def route(request_route):
                if urlsplit(request_route.request.url).netloc in allowed:
                    request_route.continue_()
                else:
                    external.append(request_route.request.url)
                    request_route.abort()

            context.route('**/*', route)
            context.add_init_script("""window.__copies=[];Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.__copies.push(text)}}});""")
            page = context.new_page()
            page.set_default_timeout(10000)
            page.emulate_media(reduced_motion='reduce')
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            result = {'case': case, 'viewport': width}
            try:
                page.goto(first)
                expect(page.locator('.room-banner h1')).to_contain_text('Seminar Room 1-1')

                def open_sidebar():
                    if 'open' not in page.locator('.collapsible-sidebar').get_attribute('class').split():
                        page.locator('.sidebar-toggle').click()

                if case.startswith('share-reload'):
                    open_sidebar()
                    page.locator('.reserved-list__name-input').fill('Test Ælice 🦐')
                    page.locator('.reserved-list__name-input').press('End')
                    page.locator('.reserved-list__name-input').press_sequentially(' 123')
                    page.locator('.banner-btn-copy').click()
                    page.wait_for_function('window.__copies.length === 1')
                    copied = page.evaluate('window.__copies[0]')
                    assert 'from=fixture' in copied and copied.endswith('#seats')
                    fresh = context.new_page()
                    fresh.goto(copied)
                    fresh.locator('.sidebar-toggle').click()
                    expect(fresh.locator('.reserved-list__name-input')).to_have_value('Test Ælice 🦐 123')
                    fresh.close()
                elif case in ['history-selection', 'history-room']:
                    destination = other_room if case == 'history-room' else second
                    page.evaluate("url => history.pushState({...history.state, idx:(history.state?.idx ?? 0)+1, key:'fixture-next'},'',url)", destination)
                    page.go_back()
                    page.go_forward()
                    open_sidebar()
                    if case == 'history-room':
                        expect(page.locator('.room-banner h1')).to_contain_text('Seminar Room 1-2')
                    expect(page.locator('.reserved-list__name-input')).to_have_value('Test Bob')
                elif case == 'room-picker':
                    page.locator('.back-link').click()
                    page.locator(f'a[href="/room/{ROOM_B}"]').click()
                    expect(page.locator('.room-banner h1')).to_contain_text('Seminar Room 1-2')
                    page.get_by_role('button', name='Seat 1', exact=True).focus()
                    page.keyboard.press('Enter')
                    expect(page.get_by_role('textbox', name='Name for seat 1', exact=True)).to_have_value('')
                    page.go_back()
                    page.go_back()
                    expect(page.locator('.room-banner h1')).to_contain_text('Seminar Room 1-1')
                    open_sidebar()
                    expect(page.get_by_role('textbox', name='Name for seat 1', exact=True)).to_have_value('Test Alice')
                elif case == 'mismatched-room':
                    payload = quote(encoded(ROOM_B, {'1': 'Test Bob'}))
                    page.goto(f'{base}/room/{ROOM_A}?s={payload}&from=fixture#seats')
                    expect(page.locator('.room-banner h1')).to_contain_text('Seminar Room 1-2')
                    assert 's=' in page.url and 'from=fixture' in page.url and page.url.endswith('#seats'), 'Room redirection lost the shared selection or other URL fields'
                    page.reload()
                    open_sidebar()
                    expect(page.locator('.reserved-list__name-input')).to_have_value('Test Bob')
                elif case.startswith('too-large'):
                    open_sidebar()
                    large = base64.b64encode(random.Random(17).randbytes(4096)).decode()
                    page.locator('.reserved-list__name-input').fill(large)
                    expect(page.locator('.room-view-footer')).to_contain_text('too large')
                    share = page.locator('.banner-btn-copy')
                    if share.is_enabled():
                        share.click()
                    assert page.evaluate('window.__copies.length') == 0, 'Share copied an older, incomplete selection'
                    expect(page.locator('.reserved-list__name-input')).to_have_value(large)
                    page.get_by_role('button', name='Clear All', exact=True).click()
                    expect(page.locator('.reserved-list__name-input')).to_have_count(0)
                    page.locator('.banner-btn-copy').click()
                    page.wait_for_function('window.__copies.length === 1')
                    page.reload()
                    open_sidebar()
                    expect(page.locator('.reserved-list__name-input')).to_have_count(0)
                elif case.startswith('clipboard-denied') or case == 'clipboard-unavailable':
                    if case == 'clipboard-unavailable':
                        page.evaluate("() => {Object.defineProperty(navigator,'clipboard',{configurable:true,value:undefined})}")
                    else:
                        page.evaluate("() => {navigator.clipboard.writeText=async()=>{throw new DOMException('Fixture denied','NotAllowedError')}}")
                    page.locator('.banner-btn-copy').click()
                    expect(page.get_by_role('status')).to_contain_text('Copy')
                    assert not errors, errors
                    page.evaluate("() => {Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>window.__copies.push(text)}})}")
                    page.locator('.banner-btn-copy').click()
                    page.wait_for_function('window.__copies.length === 1')
                    expect(page.get_by_role('status')).to_contain_text('copied')
                elif case == 'history-write-denied':
                    open_sidebar()
                    page.evaluate("() => {window.__replace=history.replaceState;history.replaceState=()=>{throw new DOMException('Fixture blocked','SecurityError')}}")
                    page.locator('.reserved-list__name-input').fill('Test Pending')
                    expect(page.get_by_role('status')).to_contain_text('Unable to save')
                    expect(page.locator('.banner-btn-copy')).to_be_disabled()
                    expect(page.locator('.reserved-list__name-input')).to_have_value('Test Pending')
                    page.evaluate('() => {history.replaceState=window.__replace}')
                    page.locator('.reserved-list__name-input').fill('Test Recovered')
                    page.locator('.banner-btn-copy').click()
                    page.wait_for_function('window.__copies.length === 1')
                    page.reload()
                    open_sidebar()
                    expect(page.locator('.reserved-list__name-input')).to_have_value('Test Recovered')
                elif case in ['invalid-link', 'oversized-link']:
                    payload = 'x' * 1801 if case == 'oversized-link' else 'not-a-valid-selection'
                    page.goto(f'{base}/room/{ROOM_A}?s={payload}')
                    expect(page.get_by_role('status')).to_contain_text('selection')
                    expect(page.locator('.banner-btn-copy')).to_be_disabled()
                    page.get_by_role('button', name='Seat 1', exact=True).focus()
                    page.keyboard.press('Enter')
                    page.locator('.banner-btn-copy').click()
                    page.wait_for_function('window.__copies.length === 1')
                assert not errors, errors
                assert not external, external
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal page overflow'
                heading_box = page.locator('.room-banner__center').bounding_box()
                share_box = page.locator('.banner-btn-copy').bounding_box()
                assert heading_box['x'] + heading_box['width'] <= share_box['x'], 'Room title overlaps Share'
                result.update(status='passed', external_requests=0, resolved_url=page.url)
            except Exception as error:
                result.update(status='failed', error=str(error), javascript_errors=errors)
            try:
                page.screenshot(path=str(output / f'{case}.png'), full_page=False, animations='disabled', timeout=20000)
            except Exception as error:
                result.update(status='failed', screenshot_error=str(error))
            checks.append(result)
            print(json.dumps(result), flush=True)
            context.close()
        browser.close()
    (output / 'browser-results.json').write_text(json.dumps({'base': base, 'checks': checks}, indent=2) + '\n')
    return all(check['status'] == 'passed' for check in checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base')
    parser.add_argument('--output', type=Path, default=ROOT / 'browser-results')
    parser.add_argument('--cases', nargs='+', default=['share-reload', 'share-reload-mobile', 'history-selection', 'history-room', 'room-picker', 'mismatched-room', 'too-large', 'too-large-mobile', 'clipboard-denied', 'clipboard-denied-mobile', 'clipboard-unavailable', 'history-write-denied', 'invalid-link', 'oversized-link'])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = None
    worker = None
    try:
        base = args.base
        if not base:
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(AppHandler, directory=str(ROOT / 'dist')))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f'http://127.0.0.1:{server.server_port}'
        success = run(base.rstrip('/'), args.output, args.cases)
    finally:
        if server:
            server.shutdown()
            server.server_close()
            worker.join()
    raise SystemExit(0 if success else 1)
