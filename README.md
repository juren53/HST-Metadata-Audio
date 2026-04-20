# HSTL Audio Metadata Project

This portion of the project will embed metadata from the Truman Library archives into approximately 2,000 audio files (WAV and MP3) for upload to the National Archives and Records Administration (NARA) catalog.

## Overview

Audio recordings from the Harry S. Truman Presidential Library are cataloged in an internal database. This project extracts that metadata, generates thumbnails, and embeds both into the audio files using standard ID3 tags before submission to the NARA catalog.

## Process Steps

1. **Export HST Audio DB metadata to a CSV file** — The source CSV includes fields such as title, accession number, date, restrictions, description, speakers, production/copyright information, and up to ten associated audio file URLs.
2. **Match audio files** — `match-audio-files.py` cross-references MP3 files in the working directory against filenames listed in the CSV, reporting matches and missing files.
3. **Create HST thumbnail with accession number** — Generate a cover image that includes the accession number for each recording.
4. **Embed thumbnail and metadata in MP3 file** — Use `ffmpeg` to write ID3v2 tags (title, date, description, speakers, etc.) and attach the thumbnail as cover art.

## CSV Metadata Fields

| Field | Description |
|---|---|
| `title` | Recording title |
| `Accession Number` | HSTL accession identifier (e.g., `SR62-122`) |
| `Date` | Recording date |
| `Restrictions` | Access restrictions |
| `Description` | Archival description of the recording |
| `Speakers` | Named speakers |
| `Production and Copyright` | Broadcast network or production credit |
| `Sound_File_1–10` | URLs to individual audio file segments |

## Scripts

### `match-audio-files.py`
Compares MP3 filenames in the current working directory against the filenames extracted from the CSV. Outputs a count of matches and a list of any unmatched files.

**Requirements:** Python 3, `pandas`

```bash
python3 match-audio-files.py
```

## Embedding Metadata with ffmpeg

To embed album art (thumbnail) into an MP3 file:

```bash
ffmpeg -i input.mp3 -i thumbnail.jpg \
  -map 0 -map 1 -c copy \
  -id3v2_version 3 \
  -metadata:s:v title="Album cover" \
  -metadata:s:v comment="Cover (Front)" \
  output.mp3
```

## Repository Structure

```
Audio/
├── match-audio-files.py     # File matching utility
├── HSTL-audio-test.csv      # Sample metadata export
├── test.csv                 # Test CSV for development
├── background/              # Reference notes on audio formats (BWF)
├── docs/                    # Project documentation
└── notes/                   # ffmpeg recipes and working notes
```

## Dependencies

- Python 3
- [pandas](https://pandas.pydata.org/)
- [ffmpeg](https://ffmpeg.org/)
