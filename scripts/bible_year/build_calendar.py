"""Build a reproducible campaign from the app's read-only lesson export."""
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/bible-year'
BOOKS = ['seniors', 'kids', 'young-adults', 'women', 'men', 'couples', 'beginners']
LINKS = {'ios': 'https://apps.apple.com/app/id6770936148', 'android': 'https://play.google.com/store/apps/details?id=com.cssmatter.biblestudylibrary'}

def clean(text):
    return re.sub(r'\s+', ' ', str(text).replace('\\n', ' ')).strip()

def sentences(text, limit):
    parts = re.split(r'(?<=[.!?])\s+', clean(text))
    out = []
    for part in parts:
        if len((' '.join(out) + ' ' + part).split()) > limit:
            break
        out.append(part)
    return ' '.join(out)

def build():
    lessons = json.loads((DATA / 'lessons.json').read_text(encoding='utf-8'))
    lookup = {(x['book_id'].split('for-')[-1], x['week_number']): x for x in lessons}
    entries = []
    start = dt.date(2026, 11, 23)
    for day in range(365):
        book, week = BOOKS[day % 7], day // 7 + 1
        recap = day == 364 or (book, week) not in lookup
        source = lookup[(book, min(week, 52) if day == 364 else week - 1 if recap else week)]
        sections = {x['type']: clean(x.get('body', '')) for x in source['sections']}
        title = ('A Year of Faith: Reflect and Begin Again' if day == 364 else 'Pause and Practice: ' + source['title']) if recap else source['title']
        audience = book.replace('-', ' ').title()
        hook = f'{audience}: take one small step in faith today.'
        takeaway = sentences(sections.get('key_takeaway', sections.get('lesson', '')), 32)
        if not takeaway:
            takeaway = sentences(sections.get('lesson', ''), 45)
        cta = 'Continue in the 52 Week Bible Study app. Download on iOS and Android.'
        short = [
            {'title': 'GROW IN FAITH', 'text': hook, 'icon': 'seed'},
            {'title': 'READ', 'text': f"Our reading is {source['scripture']}.", 'icon': 'book'},
            {'title': 'REFLECT', 'text': takeaway, 'icon': 'heart'},
            {'title': 'YOUR NEXT STEP', 'text': 'Read this passage. Write one thought, and pray about your next step.', 'icon': 'prayer'},
            {'title': 'BEGIN TODAY', 'text': cta, 'icon': 'app'},
        ]
        long = [{'title': title.upper(), 'text': f"Welcome to {audience}, week {min(week,52)}. {hook} Today we explore {title}. Our reading is {source['scripture']}.", 'icon': 'book'}]
        for typ, label, icon, limit in [('opening_story','THE STORY','seed',65),('lesson','THE LESSON','book',65),('what_it_means','FOR YOUR LIFE','heart',55),('key_takeaway','REMEMBER','sun',40),('reflection','PAUSE AND REFLECT','journal',40),('challenge','ONE SMALL STEP','path',45),('closing_prayer','LET US PRAY','prayer',65)]:
            text = sentences(sections.get(typ, ''), limit)
            if text:
                long.append({'title': label, 'text': text, 'icon': icon})
        long.append({'title': 'CONTINUE YOUR JOURNEY', 'text': cta + ' Find this book and weekly lesson in the app. Save this video and return to the reflection during your week.', 'icon': 'app'})
        tags = ['BibleStudy','ChristianFaith','DailyDevotional','BibleStudyApp','Scripture','Prayer','FaithJourney',audience.replace(' ', '')+'BibleStudy','ChristianEncouragement','GrowInFaith','BibleReflection','52WeekBibleStudy']
        description = f"{title} | {audience} | Week {min(week,52)}\nRead: {source['scripture']}\n\nDownload our Bible Study app:\niOS: {LINKS['ios']}\nAndroid: {LINKS['android']}\n\n" + ' '.join('#'+x for x in tags)
        entries.append({'id': f'day-{day+1:03}', 'date': str(start+dt.timedelta(days=day)), 'book':book,'week': min(week,52),'title':title,'scripture':source['scripture'],'source_week':source['week_number'],'editorial_recap':recap,'made_for_kids':book=='kids','short':short,'long':long,'description':description,'instagram_caption':description.split('\n\n#')[0]+'\n\n'+' '.join('#'+x for x in tags[:5]),'tags':tags,'links':LINKS})
    assert len(entries)==365 and len({e['date'] for e in entries})==365
    (DATA/'calendar.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
    (DATA/'calendar.csv').write_text('date,episode,book,week,recap\n'+'\n'.join(f"{e['date']},{e['id']},{e['book']},{e['week']},{e['editorial_recap']}" for e in entries)+'\n',encoding='utf-8')
    print(f'Built {len(entries)} daily pairs: 730 narration scripts.')

if __name__ == '__main__':
    build()
