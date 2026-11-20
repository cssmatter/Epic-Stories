"""Upload the approved local pilot renders using existing God Is Greatest accounts."""
import json
import os
from pathlib import Path
import sys
import time
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from youtube_uploader import get_authenticated_service, upload_video

STATE_PATH = ROOT / 'data/bible-pilot/upload-state.json'
STATE = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {}
RELEASE = 'https://github.com/cssmatter/Epic-Stories/releases/download/bible-seniors-week01-pilot'

def save():
    STATE_PATH.write_text(json.dumps(STATE, indent=2) + '\n')

def metadata(kind):
    return json.loads((ROOT / f'data/bible-pilot/{kind}.json').read_text())

def graph(method, path, **params):
    response = requests.request(method, f'https://graph.facebook.com/v24.0/{path}',
        headers={'Authorization': 'Bearer ' + os.environ['IG_ACCESS_TOKEN']},
        params=params if method == 'GET' else None,
        data=params if method != 'GET' else None, timeout=90)
    data = response.json()
    if not response.ok or 'error' in data:
        err = data.get('error', {})
        raise RuntimeError(f'Instagram API error {err.get("code", response.status_code)}: {err.get("message", "Request failed")}')
    return data

def youtube(kind):
    entry = STATE.setdefault('youtube_' + kind, {})
    meta = metadata(kind)
    if not entry.get('id'):
        video_id = upload_video(str(ROOT / f'pilot-media/seniors-week-01-{kind}.mp4'),
            meta['title'], meta['description'], category_id='27',
            keywords='Bible study,Psalm 71,Christian encouragement,seniors,faith',
            token_file='token_godisgreatest.pickle',
            privacy_status=os.environ.get('YOUTUBE_PRIVACY', 'unlisted'))
        if not video_id:
            raise RuntimeError('YouTube upload did not return a video ID')
        entry.update(id=video_id, url=f'https://youtu.be/{video_id}')
        save()
    if not entry.get('comment_id'):
        client = get_authenticated_service('token_godisgreatest.pickle')
        result = client.commentThreads().insert(part='snippet', body={'snippet': {
            'videoId': entry['id'], 'topLevelComment': {'snippet': {'textOriginal': meta['comment']}}
        }}).execute()
        entry['comment_id'] = result['id']
        save()
    print(kind, entry['url'])

def instagram():
    entry = STATE.setdefault('instagram_short', {})
    meta = metadata('short')
    account = os.environ['IG_BUSINESS_ID']
    if not entry.get('id'):
        if not entry.get('container_id'):
            result = graph('POST', f'{account}/media', media_type='REELS',
                video_url=RELEASE + '/seniors-week-01-short.mp4',
                caption=meta['description'], share_to_feed='true')
            entry['container_id'] = result['id']
            save()
        for _ in range(60):
            result = graph('GET', entry['container_id'], fields='status_code,status')
            status = result.get('status_code')
            if status == 'FINISHED':
                break
            if status in ('ERROR', 'EXPIRED'):
                raise RuntimeError(f'Instagram container {status}; inspect saved container before retrying')
            if status == 'PUBLISHED':
                raise RuntimeError('Container already published; reconcile media ID before retrying to avoid duplicates')
            time.sleep(10)
        else:
            raise RuntimeError('Instagram processing timed out; container is saved for retry')
        entry['id'] = graph('POST', f'{account}/media_publish', creation_id=entry['container_id'])['id']
        save()
    if not entry.get('comment_id'):
        entry['comment_id'] = graph('POST', f'{entry["id"]}/comments', message=meta['comment'])['id']
        save()
    entry['url'] = graph('GET', entry['id'], fields='permalink')['permalink']
    save()
    print('Instagram', entry['url'])

def main():
    failures = []
    selection = os.environ.get('YOUTUBE_VIDEOS', 'both')
    jobs = [(kind, lambda kind=kind: youtube(kind)) for kind in ['short', 'long']
            if selection in ('both', kind)]
    if os.environ.get('UPLOAD_INSTAGRAM', 'false').lower() == 'true':
        jobs.append(('Instagram', instagram))
    for name, job in jobs:
        try:
            job()
        except Exception as exc:
            failures.append(name)
            print(f'::error::{name}: {exc}')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
            summary.write('## Bible Study pilot uploads\n\n')
            for name, result in STATE.items():
                summary.write(f'- {name}: {result.get("url", result.get("id", "pending"))}\n')
            if failures:
                summary.write('\nFailed steps: ' + ', '.join(failures) + '\n')
    if failures:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
