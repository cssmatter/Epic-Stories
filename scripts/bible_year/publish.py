"""Publish a dated episode using the existing God Is Greatest credentials."""
import argparse, datetime as dt, json, os, subprocess, sys, time
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from youtube_uploader import get_authenticated_service
from googleapiclient.http import MediaFileUpload
from scripts.bible_pilot.upload import graph

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--date');ap.add_argument('--select-only',action='store_true');ap.add_argument('--preview',action='store_true');args=ap.parse_args()
    date=args.date or dt.datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()
    calendar=json.loads((ROOT/'data/bible-year/calendar.json').read_text(encoding='utf-8'))
    entry=next((e for e in calendar if e['date']==date),None)
    if args.select_only:
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write(f"episode={entry['id'] if entry else ''}\n")
        print(entry['id'] if entry else 'Outside campaign dates');return
    if not entry: raise SystemExit('Date outside campaign')
    if args.preview: print(json.dumps(entry,indent=2));return
    folder=ROOT/'output/bible-year'/entry['id'];state_path=ROOT/'data/bible-year/upload-state.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {}
    record=state.setdefault(entry['id'],{})
    def save():
        state_path.write_text(json.dumps(state,indent=2)+'\n')
        if os.environ.get('GITHUB_ACTIONS'):
            subprocess.run(['git','add',str(state_path)],check=True)
            if subprocess.run(['git','diff','--cached','--quiet']).returncode:
                subprocess.run(['git','commit','-m',f"Record {entry['id']} publishing progress [skip ci]"],check=True)
                subprocess.run(['git','pull','--rebase','origin','main'],check=True)
                subprocess.run(['git','push','origin','HEAD:main'],check=True)
    yt=get_authenticated_service('token_godisgreatest.pickle')
    for kind in ['short','long']:
        key='youtube_'+kind;r=record.setdefault(key,{})
        if r.get('pending') and not r.get('id'):raise RuntimeError(f'{key} interrupted after upload started; reconcile before retry to prevent duplicates')
        if not r.get('id'):
            r['pending']=True;save()
            body={'snippet':{'title':(entry['title']+' | '+entry['book'].replace('-',' ').title()+(' #Shorts' if kind=='short' else ''))[:100],'description':entry['description'],'tags':entry['tags'],'categoryId':'27'},'status':{'privacyStatus':'public','selfDeclaredMadeForKids':entry['made_for_kids']}}
            req=yt.videos().insert(part='snippet,status',body=body,media_body=MediaFileUpload(str(folder/f"{entry['id']}-{kind}.mp4"),chunksize=8*1024*1024,resumable=True))
            result=None
            while result is None: _,result=req.next_chunk()
            r.update(id=result['id'],pending=False,url='https://youtu.be/'+result['id']);save()
        if not entry['made_for_kids'] and not r.get('comment_id'):
            try:
                res=yt.commentThreads().insert(part='snippet',body={'snippet':{'videoId':r['id'],'topLevelComment':{'snippet':{'textOriginal':'Download our app: iOS '+entry['links']['ios']+' Android '+entry['links']['android']}}}}).execute()
                r['comment_id']=res['id'];save()
            except Exception as exc:
                if getattr(getattr(exc,'resp',None),'status',None)!=403:raise
                r['comment_warning']='Comments unavailable with current channel permissions; links remain in description.';save()
    r=record.setdefault('instagram',{});account=os.environ['IG_BUSINESS_ID']
    if not r.get('id'):
        if not r.get('container_id'):
            url=f"https://github.com/cssmatter/Epic-Stories/releases/download/bible-{entry['id']}/{entry['id']}-short.mp4"
            r['container_id']=graph('POST',f'{account}/media',media_type='REELS',video_url=url,caption=entry['instagram_caption'],share_to_feed='true')['id'];save()
        for _ in range(60):
            status=graph('GET',r['container_id'],fields='status_code')['status_code']
            if status=='FINISHED':break
            if status in ('ERROR','EXPIRED','PUBLISHED'):raise RuntimeError(f'Instagram container {status}: reconcile saved container before retry')
            time.sleep(10)
        else:raise RuntimeError('Instagram processing timed out')
        r['id']=graph('POST',f'{account}/media_publish',creation_id=r['container_id'])['id'];save()
    r['url']=graph('GET',r['id'],fields='permalink')['permalink'];save()
    if not r.get('comment_id'):
        try:
            r['comment_id']=graph('POST',f"{r['id']}/comments",message='Download our app: iOS '+entry['links']['ios']+' Android '+entry['links']['android'])['id'];save()
        except RuntimeError as exc:
            if not str(exc).startswith('Instagram API error 10:'):raise
            r['comment_warning']='Comment permission unavailable; download links remain in the caption.';save()
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:
            f.write('\n'.join(f"- {key}: {value.get('url','pending')}" for key,value in record.items()))
if __name__=='__main__':main()
