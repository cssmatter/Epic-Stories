import datetime as dt
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

class CampaignTests(unittest.TestCase):
    def test_full_year_and_sources(self):
        entries=json.loads((ROOT/'data/bible-year/calendar.json').read_text(encoding='utf-8'))
        lessons=json.loads((ROOT/'data/bible-year/lessons.json').read_text(encoding='utf-8'))
        self.assertEqual(len(entries),365)
        for i,e in enumerate(entries):
            self.assertEqual(e['date'],str(dt.date(2026,11,23)+dt.timedelta(days=i)))
            source=next(l for l in lessons if l['book_id']=='52-week-bible-study-for-'+e['book'] and l['week_number']==e['source_week'])
            self.assertEqual(e['scripture'],source['scripture'])
            for kind in ['short','long']:
                self.assertTrue(all(s['text'].strip() for s in e[kind]))
                words=sum(len(s['text'].split()) for s in e[kind])
                self.assertTrue(35<=words<=90 if kind=='short' else 240<=words<=400,(e['id'],kind,words))
            self.assertEqual(e['made_for_kids'],e['book']=='kids')
            self.assertLessEqual(e['instagram_caption'].count('#'),5)
        self.assertEqual(sum(e['editorial_recap'] for e in entries),2)

    def test_actual_caption_timing(self):
        for path in (ROOT/'output/bible-year/day-001').glob('*/timeline.json'):
            data=json.loads(path.read_text(encoding='utf-8'))
            for s in data['scenes']:
                previous=s['start']
                for w in s['words']:
                    self.assertGreaterEqual(w['start'],previous)
                    self.assertGreaterEqual(w['end'],w['start'])
                    self.assertLessEqual(w['end'],s['end']+.05)
                    previous=w['start']

if __name__=='__main__':unittest.main()
