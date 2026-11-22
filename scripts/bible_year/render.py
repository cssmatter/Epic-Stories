"""Deterministic frame renderer with real speech word boundaries."""
import argparse, asyncio, base64, io, json, math, subprocess
from pathlib import Path
import edge_tts
import qrcode
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[2]
def run(args): subprocess.run(args,check=True,stdout=subprocess.DEVNULL)
def duration(p): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)]))
def uri(p): return 'data:image/png;base64,'+base64.b64encode(Path(p).read_bytes()).decode()
async def render(entry,kind,out):
    folder=out/kind;folder.mkdir(parents=True,exist_ok=True)
    scenes=[];cursor=0;audio=[]
    for i,scene in enumerate(entry[kind]):
        mp3=folder/f'{i:02}.mp3';timing=folder/f'{i:02}.json'
        if not mp3.exists() or not timing.exists():
            words=[]
            with mp3.open('wb') as f:
                async for chunk in edge_tts.Communicate(scene['text'],'en-US-GuyNeural',rate='+5%' if kind=='short' else '-5%',boundary='WordBoundary').stream():
                    if chunk['type']=='audio': f.write(chunk['data'])
                    elif chunk['type']=='WordBoundary': words.append({'word':chunk['text'],'start':chunk['offset']/1e7,'end':(chunk['offset']+chunk['duration'])/1e7})
            if not words: raise RuntimeError('No word boundaries; refusing estimated captions')
            timing.write_text(json.dumps(words),encoding='utf-8')
        words=json.loads(timing.read_text(encoding='utf-8'));d=duration(mp3)
        scenes.append({**scene,'start':cursor,'end':cursor+d,'words':[{**w,'start':w['start']+cursor,'end':w['end']+cursor} for w in words]});cursor+=d;audio.append(mp3)
    # A quiet final hold gives viewers time to scan either QR code.
    total=math.ceil((cursor+4)*30)/30;scenes[-1]['end']=total
    if kind=='short' and total>60: raise RuntimeError(f'Short too long: {total}')
    if kind=='long' and not 100<=total<=240: raise RuntimeError(f'Long narration outside 100–240 seconds: {total}')
    images={'app':uri(ROOT/'assets/bible-year/app.png')}
    for platform,url in entry['links'].items():
        b=io.BytesIO();qrcode.make(url).save(b,format='PNG');images[platform]='data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
    width,height=(720,1280) if kind=='short' else (1280,720)
    payload={'kind':kind,'scenes':scenes,'scripture':entry['scripture'],'images':images,'width':width,'height':height}
    (folder/'timeline.json').write_text(json.dumps(payload),encoding='utf-8')
    concat=folder/'audio.txt';concat.write_text('\n'.join("file '"+p.resolve().as_posix()+"'" for p in audio),encoding='utf-8')
    run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-af','apad','-t',str(total),str(folder/'voice.wav')])
    async with async_playwright() as p:
        browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
        await page.goto((Path(__file__).parent/'scene.html').as_uri());await page.evaluate('d=>setup(d)',payload)
        encoder=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-vcodec','mjpeg','-r','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',str(folder/'picture.mp4')],stdin=subprocess.PIPE)
        try:
            for frame in range(round(total*30)):
                await page.evaluate('t=>draw(t)',frame/30)
                encoder.stdin.write(await page.screenshot(type='jpeg',quality=92))
                if frame in (90,round(total*30)-45): await page.screenshot(path=str(folder/f'check-{frame}.png'))
                if frame%900==0: print(kind,frame,'/',round(total*30),flush=True)
        finally:
            encoder.stdin.close();code=encoder.wait();await browser.close()
        if code: raise RuntimeError('Video encoder failed')
    dest=out/f'{entry["id"]}-{kind}.mp4'
    run(['ffmpeg','-y','-loglevel','error','-i',str(folder/'picture.mp4'),'-i',str(folder/'voice.wav'),'-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart','-t',str(total),str(dest)])
    assert abs(duration(dest)-total)<.1
    print(dest,flush=True)

async def main():
    ap=argparse.ArgumentParser();ap.add_argument('--episode',default='day-001');ap.add_argument('--kind',choices=['short','long','both'],default='both');args=ap.parse_args()
    entries=json.loads((ROOT/'data/bible-year/calendar.json').read_text(encoding='utf-8'));entry=next(e for e in entries if e['id']==args.episode)
    for kind in (['short','long'] if args.kind=='both' else [args.kind]): await render(entry,kind,ROOT/'output/bible-year'/entry['id'])
if __name__=='__main__': asyncio.run(main())
