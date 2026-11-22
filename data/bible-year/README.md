# Daily Bible Study campaign

365 daily pairs (730 scripts), November 23, 2026 through November 22, 2027. GitHub Actions runs at 12:30 UTC / 6:00 PM India time. GitHub schedules may start late. Each run renders a vertical Short for YouTube and Instagram and a landscape long video for YouTube.

Monday Seniors; Tuesday Kids; Wednesday Young Adults; Thursday Women; Friday Men; Saturday Couples; Sunday Beginners. These are editorial audience selections, not an analytics ranking.

`lessons.json` is a read-only export of the app's seven books. `calendar.json` contains every narration script, scene/icon instructions, scripture, dates, descriptions, hashtags, store links, and audience designation. The missing Young Adults Week 25 is an explicitly labeled recap of Week 24. Day 365 is a year-end Seniors reflection. No lesson was inserted into the app database.

Rebuild: `python scripts/bible_year/build_calendar.py`

Verify: `python -m unittest discover -s scripts/bible_year -p test_campaign.py`

Render: `python scripts/bible_year/render.py --episode day-001`

Manually dispatch **Bible Study - Daily Year Campaign** with a date to render previews. Publishing defaults off for manual runs; scheduled runs publish automatically. Reuses CLIENT_SECRETS_JSON, GODISGREATEST_TOKEN_PICKLE_BASE64, IG_ACCESS_TOKEN_GODISGREATEST, and IG_BUSINESS_ID_GODISGREATEST.

Uploads are recorded in `upload-state.json` and committed immediately. An interrupted YouTube upload is marked pending and requires reconciling the channel before retry; this prevents accidental duplicate uploads. Instagram container IDs are saved before publishing. Credentials are removed by the workflow's final step.

Kids videos declare their audience as made for kids and skip YouTube comments. Other videos attempt a download comment; a permission-denied comment leaves the store links available in the description. Instagram uses five relevant hashtags; YouTube uses twelve topic-specific hashtags. Hashtags do not guarantee reach.

Visual direction: nearly black textured canvas, mint rounded icon cards, muted gold monospaced headings, white phrase captions, scripture badge, sliding/rotating exits, and illustrated animated symbols. New graphics are a reconstruction of the supplied reference's visual grammar, not its original editable assets. Speech captions use TTS word-boundary timestamps. No paid image/video generation is required. Edge speech service availability is an external dependency.

The workflow stops selecting episodes after the campaign end date. Pause it from GitHub Actions at any time. Review the first rendered pair and the run logs before relying on unattended publishing.
