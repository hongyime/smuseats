"""Verify cold-load budgets, route recovery and room filters without external services."""
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit, parse_qs, quote
import argparse, hashlib, json

from playwright.sync_api import sync_playwright, expect
from browser import AppHandler, encoded

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / 'src/data/registry.json').read_text())
ROOM = REGISTRY['rooms'][1]


def run(base, output, baseline):
    checks = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for width in [1440, 390]:
            for case in ['home-and-rooms', 'filter-cascade', 'room-data', 'compare', 'chunk-recovery']:
                if baseline and case == 'chunk-recovery':
                    continue
                context = browser.new_context(viewport={'width': width, 'height': 1000}, service_workers='block', reduced_motion='reduce')
                page = context.new_page()
                page.set_default_timeout(10000)
                requests, responses, external, errors = [], [], [], []
                def route_handler(route):
                    if urlsplit(route.request.url).netloc != urlsplit(base).netloc or route.request.method != 'GET':
                        external.append(route.request.url)
                        route.abort()
                    else:
                        route.continue_()
                context.route('**/*', route_handler)
                page.on('request', lambda req: requests.append(req.url))
                page.on('response', lambda res: responses.append(res) if res.request.resource_type == 'script' else None)
                page.on('pageerror', lambda error: errors.append(str(error)))
                result = {'case': case, 'width': width}
                try:
                    if case == 'home-and-rooms':
                        page.goto(base, wait_until='networkidle')
                        expect(page.get_by_role('heading', name='SMU Seats', exact=True)).to_be_visible()
                        result['home_js_bytes'] = sum(len(res.body()) for res in responses)
                        result['home_js_paths'] = [urlsplit(res.url).path for res in responses]
                        assert not any('/maps' in urlsplit(url).path for url in requests)
                        expect(page.locator('.building-card')).to_have_count(7)
                        assert result['home_js_bytes'] < 330000, result
                        page.get_by_role('link', name='Browse Rooms').click()
                        expect(page.locator('.room-card')).to_have_count(98)
                        rendered = page.locator('.room-card').evaluate_all("elements => Object.fromEntries(elements.map(el => [el.getAttribute('href'), Number(el.querySelector('.badge--muted').textContent.split(' ')[0])]))")
                        assert rendered == {'/room/' + room['id']: len(room['seats']) for room in REGISTRY['rooms']}
                        assert not any('RoomView-' in url or 'registry-' in url or 'Compare-' in url for url in requests), requests
                    elif case == 'filter-cascade':
                        page.goto(base + '/rooms?building=YPHSL&floor=5&type=Seminar+Room')
                        page.locator('.filter-group').first.get_by_role('button', name='Admin').click()
                        expect(page.locator('.room-card')).not_to_have_count(0)
                        assert 'floor' not in parse_qs(urlsplit(page.url).query), page.url
                        assert 'type' not in parse_qs(urlsplit(page.url).query), page.url
                        page.reload()
                        expect(page.locator('.room-card')).not_to_have_count(0)
                    elif case == 'room-data':
                        page.goto(base + '/room/' + ROOM['id'])
                        expect(page.locator('.seat')).to_have_count(len(ROOM['seats']))
                        page.wait_for_function("Array.from(document.querySelectorAll('.room-canvas-content img')).some(img=>img.complete && img.naturalWidth>0)")
                        page.get_by_role('button', name='Seat 1', exact=True).focus()
                        page.keyboard.press('Enter')
                        expect(page.locator('.reserved-list__name-input')).to_have_count(1)
                    elif case == 'compare':
                        page.goto(base + '/compare')
                        expect(page.get_by_role('heading', name='Image Enhancement Comparison')).to_be_visible()
                        page.wait_for_function("document.querySelectorAll('canvas').length===3 && Array.from(document.querySelectorAll('canvas')).every(c=>c.width>300 && c.height>300)")
                    else:
                        context.route('**/assets/RoomView-*.js', lambda route: route.abort())
                        selection = quote(encoded(ROOM['id'], {'1': 'Retry fixture'}))
                        page.goto(base + '/room/' + ROOM['id'] + '?s=' + selection + '&from=loading-fixture#seats')
                        expect(page.get_by_role('heading', name='This page could not load')).to_be_visible()
                        expect(page.get_by_role('button', name='Reload page')).to_be_visible()
                        page.screenshot(path=str(output / f'chunk-error-{width}.png'), animations='disabled')
                        context.unroute('**/assets/RoomView-*.js')
                        page.get_by_role('button', name='Reload page').click()
                        expect(page.locator('.seat')).to_have_count(len(ROOM['seats']))
                        assert page.url.endswith('&from=loading-fixture#seats'), page.url
                        page.locator('.sidebar-toggle').click()
                        expect(page.locator('.reserved-list__name-input')).to_have_value('Retry fixture')
                    assert not errors, errors
                    assert not external, external
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'
                    result.update(status='passed', external_requests=0, javascript_errors=0)
                except Exception as error:
                    result.update(status='failed', error=str(error), javascript_errors=errors)
                page.screenshot(path=str(output / f'{case}-{width}.png'), animations='disabled')
                checks.append(result)
                print(json.dumps(result), flush=True)
                context.close()
        browser.close()
    (output / 'results.json').write_text(json.dumps({'base': base, 'baseline': baseline, 'checks': checks}, indent=2) + '\n')
    return all(check['status'] == 'passed' for check in checks)


def verify_artifacts(dist, baseline):
    public = ROOT / 'public'
    preserved = []
    omitted = []
    for source in public.rglob('*'):
        if not source.is_file():
            continue
        relative = source.relative_to(public)
        target = dist / relative
        diagnostic = relative.parts[:2] == ('maps', 'debug')
        if diagnostic and not baseline:
            assert not target.exists(), f'Diagnostic output copied into deployment: {relative}'
            omitted.append({'path': str(relative), 'bytes': source.stat().st_size})
        else:
            assert target.is_file(), f'Missing public asset: {relative}'
            assert hashlib.sha256(source.read_bytes()).digest() == hashlib.sha256(target.read_bytes()).digest(), relative
            preserved.append(str(relative))
    return {'preserved_public_files': len(preserved), 'excluded_diagnostic_files': len(omitted),
            'excluded_diagnostic_bytes': sum(x['bytes'] for x in omitted),
            'deployed_public_bytes': sum((dist / p).stat().st_size for p in preserved),
            'registry_rooms': len(REGISTRY['rooms']), 'registry_seats': sum(len(r['seats']) for r in REGISTRY['rooms'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base')
    parser.add_argument('--dist', type=Path, default=ROOT / 'dist')
    parser.add_argument('--output', type=Path, default=ROOT / 'loading-results')
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = None
    try:
        base = args.base
        if not base:
            artifact = verify_artifacts(args.dist, args.baseline)
            (args.output / 'artifacts.json').write_text(json.dumps(artifact, indent=2) + '\n')
            print(json.dumps(artifact), flush=True)
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(AppHandler, directory=str(args.dist)))
            worker = Thread(target=server.serve_forever, daemon=True)
            worker.start()
            base = f'http://127.0.0.1:{server.server_port}'
        success = run(base.rstrip('/'), args.output, args.baseline)
    finally:
        if server:
            server.shutdown()
            server.server_close()
            worker.join()
    raise SystemExit(0 if success else 1)
