import json
import os
import urllib.parse
from datetime import datetime
from email.utils import format_datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Base URL for GitHub Pages
BASE_URL = "https://cssmatter.github.io/Epic-Stories/"
FEED_TITLE = "Book Summaries Podcast"
FEED_LINK = BASE_URL + "assets/BookSummariesChannel/feed.xml"
FEED_DESC = "Audio summaries of the world's best books, helping you learn and grow."
FEED_LANGUAGE = "en-us"
FEED_AUTHOR = "BookSummariesChannel"
FEED_IMAGE = BASE_URL + "assets/BookSummariesChannel/podcast_cover.jpg" # We should have a cover if possible, fallback to placeholder
FEED_CATEGORY = "Education"

def generate_rss(json_path, output_xml_path):
    # Load metadata
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Sort episodes by pubDate descending (latest first)
    # The pubDate is currently like "2026-01-20 16:18:23 +0530"
    def parse_date(date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            return datetime.now()

    data.sort(key=lambda x: parse_date(x.get("pubDate", "")), reverse=True)

    # RSS Root
    rss = ET.Element("rss", {
        "version": "2.0",
        "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "xmlns:content": "http://purl.org/rss/1.0/modules/content/"
    })

    channel = ET.SubElement(rss, "channel")

    # Channel metadata
    ET.SubElement(channel, "title").text = FEED_TITLE
    ET.SubElement(channel, "link").text = FEED_LINK
    ET.SubElement(channel, "description").text = FEED_DESC
    ET.SubElement(channel, "language").text = FEED_LANGUAGE
    ET.SubElement(channel, "itunes:author").text = FEED_AUTHOR
    
    # Optional image for podcast
    image = ET.SubElement(channel, "image")
    ET.SubElement(image, "url").text = FEED_IMAGE
    ET.SubElement(image, "title").text = FEED_TITLE
    ET.SubElement(image, "link").text = FEED_LINK

    itunes_image = ET.SubElement(channel, "itunes:image", {"href": FEED_IMAGE})
    ET.SubElement(channel, "itunes:category", {"text": FEED_CATEGORY})
    ET.SubElement(channel, "itunes:explicit").text = "false"

    # Add episodes
    for item_data in data:
        folder_name = item_data.get("folder_name", "")
        if not folder_name:
            continue

        item = ET.SubElement(channel, "item")
        
        ET.SubElement(item, "title").text = item_data.get("title", folder_name)
        ET.SubElement(item, "description").text = item_data.get("description", "")
        ET.SubElement(item, "itunes:summary").text = item_data.get("description", "")

        pub_date = parse_date(item_data.get("pubDate", ""))
        ET.SubElement(item, "pubDate").text = format_datetime(pub_date)

        # Enclosure (MP3 file)
        # Assuming the MP3 file is named exactly like the folder name
        mp3_filename = f"{folder_name}.mp3"
        # URL encode the paths, replacing spaces with %20
        encoded_folder = urllib.parse.quote(folder_name)
        encoded_file = urllib.parse.quote(mp3_filename)
        
        mp3_url = f"{BASE_URL}assets/BookSummariesChannel/{encoded_folder}/{encoded_file}"
        
        # We need the size in bytes to be fully valid. For generation speed, we can make it up if file is missing,
        # but let's try to get actual size if run locally.
        local_mp3_path = os.path.join(os.path.dirname(output_xml_path), folder_name, mp3_filename)
        file_size = 0
        if os.path.exists(local_mp3_path):
            file_size = os.path.getsize(local_mp3_path)
        else:
            file_size = 10000000 # Dummy 10MB if file not found during generation

        ET.SubElement(item, "enclosure", {
            "url": mp3_url,
            "type": "audio/mpeg",
            "length": str(file_size)
        })

        # GUID (Unique identifier)
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = mp3_url

        # Author and Image for this episode
        ET.SubElement(item, "itunes:author").text = item_data.get("author", FEED_AUTHOR)
        
        # Try to find thumbnail
        thumbnail_filename = "thumbnail_3000x3000.jpg"
        local_thumb_path = os.path.join(os.path.dirname(output_xml_path), folder_name, thumbnail_filename)
        if os.path.exists(local_thumb_path):
            encoded_thumb = urllib.parse.quote(thumbnail_filename)
            thumb_url = f"{BASE_URL}assets/BookSummariesChannel/{encoded_folder}/{encoded_thumb}"
            ET.SubElement(item, "itunes:image", {"href": thumb_url})

    # Prettify the XML
    rough_string = ET.tostring(rss, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    with open(output_xml_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)
    
    print(f"Generated RSS feed successfully at {output_xml_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # The script is in scripts/book_summaries/
    # The assets are in assets/BookSummariesChannel/
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    assets_dir = os.path.join(project_root, "assets", "BookSummariesChannel")
    
    json_path = os.path.join(assets_dir, "podcast_data.json")
    output_xml_path = os.path.join(assets_dir, "feed.xml")
    
    # Generate the podcast feed
    generate_rss(json_path, output_xml_path)
