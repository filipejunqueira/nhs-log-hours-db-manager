// The ONLY arithmetic the front end performs: minutes ÷ 60 for display.

/** The band keys the engine emits, in display order. Single source of truth:
 *  types/web-data.ts derives the Band union from this, the label map below is
 *  typed against it, every component iterates it, and lib/validate.ts checks
 *  the engine's actual keys against it. */
export const BANDS = ["contracted", "additional", "overtime"] as const

/** The clock-classification keys the engine emits, in display order. Same
 *  single-source role as BANDS. */
export const CLASSES = ["daytime", "weekday_night", "saturday", "sunday", "bank_holiday"] as const

/** Duration in minutes → "X.XX" hours string (2 dp). */
export function minutesToHours(min: number): string {
  return (min / 60).toFixed(2)
}

/** Duration in minutes → hours as a NUMBER, for plotting only. Chart.js picks
 *  axis tick positions that are round in whatever unit it is given, so feeding
 *  it minutes produced an axis reading 33.33 h / 66.67 h. Feeding it hours
 *  gives round hours. Display strings still come from minutesToHours. */
export function minutesToHoursValue(min: number): number {
  return min / 60
}

/** Percentage already computed by the engine → "X.XX%". No arithmetic:
 *  pct_by_band/pct_by_class arrive as percentages (BUILD_NOTES §3). This only
 *  fixes the decimal count, which varies field to field in the raw JSON
 *  (93.43, 0.9, 0) and breaks the tabular-numeral alignment. */
export function formatPercent(pct: number): string {
  return `${pct.toFixed(2)}%`
}

/** Minutes-from-midnight → "HH:MM" clock string. Rounds to the nearest
 *  minute first: mean_start_minute/mean_end_minute (statistics) are
 *  non-integer averages, unlike the integer start_minute/end_minute on
 *  individual days. */
export function minuteToClock(min: number): string {
  const rounded = Math.round(min)
  const h = Math.floor(rounded / 60)
  const m = rounded % 60
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
}

// sumMinutes was removed at schema 1.2.0 (2026-08-17), as the 2026-07-19
// decision that sanctioned it said it would be. The engine now emits
// totals.above_contract_minutes, the only figure it ever added up. This file
// is back to holding no arithmetic beyond minutes ÷ 60 and clock formatting.

/** Typed against BANDS, so adding a band there without a label fails vue-tsc. */
const BAND_LABELS: Record<(typeof BANDS)[number], string> = {
  contracted: "Contracted",
  additional: "Additional",
  overtime: "Overtime",
}

/** Typed against CLASSES, same compile-time link as BAND_LABELS. */
const CLASS_LABELS: Record<(typeof CLASSES)[number], string> = {
  daytime: "Daytime",
  weekday_night: "Weekday Night",
  saturday: "Saturday",
  sunday: "Sunday",
  bank_holiday: "Bank Holiday",
}

/** Human-readable label for a Band key. Accepts any string and falls back to
 *  the key itself, so an unrecognised key from a future engine renders as
 *  itself rather than blank (lib/validate.ts raises the warning). */
export function labelForBand(band: string): string {
  return BAND_LABELS[band as (typeof BANDS)[number]] ?? band
}

/** Human-readable label for an UnsocialClass key. Same fallback as labelForBand. */
export function labelForClass(cls: string): string {
  return CLASS_LABELS[cls as (typeof CLASSES)[number]] ?? cls
}

/** ISO weekday number (1 = Monday) → short name. Lookup, not arithmetic. */
export function labelForWeekday(iso: number): string {
  const names = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
  return names[iso] ?? String(iso)
}

/** Human-readable label for a day_type key. */
export function labelForDayType(t: string): string {
  const labels: Record<string, string> = {
    weekday: "Weekday",
    saturday: "Saturday",
    sunday: "Sunday",
    bank_holiday: "Bank holiday",
  }
  return labels[t] ?? t
}
