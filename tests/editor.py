"""Real pointer/editor regressions using disposable browser state and exports."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
import argparse
import json
import math
import re
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT/'src/data/registry.json').read_text())
ROOM = REGISTRY['rooms'][0]
DEFAULT_CASES = [f'{name}-{width}' for width in ['desktop','mobile'] for name in
                 ['cancel-add','cancel-drag','lost-capture','lost-capture-active','keyboard-bounds','edit-export','viewer-translate','viewer-zoom']]

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if not Path(self.translate_path(urlsplit(self.path).path)).is_file():
            self.path = '/index.html'
        super().do_GET()
    def log_message(self,*args): pass

def run(base,output,cases):
    checks=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for case in cases:
            width=390 if case.endswith('mobile') else 1440
            context=browser.new_context(viewport={'width':width,'height':1000},has_touch=True,reduced_motion='reduce')
            page=context.new_page()
            page.set_default_timeout(10000)
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            result={'case':case,'width':width}
            try:
                if case.startswith('viewer-'):
                    page.goto(f'{base}/room/{ROOM["id"]}')
                    frame=page.locator('.room-canvas-frame')
                    content=page.locator('.room-canvas-content')
                    expect(frame).to_be_visible()
                    transform=lambda:content.evaluate('(el)=>{const m=new DOMMatrix(getComputedStyle(el).transform);return {zoom:m.a,x:m.e,y:m.f}}')
                    before=transform()
                    bounds=frame.bounding_box()
                    y=bounds['y']+bounds['height']*.3
                    x1=bounds['x']+bounds['width']*.35
                    x2=bounds['x']+bounds['width']*.65
                    session=context.new_cdp_session(page)
                    points=[{'x':x1,'y':y,'id':1},{'x':x2,'y':y,'id':2}]
                    session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':points})
                    if case.startswith('viewer-translate'):
                        points=[{**point,'x':point['x']+30,'y':point['y']+20} for point in points]
                    else:
                        points=[{**points[0],'x':x1-20},{**points[1],'x':x2+20}]
                    session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':points})
                    page.wait_for_timeout(150)
                    session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
                    after=transform()
                    if case.startswith('viewer-translate'):
                        assert abs(after['x']-before['x']-30)<1 and abs(after['y']-before['y']-20)<1, (before,after)
                        assert abs(after['zoom']-before['zoom'])<.01, (before,after)
                    else:
                        expected=before['zoom']*((x2-x1+40)/(x2-x1))
                        assert abs(after['zoom']-expected)<.01, (before,after,expected)
                    result['viewport_before']=before;result['viewport_after']=after
                elif case=='editor-disabled':
                    page.goto(base+'/edit')
                    expect(page.locator('.editor-canvas-frame')).to_have_count(0)
                    assert urlsplit(page.url).path!='/edit'
                else:
                    page.goto(base+'/edit')
                    frame=page.locator('.editor-canvas-frame')
                    svg=frame.locator('svg')
                    expect(frame).to_be_visible()
                    expect(page.locator('[data-seat-id]')).to_have_count(len(ROOM['seats']))
                    def point(x,y):
                        return svg.evaluate('(el,p)=>{const v=new DOMPoint(p.x,p.y).matrixTransform(el.getScreenCTM());return {x:v.x,y:v.y}}',{'x':x,'y':y})
                    def position(seat_id):
                        return page.locator(f'[data-seat-id="{seat_id}"] circle').evaluate('(el)=>({x:Number(el.getAttribute("cx")),y:Number(el.getAttribute("cy"))})')
                    def select(seat):
                        pos=point(seat['x'],seat['y']);page.mouse.click(pos['x'],pos['y'])
                    def cancel(x,y):
                        frame.dispatch_event('pointercancel',{'pointerId':1,'pointerType':'mouse','button':0,'clientX':x,'clientY':y,'bubbles':True})
                        page.mouse.up()
                    if case.startswith('cancel-add') or case.startswith('lost-capture'):
                        page.get_by_role('button',name='+ Add Seat',exact=True).click()
                        pos=point(5,5)
                        page.mouse.move(pos['x'],pos['y']);page.mouse.down()
                        if case.startswith('lost-capture'):
                            if case.startswith('lost-capture-active'):
                                page.mouse.move(pos['x']+1,pos['y']+1)
                            frame.evaluate('(el)=>el.releasePointerCapture(1)')
                            page.mouse.move(pos['x']+2,pos['y']+1)
                            page.mouse.up()
                        else: cancel(pos['x'],pos['y'])
                        expect(page.locator('[data-seat-id]')).to_have_count(len(ROOM['seats']))
                        expect(page.get_by_role('button',name='Undo',exact=True)).to_be_disabled()
                    elif case.startswith('cancel-drag'):
                        seat=ROOM['seats'][0];before=position(seat['id']);pos=point(seat['x'],seat['y'])
                        page.mouse.move(pos['x'],pos['y']);page.mouse.down()
                        page.mouse.move(pos['x']+20,pos['y']+15,steps=5)
                        page.wait_for_timeout(100)
                        cancel(pos['x']+20,pos['y']+15)
                        assert position(seat['id'])==before, (before,position(seat['id']))
                        expect(page.get_by_role('button',name='Undo',exact=True)).to_be_disabled()
                    elif case.startswith('keyboard-bounds'):
                        seat=min(ROOM['seats'],key=lambda seat:seat['x']);select(seat)
                        for _ in range(math.ceil(seat['x']/10)+2):page.keyboard.press('Shift+ArrowLeft')
                        assert position(seat['id'])['x']==0, position(seat['id'])
                        page.get_by_role('button',name='Undo',exact=True).click()
                        assert position(seat['id'])['x']>0, 'Repeated boundary nudges must not consume undo steps'
                    elif case.startswith('edit-export'):
                        page.get_by_role('button',name='+ Add Seat',exact=True).click()
                        pos=point(5,5);page.mouse.click(pos['x'],pos['y'])
                        expect(page.locator('[data-seat-id]')).to_have_count(len(ROOM['seats'])+1)
                        page.keyboard.press('Shift+ArrowRight')
                        with page.expect_download() as download:
                            page.get_by_role('button',name='Export JSON',exact=True).click()
                        exported=json.loads(Path(download.value.path()).read_text())
                        assert len(exported['rooms'])==len(REGISTRY['rooms'])
                        assert exported['rooms'][1:]==REGISTRY['rooms'][1:]
                        assert exported['rooms'][0]['seats'][:-1]==ROOM['seats']
                        assert exported['rooms'][0]['seats'][-1]['x']==15
                        page.get_by_role('button',name='Undo',exact=True).click()
                        page.get_by_role('button',name='Undo',exact=True).click()
                        expect(page.locator('[data-seat-id]')).to_have_count(len(ROOM['seats']))
                        expect(page.get_by_role('button',name='Undo',exact=True)).to_be_disabled()
                        result['export_preserves_other_rooms']=True
                assert not errors, errors
                result['passed']=True
            except Exception as error:
                result.update({'passed':False,'error':str(error)})
            result['javascript_errors']=errors
            page.screenshot(path=str(output/(case+'.png')),full_page=False)
            checks.append(result)
            print(json.dumps({'case':case,'passed':result['passed']}),flush=True)
            context.close()
        browser.close()
    (output/'results.json').write_text(json.dumps(checks,indent=2)+'\n')
    return all(check['passed'] for check in checks)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--url');parser.add_argument('--dist',default='dist-editor')
    parser.add_argument('--output',default='editor-results')
    parser.add_argument('--cases',nargs='+',default=DEFAULT_CASES)
    args=parser.parse_args();output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    server=None
    if args.url:base=args.url
    else:
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/args.dist)))
        Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:passed=run(base,output,args.cases)
    finally:
        if server:server.shutdown();server.server_close()
    raise SystemExit(0 if passed else 1)
