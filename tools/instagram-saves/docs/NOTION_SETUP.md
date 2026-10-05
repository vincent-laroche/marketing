# Notion Setup

## Create the Integration

1. Go to Notion integrations.
2. Create an internal integration.
3. Copy the integration token into `.env` as `NOTION_TOKEN`.
4. Share both target databases with the integration.

## Find Database IDs

Open each database as a full page. Copy the long ID from the URL and paste it into:

- `NOTION_INSTAGRAM_SAVES_DATABASE_ID`
- `NOTION_CONTENT_IDEAS_DATABASE_ID`

## Instagram Saves Properties

- `Name`: title
- `Status`: select: `New`, `Reviewed`, `Processed`, `Skipped`, `Error`
- `Collection`: select
- `Caption`: rich_text
- `Author`: rich_text
- `Username`: rich_text
- `Instagram URL`: url
- `Media ID`: rich_text
- `Shortcode`: rich_text
- `Type`: select: `Post`, `Reel`, `Carousel`, `IGTV`, `Unknown`
- `Saved At`: date
- `Synced At`: date
- `Last Seen At`: date
- `Source`: select: `Instagram Saved`
- `Raw JSON`: rich_text
- `Processing Notes`: rich_text
- `Content Idea Created`: checkbox
- `Content Idea URL`: url
- `Audio Transcript`: rich_text
- `On-Screen Text`: rich_text
- `Combined Script`: rich_text
- `Transcription Status`: select: `not_requested`, `completed`, `empty`, `error`, `skipped_non_reel`
- `OCR Status`: select: `pending`, `completed`, `empty`, `error`, `missing_screenshots`
- `Source Extract JSON Path`: rich_text
- `Extraction Notes`: rich_text

## Content Ideas Properties

- `Name`: title
- `Status`: select: `Draft`, `Reviewed`, `Approved`, `In Production`, `Published`, `Archived`
- `Priority`: select: `High`, `Medium`, `Low`
- `Pillar`: select: `Education`, `Trust`, `Product Guidance`, `Maintenance`, `Objection Handling`, `Founder POV`, `Customer Journey`
- `Platform`: multi_select: `Instagram`, `TikTok`, `YouTube Shorts`, `YouTube Long-form`, `Blog`, `Email`
- `Format`: select: `Reel`, `Carousel`, `Short Video`, `Long-form Video`, `Static Post`, `Story`, `Email`, `Blog`
- `Angle`: rich_text
- `Hook Options`: rich_text
- `Outline`: rich_text
- `CTA`: rich_text
- `Script Draft`: rich_text
- `Source Instagram URL`: url
- `Source Author`: rich_text
- `Source Media ID`: rich_text
- `Week Of`: date
- `Created From Save`: checkbox
- `Created At`: date
- `Notes`: rich_text

Run:

```bash
instagram-saves validate-notion
```

Fix any missing property names before syncing.
