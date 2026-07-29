# data/exports — the archive of ingested CSVs

One file per distinct spreadsheet export that has ever been the basis for
published figures. `scripts/ingest.sh` writes here and **never overwrites or
deletes**: if a file with the same content is offered again it is reported, not
copied a second time.

## Two naming eras

**From 2026-07-29 onward** — written by ingest.sh:

```
hours_export_<ingest-time>_covers-to-<last-work-date>.csv
hours_export_2026-07-29_2043_covers-to-2026-07-14.csv
```

The first date is when the file entered the repo; the second is the latest
working day inside it. Sorting the folder alphabetically also sorts it by when
each export arrived. Because the ingest time is part of the name, two exports
can never collide, so nothing is ever lost.

**Before that** — the two files below were named by hand, by download date,
before ingest.sh existed:

- `hours_export_2026-06-25.csv` — data ends 25 Jun 2026
- `hours_export_2026-07-18.csv` — data ends **14 Jul 2026**, despite the name

They are kept under their original names on purpose: both are committed and
referenced in the docs/TODO.md Done log, and renaming them would churn history
to fix cosmetics. Read the second date in a modern filename as authoritative;
for these two, run the engine on the file if you need to know its true span.

## Why this matters

These files are the audit trail. If a published figure is ever questioned, the
answer is "here is the exact export it came from, and when it arrived". An
archive that can be overwritten cannot answer that.

The canonical CSV the engine actually reads is
`engine_v2/data/filipe_working_hours_log.csv` — a copy of whichever export was
most recently accepted. The frozen test fixture under `engine_v2/tests/` is a
separate thing again and is never touched by ingest.
