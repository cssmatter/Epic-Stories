import json
from googletrans import Translator
import re

def is_urdu(text):
    return bool(re.search(r'[\u0600-\u06FF]', text))

translator = Translator()
path = r"C:\git\youtube-automation\Epic-Stories-All-youtube-automation-shorts\scripts\shayari\output\Do Dil Mil Rahe Hain ｜ KUMAR SANU ｜ Nadeem Shravan ｜ Pardes ｜ 1997_lyrics.json"

with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data.get('lyrics_with_timestamps', []):
    line = item.get('line', '')
    if is_urdu(line):
        try:
            res = translator.translate(line, src='ur', dest='hi')
            item['line'] = res.text
            print(f"Translated: {line} -> {res.text}")
        except Exception as e:
            print(f"Error translating {line}: {e}")

old_plain = data.get('plain_lyrics', '')
new_plain = []
for line in old_plain.split('\n'):
    if is_urdu(line):
        try:
            res = translator.translate(line, src='ur', dest='hi')
            new_plain.append(res.text)
        except:
            new_plain.append(line)
    else:
        new_plain.append(line)

data['plain_lyrics'] = '\n'.join(new_plain)

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Done translating JSON.")
