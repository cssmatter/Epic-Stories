
import os
import sys
from youtube_uploader import upload_video

# Metadata for "The 90-Second Rule"
title = "How to Never Get Angry: The 90-Second Rule for Emotional Mastery"
description = (
    "Stop letting people ruin your day. Discover the neurological secret of the 90-second rule, "
    "the truth about the button-pusher myth, and how to use the observer self to maintain unshakable peace.\n\n"
    "#90SecondRule #SelfMastery #Mindfulness #AngerManagement #MentalHealth #PersonalGrowth #Calm #Resilience"
)
tags = "anger management,90 second rule,emotional intelligence,mindfulness,self-improvement,mental strength,how to stay calm,resilience,psychology hacks"

video_path = os.path.abspath("output/epicstories/epic_story.mp4")
thumbnail_path = os.path.abspath("output/epicstories/thumbnail.png")

if __name__ == "__main__":
    print(f"Uploading: {title}")
    try:
        video_id = upload_video(
            file_path=video_path,
            title=title,
            description=description,
            keywords=tags,
            thumbnail=thumbnail_path,
            privacy_status='private'
        )
        if video_id:
            print(f"SUCCESS! Video ID: {video_id}")
    except Exception as e:
        print(f"FAILED: {e}")
