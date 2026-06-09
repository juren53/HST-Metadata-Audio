"""
HST Audio Metadata Analysis
Reads Drupal and NARA Catalog CSV exports, produces a multi-tab .xlsx file.

Tabs produced:
  1. Matched_Combined        - all columns from both sources, joined on NAID
  2. Description_Update      - NAID + accession + catalog scope note + Drupal description + P&C
  3. Title_Mismatch          - matched records where titles differ
  4. AccNum_LocalID_Mismatch - matched records where accession/local-id differ
  5. Catalog_Only            - catalog records with no matching Drupal NAID
  6. Drupal_NoNAID_Published - Drupal published records (has Sound Recording URL) with no NAID
  7. Template_Mapped         - published/no-NAID records adapted to bulk cataloging template columns
  8. Template_Matched        - matched records adapted to template columns for catalog updates
"""

import re
from datetime import datetime
import pandas as pd
from pathlib import Path

BASE      = Path(__file__).parent
TIMESTAMP = datetime.now().strftime("%Y-%m-%d-%H%M")

DRUPAL_CSV   = BASE / "HST-SRC_ALL_DrupalExport_2026-05-07_edited.csv"
CATALOG_CSV  = BASE / "HST-SRC_ALL_catalog-export-20260507.csv"
OUTPUT_XLSX  = BASE / f"HST_Audio_Analysis_{TIMESTAMP}.xlsx"

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
drupal  = pd.read_csv(DRUPAL_CSV,  dtype=str).fillna("")
catalog = pd.read_csv(CATALOG_CSV, dtype=str).fillna("")

# Normalise NAID columns to a clean string; blank out whitespace-only values
drupal["NAID"]    = drupal["NAID"].str.strip()
catalog["naId"]   = catalog["naId"].str.strip()

# Working copies with a common join key
drupal["_naid"]   = drupal["NAID"].replace("", pd.NA)
catalog["_naid"]  = catalog["naId"].replace("", pd.NA)

# ---------------------------------------------------------------------------
# Split populations
# ---------------------------------------------------------------------------
drupal_with_naid    = drupal.dropna(subset=["_naid"]).copy()
drupal_without_naid = drupal[drupal["_naid"].isna()].copy()

# Records whose NAID appears in both sources
common_naids = set(drupal_with_naid["_naid"]) & set(catalog["_naid"].dropna())

drupal_matched   = drupal_with_naid[drupal_with_naid["_naid"].isin(common_naids)].copy()
catalog_matched  = catalog[catalog["_naid"].isin(common_naids)].copy()
catalog_only     = catalog[~catalog["_naid"].isin(common_naids)].copy()

print(f"Drupal rows           : {len(drupal)}")
print(f"Catalog rows          : {len(catalog)}")
print(f"Common NAIDs          : {len(common_naids)}")
print(f"Drupal matched        : {len(drupal_matched)}")
print(f"Catalog-only          : {len(catalog_only)}")
print(f"Drupal without NAID   : {len(drupal_without_naid)}")

# ---------------------------------------------------------------------------
# Tab 1 — Matched_Combined
# ---------------------------------------------------------------------------
# Prefix every column from each source to avoid ambiguity, except the join key
drupal_t1   = drupal_matched.drop(columns=["_naid"]).add_prefix("drupal_")
catalog_t1  = catalog_matched.drop(columns=["_naid"]).add_prefix("catalog_")

# Re-attach the shared NAID as the first column
drupal_t1.insert(0,  "NAID", drupal_matched["_naid"].values)
catalog_t1.insert(0, "NAID", catalog_matched["_naid"].values)

matched_combined = (
    drupal_t1
    .merge(catalog_t1, on="NAID", how="inner")
    .sort_values("NAID")
    .reset_index(drop=True)
)

# ---------------------------------------------------------------------------
# Tab 2 — Description_Update
# ---------------------------------------------------------------------------
desc_base = drupal_matched.merge(
    catalog_matched[["_naid", "scopeAndContentNote"]],
    on="_naid",
    how="left",
)

description_update = desc_base[[
    "_naid",
    "Accession Number",
    "scopeAndContentNote",
    "Description",
    "Production and Copyright",
]].rename(columns={
    "_naid":                  "NAID",
    "scopeAndContentNote":    "Catalog_scopeAndContentNote",
    "Description":            "Drupal_Description",
    "Production and Copyright": "Drupal_ProductionAndCopyright",
}).sort_values("NAID").reset_index(drop=True)

# ---------------------------------------------------------------------------
# Tab 3 — Title_Mismatch
# ---------------------------------------------------------------------------
title_base = drupal_matched.merge(
    catalog_matched[["_naid", "title"]],
    on="_naid",
    how="inner",
    suffixes=("_drupal", "_catalog"),
)

# Compare stripped, case-insensitive
title_base["_drupal_title_norm"]   = title_base["title_drupal"].str.strip().str.lower()
title_base["_catalog_title_norm"]  = title_base["title_catalog"].str.strip().str.lower()

title_mismatch = (
    title_base[title_base["_drupal_title_norm"] != title_base["_catalog_title_norm"]]
    [[  "_naid",
        "Accession Number",
        "title_catalog",
        "title_drupal",
    ]]
    .rename(columns={
        "_naid":          "NAID",
        "title_catalog":  "Catalog_Title",
        "title_drupal":   "Drupal_Title",
    })
    .sort_values("NAID")
    .reset_index(drop=True)
)

# ---------------------------------------------------------------------------
# Tab 4 — AccNum_LocalID_Mismatch
# ---------------------------------------------------------------------------
acc_base = drupal_matched.merge(
    catalog_matched[["_naid", "localIdentifier"]],
    on="_naid",
    how="inner",
)

acc_base["_drupal_acc_norm"]   = acc_base["Accession Number"].str.strip().str.lower()
acc_base["_catalog_lid_norm"]  = acc_base["localIdentifier"].str.strip().str.lower()

acc_mismatch = (
    acc_base[acc_base["_drupal_acc_norm"] != acc_base["_catalog_lid_norm"]]
    [[  "_naid",
        "localIdentifier",
        "Accession Number",
    ]]
    .rename(columns={
        "_naid":            "NAID",
        "localIdentifier":  "Catalog_LocalIdentifier",
        "Accession Number": "Drupal_AccessionNumber",
    })
    .sort_values("NAID")
    .reset_index(drop=True)
)

# ---------------------------------------------------------------------------
# Tab 5 — Catalog_Only
# ---------------------------------------------------------------------------
catalog_only_out = (
    catalog_only
    .drop(columns=["_naid"])
    .sort_values("naId")
    .reset_index(drop=True)
)

# ---------------------------------------------------------------------------
# Tab 6 — Drupal_NoNAID_Published
# ---------------------------------------------------------------------------
published_no_naid = (
    drupal_without_naid[drupal_without_naid["Sound Recording"].str.strip() != ""]
    .drop(columns=["_naid"])
    .reset_index(drop=True)
)

print(f"Drupal published/no-NAID: {len(published_no_naid)}")

# ---------------------------------------------------------------------------
# Shared lookup tables and helper functions (used by Tab 7 and Tab 8)
# ---------------------------------------------------------------------------

# Format Mapping: Drupal "Original Format(s)" → template fields
# generalMediaType inferred from NARA catalog data (all legacy audio = Magnetic Media
# except optical/compact disc)
FORMAT_MAP = {
    "disc, 16-inch":  dict(specificMediaType="Audio Disc",                    generalMediaType="Magnetic Media", dimensions="16 inch", format=""),
    "disc, 12-inch":  dict(specificMediaType="Audio Disc",                    generalMediaType="Magnetic Media", dimensions="12 inch", format=""),
    "disc, 10-inch":  dict(specificMediaType="Audio Disc",                    generalMediaType="Magnetic Media", dimensions="10 inch", format=""),
    "disc, 7-inch":   dict(specificMediaType="Audio Disc",                    generalMediaType="Magnetic Media", dimensions="7 inch",  format=""),
    "flexible disc":  dict(specificMediaType="Audio Disc",                    generalMediaType="Magnetic Media", dimensions="",        format=""),
    "reel-to-reel":   dict(specificMediaType="Audio Tape/Reel",               generalMediaType="Magnetic Media", dimensions="",        format=""),
    "cassette":       dict(specificMediaType="Magnetic Tape Cassette",        generalMediaType="Magnetic Media", dimensions="",        format=""),
    "microcassette":  dict(specificMediaType="Magnetic Tape Cassette",        generalMediaType="Magnetic Media", dimensions="",        format=""),
    "compact disc":   dict(specificMediaType="Optical Disk: Compact Disk",    generalMediaType="Optical",        dimensions="",        format="Sound: Compact Disk"),
    "wire recording": dict(specificMediaType="Wire Recording",                generalMediaType="Magnetic Media", dimensions="",        format=""),
}

# Recording Speed: Drupal value → template value
SPEED_MAP = {
    "7-1/2 ips":  "Audio Tape: 7 1/2 ips",
    "3-3/4 ips":  "Audio Tape: 3 3/4 ips",
    "1-7/8 ips":  "Audio Tape: 1 7/8 ips",
    "15 ips":     "Audio Tape: 15 ips",
    "33-1/3 rpm": "Audio Disk: 33 1/3 rpm",
    "45 rpm":     "Audio Disk: 45 rpm",
    "78 rpm":     "Audio Disk: 78 rpm",
}

# Restrictions: Drupal value → use restriction fields
RESTRICTION_MAP = {
    "Unrestricted": dict(
        useRestrictionStatus="Unrestricted",
        specificUseRestriction="",
        useRestrictionNote="",
    ),
    "Restricted": dict(
        useRestrictionStatus="Restricted",
        specificUseRestriction="Copyright",
        useRestrictionNote="This Item is restricted fully due to copyright.",
    ),
    "Undetermined": dict(
        useRestrictionStatus="Undetermined",
        specificUseRestriction="",
        useRestrictionNote="The copyright status of this recording is unknown.",
    ),
}


def parse_date(raw):
    """
    Return (month, day, year, qualifier) from Drupal Date strings.
    Handles: "17-Oct-52", "September 21, 1946", "1961", date ranges
    (takes the first/earliest date from a range).
    All 2-digit years treated as 1900s (Truman-era recordings).
    """
    if not raw or not raw.strip():
        return "", "", "", ""

    # Normalise: take only the part before a range separator (\n - or -)
    first = re.split(r"\n\s*-|\s+-\s+", raw.strip())[0].strip()

    qualifier = "ca." if "ca." in first.lower() else ""
    first = re.sub(r"ca\.?\s*", "", first, flags=re.IGNORECASE).strip()

    # Try "17-Oct-52" (day-abbrev-2digitYear)
    m = re.match(r"^(\d{1,2})-([A-Za-z]{3})-(\d{2})$", first)
    if m:
        day, mon_str, yr2 = m.groups()
        mon = pd.to_datetime(mon_str, format="%b").month
        year = 1900 + int(yr2)
        return str(mon), str(day), str(year), qualifier

    # Try "September 21, 1946" or "Sep 21, 1946"
    m = re.match(r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$", first)
    if m:
        mon_str, day, year = m.groups()
        try:
            mon = pd.to_datetime(mon_str, format="%B").month
        except Exception:
            mon = pd.to_datetime(mon_str, format="%b").month
        return str(mon), str(day), str(year), qualifier

    # Try 4-digit year only  "1961"
    m = re.match(r"^(\d{4})$", first)
    if m:
        return "", "", m.group(1), qualifier

    # Try "dd-Mon-yyyy" edge case
    m = re.match(r"^(\d{1,2})-([A-Za-z]{3})-(\d{4})$", first)
    if m:
        day, mon_str, year = m.groups()
        mon = pd.to_datetime(mon_str, format="%b").month
        return str(mon), str(day), str(year), qualifier

    # Fallback: return raw value in year field so nothing is silently lost
    return "", "", first, qualifier


def build_scope_note(description, prod_copyright):
    """Combine Drupal Description and Production and Copyright per template formula."""
    desc = description.strip()
    pc   = prod_copyright.strip()
    if pc:
        return f"{desc}\n\nProduction and Copyright info:\n{pc}" if desc else f"Production and Copyright info:\n{pc}"
    return desc


def build_staff_note(internal_note, preservation):
    """Combine Internal Note and Preservation into StaffOnlyNote."""
    parts = [p.strip() for p in [internal_note, preservation] if p.strip()]
    return "  |  ".join(parts)


def build_custodial_note(related_collection):
    rc = related_collection.strip()
    if rc:
        return f"Transferred to the sound recordings from the {rc}"
    return ""


def extract_filename(url):
    url = url.strip()
    if url:
        return url.rsplit("/", 1)[-1]
    return ""


# ---------------------------------------------------------------------------
# Tab 8 — Template_Matched
# Adapts matched records to template columns for catalog updates.
# Uses catalog's pre-structured fields (dates, media types, subjects, contributors)
# and Drupal fields for data not captured in the catalog (title, P&C, recording speed).
# ---------------------------------------------------------------------------

_CATALOG_COLS = set(catalog_matched.columns)

def _cget(row, col):
    return row[col] if col in _CATALOG_COLS else ""

def collect_speakers(c_row):
    """Return semicolon-joined Speaker contributor headings from catalog row."""
    parts = []
    for i in range(15):
        if _cget(c_row, f"contributors.{i}.contributorType").strip() == "Speaker":
            h = _cget(c_row, f"contributors.{i}.heading").strip()
            if h:
                parts.append(h)
    return "; ".join(parts)

def collect_subjects_by_type(c_row, auth_type):
    """Return semicolon-joined subject headings matching a given authorityType."""
    parts = []
    for i in range(8):
        if _cget(c_row, f"subjects.{i}.authorityType").strip() == auth_type:
            h = _cget(c_row, f"subjects.{i}.heading").strip()
            if h and h not in parts:
                parts.append(h)
    return "; ".join(parts)

def derive_specific_use_restriction(use_status, use_note):
    """Map catalog useRestriction.status to specificUseRestriction value."""
    s = use_status.strip().lower()
    if "restricted" in s:
        return "Copyright"
    return ""

# Index catalog by naId for O(1) lookup; keep first row where duplicates exist
catalog_idx = catalog_matched.set_index("_naid", drop=False)

# Merge so each Drupal row (including the one duplicate) gets its catalog row
matched_for_template = drupal_matched.merge(
    catalog_matched[["_naid"]],  # just the key; we'll look up catalog via index
    on="_naid",
    how="left",
)

rows_t8 = []
for _, d in drupal_matched.iterrows():
    naid = d["_naid"]
    c = catalog_idx.loc[naid] if naid in catalog_idx.index else pd.Series(dtype=str)

    # --- Catalog fields ---
    specific_media = _cget(c, "physicalOccurrences.0.mediaOccurrences.0.specificMediaType").strip()
    general_media  = _cget(c, "physicalOccurrences.0.mediaOccurrences.0.generalMediaTypes.0").strip()
    dimensions     = _cget(c, "physicalOccurrences.0.mediaOccurrences.0.dimension").strip()
    copy_status    = _cget(c, "physicalOccurrences.0.copyStatus").strip() or "Preservation-Reference"
    access_status  = _cget(c, "accessRestriction.status").strip() or "Unrestricted"
    use_status     = _cget(c, "useRestriction.status").strip() or "Unrestricted"
    use_note       = _cget(c, "useRestriction.note").strip()
    specific_use   = derive_specific_use_restriction(use_status, use_note)
    prod_month     = _cget(c, "productionDates.0.month").strip()
    prod_day       = _cget(c, "productionDates.0.day").strip()
    prod_year      = _cget(c, "productionDates.0.year").strip()
    local_id       = _cget(c, "localIdentifier").strip()
    catalog_scope  = _cget(c, "scopeAndContentNote").strip()
    catalog_title  = _cget(c, "title").strip()
    vcn_type       = _cget(c, "variantControlNumbers.0.type").strip()
    vcn_num        = _cget(c, "variantControlNumbers.0.number").strip()
    vcn_note       = _cget(c, "variantControlNumbers.0.note").strip()
    custodial      = _cget(c, "custodialHistoryNote").strip()
    access_file    = _cget(c, "digitalObjects.0.objectFilename").strip()
    dg_group       = _cget(c, "dataControlGroup.groupName").strip() or "PL-HST"

    # Subjects routed by authorityType
    geo_ref  = collect_subjects_by_type(c, "geographicPlaceName")
    org_ref  = collect_subjects_by_type(c, "organization")
    pers_ref = collect_subjects_by_type(c, "person") or d.get("People Mentioned", "").strip()
    topic    = collect_subjects_by_type(c, "topicalSubject") or d.get("Keywords", "").strip()
    speakers = collect_speakers(c) or d.get("Speakers", "").strip()

    # --- Drupal fields ---
    drupal_title = d.get("title", "").strip()
    description  = d.get("Description", "").strip()
    prod_copy    = d.get("Production and Copyright", "").strip()
    scope_note   = build_scope_note(description, prod_copy)

    # Qualifier: check Drupal Date string for "ca."
    _, _, _, qualifier = parse_date(d.get("Date", ""))

    # Recording speed: not in catalog — use Drupal
    speed_raw = d.get("Recording Speed", "").strip()
    speed = SPEED_MAP.get(speed_raw, speed_raw)

    # EditStatus from Drupal Excerpt or Complete
    excerpt_map = {"Complete": "N", "Excerpt": "Y"}
    edit_status = excerpt_map.get(d.get("Excerpt or Complete", "").strip(), "")

    # StaffOnlyNote from Drupal
    staff_note = build_staff_note(d.get("Internal Note", ""), d.get("Preservation", ""))

    # Custodial: prefer catalog; fall back to Drupal Related Collection
    if not custodial:
        custodial = build_custodial_note(d.get("Related Collection", ""))

    # Access filename: prefer catalog object filename, fall back to URL
    if not access_file:
        access_file = extract_filename(d.get("Sound Recording", ""))

    rows_t8.append({
        "naId":                     naid,
        "dataControlGroup":         dg_group,
        "collectionIdentifier":     "HST-SRC",
        "parentSeries":             "310670814",
        "title":                    drupal_title,
        "generalRecordsType":       "Sound Recordings",
        "copyStatus":               copy_status,
        "specificMediaType":        specific_media,
        "generalMediaType":         general_media,
        "accessRestrictionStatus":  access_status,
        "useRestrictionStatus":     use_status,
        "specificUseRestriction":   specific_use,
        "useRestrictionNote":       use_note,
        "productionDateMonth":      prod_month,
        "productionDateDay":        prod_day,
        "productionDateYear":       prod_year,
        "productionDateQualifier":  qualifier,
        "localIdentifier":          local_id,
        "scopeAndContentNote":      scope_note,
        "[Description]":            description,
        "[ProductionAndCopyright]": prod_copy,
        "topicalSubject":           topic,
        "geographicReference":      geo_ref,
        "organizationalReference":  org_ref,
        "personalReference":        pers_ref,
        "variantControlNumberType": vcn_type,
        "variantControlNumber":     vcn_num,
        "variantControlNumberNote": vcn_note,
        "editStatus":               edit_status,
        "dimensions":               dimensions,
        "format":                   "",
        "recordingSpeed":           speed,
        "runningTime":              "",
        "personalContributor":      speakers,
        "staffOnlyNote":            staff_note,
        "[InternalNote]":           d.get("Internal Note", "").strip(),
        "[PreservationNote]":       d.get("Preservation", "").strip(),
        "personalDonor":            "",
        "organizationalDonor":      "",
        "custodialHistoryNote":     custodial,
        "[RelatedCollection]":      d.get("Related Collection", "").strip(),
        "accessFilename":           access_file,
        "[soundRecordingURL]":      d.get("Sound Recording", "").strip(),
        # Review helpers
        "[Catalog_Title]":          catalog_title,
        "[Catalog_scopeAndContentNote]": catalog_scope,
        "[Drupal_AccessionNumber]": d.get("Accession Number", "").strip(),
    })

template_matched = pd.DataFrame(rows_t8).sort_values("naId").reset_index(drop=True)
print(f"Template_Matched rows : {len(template_matched)}")

# ---------------------------------------------------------------------------
# Tab 7 — Template_Mapped
# Adapts published/no-NAID Drupal records to bulk cataloging template columns.
# Column order matches Template-Bulk row 1 from LAA_2ndDraft_SoundRec_Template.
# ---------------------------------------------------------------------------

# --- Build Template_Mapped dataframe ---
src = published_no_naid.copy()

rows = []
for _, r in src.iterrows():
    fmt_key = r["Original Format(s)"].strip().lower()
    fmt     = FORMAT_MAP.get(fmt_key, dict(specificMediaType="", generalMediaType="", dimensions="", format=""))

    spd_key = r["Recording Speed"].strip()
    speed   = SPEED_MAP.get(spd_key, spd_key)

    restr   = RESTRICTION_MAP.get(r["Restrictions"].strip(), RESTRICTION_MAP["Unrestricted"])

    mon, day, year, qual = parse_date(r["Date"])

    excerpt_map = {"Complete": "N", "Excerpt": "Y"}
    edit_status = excerpt_map.get(r["Excerpt or Complete"].strip(), "")

    filename = extract_filename(r["Sound Recording"])

    rows.append({
        # Static fields
        "dataControlGroup":       "PL-HST",
        "collectionIdentifier":   "HST-SRC",
        "parentSeries":           "310670814",
        # From Drupal
        "title":                  r["title"].strip(),
        "generalRecordsType":     "Sound Recordings",
        "copyStatus":             "Preservation-Reference",
        "specificMediaType":      fmt["specificMediaType"],
        "generalMediaType":       fmt["generalMediaType"],
        "accessRestrictionStatus": "Unrestricted",
        "useRestrictionStatus":   restr["useRestrictionStatus"],
        "specificUseRestriction": restr["specificUseRestriction"],
        "useRestrictionNote":     restr["useRestrictionNote"],
        "productionDateMonth":    mon,
        "productionDateDay":      day,
        "productionDateYear":     year,
        "productionDateQualifier": qual,
        "localIdentifier":        r["Accession Number"].strip(),
        "scopeAndContentNote":    build_scope_note(r["Description"], r["Production and Copyright"]),
        # Helper columns kept visible for review
        "[Description]":          r["Description"].strip(),
        "[ProductionAndCopyright]": r["Production and Copyright"].strip(),
        "topicalSubject":         r["Keywords"].strip(),
        "geographicReference":    r["Place"].strip(),
        "organizationalReference": "",
        "personalReference":      r["People Mentioned"].strip(),
        "variantControlNumberType": "",
        "variantControlNumber":   "",
        "variantControlNumberNote": "",
        "editStatus":             edit_status,
        "dimensions":             fmt["dimensions"],
        "format":                 fmt["format"],
        "recordingSpeed":         speed,
        "runningTime":            "",
        "personalContributor":    r["Speakers"].strip(),
        "staffOnlyNote":          build_staff_note(r["Internal Note"], r["Preservation"]),
        "[InternalNote]":         r["Internal Note"].strip(),
        "[PreservationNote]":     r["Preservation"].strip(),
        "personalDonor":          "",
        "organizationalDonor":    "",
        "custodialHistoryNote":   build_custodial_note(r["Related Collection"]),
        "[RelatedCollection]":    r["Related Collection"].strip(),
        "accessFilename":         filename,
        # Source URL kept for reference
        "[soundRecordingURL]":    r["Sound Recording"].strip(),
    })

template_mapped = pd.DataFrame(rows)

print(f"Template_Mapped rows  : {len(template_mapped)}")

# Spot-check unmapped formats
unmapped_formats = src[~src["Original Format(s)"].str.strip().str.lower().isin(FORMAT_MAP)]["Original Format(s)"].value_counts()
if not unmapped_formats.empty:
    print("  Unmapped formats (no lookup entry):")
    for fmt_val, cnt in unmapped_formats.items():
        print(f"    '{fmt_val}' ({cnt} records)")

# ---------------------------------------------------------------------------
# Write output
# ---------------------------------------------------------------------------
tab_counts = {
    "Matched_Combined":        len(matched_combined),
    "Description_Update":      len(description_update),
    "Title_Mismatch":          len(title_mismatch),
    "AccNum_LocalID_Mismatch": len(acc_mismatch),
    "Catalog_Only":            len(catalog_only_out),
    "Drupal_NoNAID_Published": len(published_no_naid),
    "Template_Mapped":         len(template_mapped),
    "Template_Matched":        len(template_matched),
}

with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
    matched_combined.to_excel(   writer, sheet_name="Matched_Combined",        index=False)
    description_update.to_excel( writer, sheet_name="Description_Update",      index=False)
    title_mismatch.to_excel(     writer, sheet_name="Title_Mismatch",          index=False)
    acc_mismatch.to_excel(       writer, sheet_name="AccNum_LocalID_Mismatch", index=False)
    catalog_only_out.to_excel(   writer, sheet_name="Catalog_Only",            index=False)
    published_no_naid.to_excel(  writer, sheet_name="Drupal_NoNAID_Published", index=False)
    template_mapped.to_excel(    writer, sheet_name="Template_Mapped",         index=False)
    template_matched.to_excel(   writer, sheet_name="Template_Matched",        index=False)

    # Auto-fit column widths (capped at 60)
    for sheet_name, ws in writer.sheets.items():
        for col in ws.columns:
            max_len = max(
                (len(str(cell.value)) if cell.value is not None else 0)
                for cell in col
            )
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)

print(f"\nOutput: {OUTPUT_XLSX}")
for tab, count in tab_counts.items():
    print(f"  {tab:<30} {count:>5} rows")
