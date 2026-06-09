# HST Audio Metadata Analysis — Process Notes

**Date:** 2026-06-08-2026  
**Script:** `build_tabs.py`  
**Output:** `HST_Audio_Analysis_YYYY-MM-DD-HHMM.xlsx`

---

## Overview

This analysis compares sound recording metadata from two sources — the NARA catalog and the Truman Library's Drupal website — to identify discrepancies, prepare catalog updates, and adapt unpublished-in-catalog records for bulk cataloging submission. The output workbook contains eight tabs organized around two goals:

**Comparison and cleanup (Tabs 1–5):** Side-by-side analysis of the 812 records present in both sources, surfacing differences in titles, accession numbers, and descriptions, plus the 27 records that exist in the catalog but not in Drupal.

**Catalog submissions and updates (Tabs 6–8):** The 181 Drupal records published online but not yet in the NARA catalog (Tab 6), mapped to the bulk cataloging template for new submissions (Tab 7); and the 812 matched records mapped to the same template format for catalog updates, with rebuilt scope notes incorporating Production and Copyright data that was never migrated (Tab 8).

---

## Input Files

| File | Description |
|---|---|
| `HST-SRC_ALL_DrupalExport_2026-05-07_edited.csv` | Drupal export of all sound recordings (published and unpublished), with some columns removed. 1,177 records. |
| `HST-SRC_ALL_catalog-export-20260507.csv` | NARA catalog export of published sound recordings. 838 records. |
| `LAA_2ndDraft_SoundRec_Template-BulkVer10-19-23.xlsx` | Sound Recording bulk cataloging template (work in progress). Used as the target format for Priority 2 mapping. |

---

## How the Script Works

The script (`build_tabs.py`) is a Python script using `pandas` and `openpyxl`. It reads both CSVs, performs comparisons and transformations, and writes a single Excel file with eight named tabs.

### Key join logic

The two sources are joined on their respective NAID fields:
- Drupal column: `NAID`
- Catalog column: `naId`

Records are split into three populations before any tab is built:
- **Matched** — NAID present in both sources (811 common NAIDs)
- **Catalog-only** — NAID in catalog but not in Drupal (27 records)
- **Drupal/no-NAID** — Drupal records with a blank NAID field (365 records)

Within the Drupal/no-NAID population, **published** records are identified by the presence of a URL in the `Sound Recording` column (181 records).

---

## Output Tabs

### Tab 1 — `Matched_Combined` (812 rows)

An inner join of all matched records. Every column from both sources is included, with `drupal_` and `catalog_` prefixes applied to all columns to avoid ambiguity. The shared `NAID` appears as the first column. Sorted by NAID.

**Purpose:** Complete side-by-side view of all data for matched records before any targeted cleanup.

---

### Tab 2 — `Description_Update` (812 rows)

For all matched records, isolates the fields relevant to updating catalog descriptions.

Columns: `NAID` | `Accession Number` | `Catalog_scopeAndContentNote` | `Drupal_Description` | `Drupal_ProductionAndCopyright`

**Purpose:** All catalog descriptions need to be updated because the Production and Copyright information was not migrated. This tab provides the source data needed for that update.

---

### Tab 3 — `Title_Mismatch` (597 rows)

Matched records where the Drupal title and catalog title differ. Comparison is case-insensitive with leading/trailing whitespace stripped.

Columns: `NAID` | `Accession Number` | `Catalog_Title` | `Drupal_Title`

**Purpose:** Identify title discrepancies that need to be resolved in the catalog. The high count (~74% of matched records) suggests many differences may be minor formatting variations rather than substantive changes — review recommended before batch updating.

---

### Tab 4 — `AccNum_LocalID_Mismatch` (5 rows)

Matched records where the Drupal `Accession Number` and the catalog `localIdentifier` differ (case-insensitive, stripped comparison).

Columns: `NAID` | `Catalog_LocalIdentifier` | `Drupal_AccessionNumber`

**Purpose:** Flag the small number of records where these identifiers are out of sync.

---

### Tab 5 — `Catalog_Only` (27 rows)

All catalog records whose `naId` does not appear in the Drupal `NAID` column. All catalog columns are included. Sorted by `naId`.

**Purpose:** Identify records that exist in the NARA catalog but are not represented in Drupal — potential gaps, duplicates, or records that need to be re-evaluated.

---

### Tab 6 — `Drupal_NoNAID_Published` (181 rows)

Drupal records where the `NAID` field is blank and a URL is present in the `Sound Recording` column. All original Drupal columns are included.

**Purpose:** Source data for the 181 published sound recordings that have not yet been cataloged in NARA. These records are the input for the template mapping (Tab 7).

---

### Tab 7 — `Template_Mapped` (181 rows)

The 181 published/no-NAID Drupal records adapted to the column structure of the Sound Recording bulk cataloging template (`LAA_2ndDraft_SoundRec_Template-BulkVer10-19-23.xlsx`, sheet `Template-Bulk`).

Helper columns (prefixed with `[...]`) are included alongside mapped columns so source data is visible for review before submission.

#### Field mapping

| Template column | Source | Notes |
|---|---|---|
| `dataControlGroup` | Static | `PL-HST` |
| `collectionIdentifier` | Static | `HST-SRC` |
| `parentSeries` | Static | `310670814` (Truman series NAID) |
| `title` | Drupal `title` | |
| `generalRecordsType` | Static | `Sound Recordings` |
| `copyStatus` | Static | `Preservation-Reference` |
| `specificMediaType` | Drupal `Original Format(s)` → format lookup | See format lookup table below |
| `generalMediaType` | Drupal `Original Format(s)` → format lookup | See format lookup table below |
| `dimensions` | Drupal `Original Format(s)` → format lookup | See format lookup table below |
| `format` | Drupal `Original Format(s)` → format lookup | Non-empty only for compact disc |
| `accessRestrictionStatus` | Static | `Unrestricted` |
| `useRestrictionStatus` | Drupal `Restrictions` → restriction lookup | See restriction lookup table below |
| `specificUseRestriction` | Drupal `Restrictions` → restriction lookup | See restriction lookup table below |
| `useRestrictionNote` | Drupal `Restrictions` → restriction lookup | See restriction lookup table below |
| `productionDateMonth` | Parsed from Drupal `Date` | See date parsing notes below |
| `productionDateDay` | Parsed from Drupal `Date` | See date parsing notes below |
| `productionDateYear` | Parsed from Drupal `Date` | See date parsing notes below |
| `productionDateQualifier` | Parsed from Drupal `Date` | `ca.` if present in date string |
| `localIdentifier` | Drupal `Accession Number` | |
| `scopeAndContentNote` | Combined: Drupal `Description` + `Production and Copyright` | See scope note formula below |
| `[Description]` | Drupal `Description` | Helper column — source for scope note |
| `[ProductionAndCopyright]` | Drupal `Production and Copyright` | Helper column — source for scope note |
| `topicalSubject` | Drupal `Keywords` | |
| `geographicReference` | Drupal `Place` | |
| `organizationalReference` | *(blank)* | No clear Drupal source; review manually |
| `personalReference` | Drupal `People Mentioned` | |
| `variantControlNumberType` | *(blank)* | Not in Drupal export |
| `variantControlNumber` | *(blank)* | Not in Drupal export |
| `variantControlNumberNote` | *(blank)* | Not in Drupal export |
| `editStatus` | Drupal `Excerpt or Complete` | `Complete` → `N`; `Excerpt` → `Y`; blank → blank |
| `recordingSpeed` | Drupal `Recording Speed` → speed lookup | See recording speed lookup table below |
| `runningTime` | *(blank)* | Not in Drupal export |
| `personalContributor` | Drupal `Speakers` | |
| `staffOnlyNote` | Combined: Drupal `Internal Note` + `Preservation` | Joined with ` \| ` separator |
| `[InternalNote]` | Drupal `Internal Note` | Helper column — source for staff note |
| `[PreservationNote]` | Drupal `Preservation` | Helper column — source for staff note |
| `personalDonor` | *(blank)* | Not in Drupal export |
| `organizationalDonor` | *(blank)* | Not in Drupal export |
| `custodialHistoryNote` | Drupal `Related Collection` | Prefixed with "Transferred to the sound recordings from the…" if non-empty |
| `[RelatedCollection]` | Drupal `Related Collection` | Helper column — source for custodial note |
| `accessFilename` | Extracted from Drupal `Sound Recording` URL | Filename portion only (after last `/`) |
| `[soundRecordingURL]` | Drupal `Sound Recording` | Helper column — full URL for reference |

#### Format lookup table

| Drupal `Original Format(s)` | `specificMediaType` | `generalMediaType` | `dimensions` |
|---|---|---|---|
| `disc, 16-inch` | Audio Disc | Magnetic Media | 16 inch |
| `disc, 12-inch` | Audio Disc | Magnetic Media | 12 inch |
| `disc, 10-inch` | Audio Disc | Magnetic Media | 10 inch |
| `disc, 7-inch` | Audio Disc | Magnetic Media | 7 inch |
| `flexible disc` | Audio Disc | Magnetic Media | *(blank)* |
| `reel-to-reel` | Audio Tape/Reel | Magnetic Media | *(blank)* |
| `cassette` | Magnetic Tape Cassette | Magnetic Media | *(blank)* |
| `microcassette` | Magnetic Tape Cassette | Magnetic Media | *(blank)* |
| `compact disc` | Optical Disk: Compact Disk | Optical | *(blank)* |
| `wire recording` | Wire Recording | Magnetic Media | *(blank)* |
| *(blank — 12 records)* | *(blank)* | *(blank)* | *(blank)* |

#### Recording speed lookup table

| Drupal `Recording Speed` | Template `recordingSpeed` |
|---|---|
| `7-1/2 ips` | Audio Tape: 7 1/2 ips |
| `3-3/4 ips` | Audio Tape: 3 3/4 ips |
| `1-7/8 ips` | Audio Tape: 1 7/8 ips |
| `15 ips` | Audio Tape: 15 ips |
| `33-1/3 rpm` | Audio Disk: 33 1/3 rpm |
| `45 rpm` | Audio Disk: 45 rpm |
| `78 rpm` | Audio Disk: 78 rpm |
| *(blank — 90 records)* | *(blank)* | |

#### Restriction lookup table

| Drupal `Restrictions` | `useRestrictionStatus` | `specificUseRestriction` | `useRestrictionNote` |
|---|---|---|---|
| `Unrestricted` | Unrestricted | *(blank)* | *(blank)* |
| `Restricted` | Restricted | Copyright | This Item is restricted fully due to copyright. |
| `Undetermined` | Undetermined | *(blank)* | The copyright status of this recording is unknown. |

#### Scope note formula

If `Production and Copyright` is non-empty:
```
{Description}

Production and Copyright info:
{Production and Copyright}
```

If `Production and Copyright` is blank, the scope note is just the `Description` text.

#### Date handling (Tab 7 — no-NAID records only)

These records have no catalog entry, so all date information must be parsed from the Drupal `Date` free-text field. The parser handles:

| Date format in Drupal | Example | Handling |
|---|---|---|
| `DD-Mon-YY` | `17-Oct-52` | Parsed; 2-digit year treated as 1900s |
| `Month DD, YYYY` | `September 21, 1946` | Parsed normally |
| `YYYY` | `1961` | Year only; month and day left blank |
| Date ranges (`\n - `) | `Sep 21, 1946\n - Oct 22, 1947` | First date taken; range discarded |
| Year ranges | `1961\n - 1962` | First year taken |
| Contains `ca.` | `ca. 1948` | `ca.` removed from date; `productionDateQualifier` set to `ca.` |
| *(blank — 5 records)* | | All date fields left blank |

---

### Tab 8 — `Template_Matched` (812 rows)

The 812 matched records (present in both Drupal and the NARA catalog) adapted to the bulk cataloging template columns for use as **catalog update records**. Because these records already exist in the catalog, the primary purpose of this tab is to supply the corrected and completed field values — most importantly the rebuilt `scopeAndContentNote` incorporating Production and Copyright data that was never migrated to the catalog.

Helper columns (prefixed with `[...]`) are included for review, including `[Catalog_Title]` and `[Catalog_scopeAndContentNote]` to allow direct comparison with existing catalog values.

**Note on the one duplicate NAID (325599974):** This NAID maps to two distinct physical items in Drupal (SR90-56-2 and SR90-56-3) but a single catalog record. Both Drupal rows are preserved in this tab; the shared catalog data populates both rows identically.

#### Field mapping

| Template column | Source | Notes |
|---|---|---|
| `naId` | Catalog / Drupal (join key) | Existing NAID — identifies the record being updated |
| `dataControlGroup` | Catalog `dataControlGroup.groupName` | |
| `collectionIdentifier` | Static | `HST-SRC` |
| `parentSeries` | Static | `310670814` (Truman series NAID) |
| `title` | Drupal `title` | Drupal is more accurate for published items; `[Catalog_Title]` helper included for comparison |
| `generalRecordsType` | Static | `Sound Recordings` |
| `copyStatus` | Catalog `physicalOccurrences.0.copyStatus` | Falls back to `Preservation-Reference` if blank |
| `specificMediaType` | Catalog `physicalOccurrences.0.mediaOccurrences.0.specificMediaType` | Already structured in catalog; no lookup needed |
| `generalMediaType` | Catalog `physicalOccurrences.0.mediaOccurrences.0.generalMediaTypes.0` | Already structured in catalog |
| `dimensions` | Catalog `physicalOccurrences.0.mediaOccurrences.0.dimension` | Already structured; values: `16 inch`, `12 inch`, `10 inch`, `7 inch`, or blank |
| `format` | *(blank)* | Not structured in catalog; not derivable from available fields |
| `accessRestrictionStatus` | Catalog `accessRestriction.status` | All 811 matched catalog records are `Unrestricted` |
| `useRestrictionStatus` | Catalog `useRestriction.status` | 808 `Unrestricted`; 3 `Restricted - Possibly` |
| `specificUseRestriction` | Derived from `useRestriction.status` | Set to `Copyright` when status contains "restricted" |
| `useRestrictionNote` | Catalog `useRestriction.note` | Passed through as-is from catalog |
| `productionDateMonth` | Catalog `productionDates.0.month` | Already parsed in catalog; no date string processing needed |
| `productionDateDay` | Catalog `productionDates.0.day` | Already parsed in catalog |
| `productionDateYear` | Catalog `productionDates.0.year` | Already parsed in catalog |
| `productionDateQualifier` | Parsed from Drupal `Date` string | Checks for `ca.` in Drupal date; catalog has no qualifier field |
| `localIdentifier` | Catalog `localIdentifier` | |
| `scopeAndContentNote` | Combined: Drupal `Description` + `Production and Copyright` | Key update — rebuilds scope note with P&C using same formula as Tab 7; `[Catalog_scopeAndContentNote]` helper included for comparison |
| `[Description]` | Drupal `Description` | Helper column — source for scope note |
| `[ProductionAndCopyright]` | Drupal `Production and Copyright` | Helper column — source for scope note |
| `topicalSubject` | Catalog subjects with `authorityType = topicalSubject` | Authority-controlled; falls back to Drupal `Keywords` if none |
| `geographicReference` | Catalog subjects with `authorityType = geographicPlaceName` | Authority-controlled; semicolon-joined when multiple |
| `organizationalReference` | Catalog subjects with `authorityType = organization` | Authority-controlled; semicolon-joined when multiple |
| `personalReference` | Catalog subjects with `authorityType = person` | Authority-controlled; falls back to Drupal `People Mentioned` if none |
| `variantControlNumberType` | Catalog `variantControlNumbers.0.type` | |
| `variantControlNumber` | Catalog `variantControlNumbers.0.number` | |
| `variantControlNumberNote` | Catalog `variantControlNumbers.0.note` | |
| `editStatus` | Drupal `Excerpt or Complete` | `Complete` → `N`; `Excerpt` → `Y`; blank → blank |
| `recordingSpeed` | Drupal `Recording Speed` → speed lookup | Not structured in catalog; see recording speed lookup table in Tab 7 section |
| `runningTime` | *(blank)* | Not in Drupal export or catalog |
| `personalContributor` | Catalog contributor headings where `contributorType = Speaker` | All 841 contributor entries across matched records are Speaker type; semicolon-joined when multiple; falls back to Drupal `Speakers` if none |
| `staffOnlyNote` | Combined: Drupal `Internal Note` + `Preservation` | Joined with ` \| ` separator |
| `[InternalNote]` | Drupal `Internal Note` | Helper column |
| `[PreservationNote]` | Drupal `Preservation` | Helper column |
| `personalDonor` | *(blank)* | Not in Drupal export |
| `organizationalDonor` | *(blank)* | Not in Drupal export |
| `custodialHistoryNote` | Catalog `custodialHistoryNote` | Falls back to Drupal `Related Collection` prefixed formula if catalog value is blank |
| `[RelatedCollection]` | Drupal `Related Collection` | Helper column |
| `accessFilename` | Catalog `digitalObjects.0.objectFilename` | Falls back to filename extracted from Drupal `Sound Recording` URL if blank |
| `[soundRecordingURL]` | Drupal `Sound Recording` | Helper column — full URL for reference |
| `[Catalog_Title]` | Catalog `title` | Review helper — compare with `title` column to assess title updates needed |
| `[Catalog_scopeAndContentNote]` | Catalog `scopeAndContentNote` | Review helper — compare with rebuilt `scopeAndContentNote` |
| `[Drupal_AccessionNumber]` | Drupal `Accession Number` | Review helper — compare with `localIdentifier` from catalog |

#### Date handling (Tab 8 — matched records)

Because matched records already exist in the NARA catalog, the catalog's pre-parsed date fields are used directly for month, day, and year — no string parsing is required for those three fields. The qualifier, however, is not captured in the catalog export and must still be derived from the Drupal `Date` string.

| Template field | Source | Detail |
|---|---|---|
| `productionDateMonth` | Catalog `productionDates.0.month` | Integer month as stored in NARA (e.g., `4` for April) |
| `productionDateDay` | Catalog `productionDates.0.day` | Integer day; blank when only year or year+month is known |
| `productionDateYear` | Catalog `productionDates.0.year` | 4-digit year |
| `productionDateQualifier` | Parsed from Drupal `Date` string | Catalog has no qualifier field. The Drupal `Date` string is checked for `ca.`; if found, qualifier is set to `ca.` and removed from the date value. See date parsing table in Tab 7 section for all Drupal date formats handled. |

The catalog also exports `productionDates.0.logicalDate` (a pre-formatted display string such as `4/27/1940`), but this field is not used in the template output since the individual structured fields are already available and more suitable for bulk submission.

---

## Counts Summary

| Tab | Rows |
|---|---|
| Matched_Combined | 812 |
| Description_Update | 812 |
| Title_Mismatch | 597 |
| AccNum_LocalID_Mismatch | 5 |
| Catalog_Only | 27 |
| Drupal_NoNAID_Published | 181 |
| Template_Mapped | 181 |
| Template_Matched | 812 |

---

## Known Limitations and Items Requiring Manual Review

- **Title mismatches (597 records):** The high count likely includes many minor formatting differences (punctuation, capitalization, abbreviations). A manual spot-check of the `Title_Mismatch` tab is recommended before deciding on a batch update strategy. The `[Catalog_Title]` helper column in `Template_Matched` supports this review.
- **Blank formats (12 records):** Twelve records in `Template_Mapped` have no `Original Format(s)` value. `specificMediaType`, `generalMediaType`, `dimensions`, and `format` will need to be filled in manually.
- **`format` field in Template_Matched:** The catalog does not have a standalone `format` field equivalent to the template column. Left blank for all 812 records.
- **Organizational reference:** No clear Drupal source field maps to `organizationalReference` in `Template_Mapped` (no-NAID records). In `Template_Matched`, catalog authority-controlled organization subjects are used.
- **Running time:** Not present in either source. Left blank in both template tabs.
- **Personal/Organizational Donor:** Not present in either source. Left blank in both template tabs.
- **Template version:** The bulk cataloging template used (`LAA_2ndDraft_SoundRec_Template-BulkVer10-19-23.xlsx`) is described as a work in progress. Column mappings may need to be updated when a final version is available.
- **parentSeries NAID:** Hardcoded to `310670814` (Truman series) in both template tabs. If any records belong to a non-Truman series, this will need to be corrected per record.
- **Duplicate NAID 325599974:** Appears twice in `Template_Matched` (Drupal records SR90-56-2 and SR90-56-3 share one catalog record). Both rows are intentionally retained.
