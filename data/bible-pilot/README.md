# Seniors Week 1 pilot

Open Actions → **Bible Study Pilot - YouTube and Instagram** → **Run workflow** on `main`.

- `youtube_videos`: `both` uploads the 30-second Short and 2-minute 43-second video.
- `youtube_privacy`: defaults to `unlisted` for review; choose `public` to publish on YouTube.
- `instagram`: checked by default; publishes the Short as a visible Reel using the existing God Is Greatest Instagram account.

The workflow uses the existing God Is Greatest account secrets. Both platforms receive the app download links in the description/caption and an additional comment. Comments are not automatically pinned.

MP4s are stored in release `bible-seniors-week01-pilot`. The workflow verifies their SHA-256 hashes before uploading. Captions are included alongside the metadata for optional use.

Completed upload IDs are committed to `upload-state.json`, so rerunning normally skips completed uploads and retries missing comments. A rerun does not change the visibility of an already uploaded YouTube video. Change that in YouTube Studio if needed. If the workflow stops immediately after a remote publish but before its ID is recorded, inspect the platform before rerunning.

This workflow is manually triggered for the pilot. The existing daily God Is Greatest schedule continues independently. The 52-week campaign is not scheduled yet.

If authentication fails, refresh the existing `GODISGREATEST_TOKEN_PICKLE_BASE64` or Instagram credentials. The workflow fails visibly and records completed platform uploads even if another platform fails.
