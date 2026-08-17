// Types mirroring engine_v2/web_data.json (schema 1.2.0).
// Source of truth is the engine output; these track it.

// Band and UnsocialClass derive from the BANDS/CLASSES arrays in lib/format.ts
// so the key names exist in exactly one place. `import type` keeps this module
// erased at compile time — it emits no runtime JavaScript.
import type { BANDS, CLASSES } from "../lib/format"

export type Band = (typeof BANDS)[number]
export type UnsocialClass = (typeof CLASSES)[number]
export type DayTypeName = "weekday" | "saturday" | "sunday" | "bank_holiday"
export type ByBand = Record<Band, number>
export type ByClass = Record<UnsocialClass, number>

export interface Meta {
  schema_version: string
  generated_at: string
  unit: "minutes"
  unit_note: string
  contract: {
    contracted_weekly_minutes: number
    fulltime_weekly_minutes: number
    pay_week_start: string
  }
  rules: {
    day_window_start_minute: number
    night_window_start_minute: number
    weekend_and_bankhol_whole_day: boolean
    bank_holidays: string[]
    bank_holiday_years_covered: number[]
  }
  methodology: string[]
  subject?: { name?: string; post?: string; [k: string]: unknown }
}

export interface FlaggedSegment {
  date: string
  start_minute: number
  end_minute: number
  duration_minutes: number
  unsocial_class: UnsocialClass
}

export interface WeekSummary {
  iso_week: string
  monday: string
  day_count: number
  total_minutes: number
  minutes_by_band: ByBand
  minutes_by_class: ByClass
  unsocial_within_baseline_minutes: number
  flagged_segments: FlaggedSegment[]
}

export interface DayRecord {
  date: string
  iso_weekday: number
  day_type: DayTypeName
  start_minute: number
  end_minute: number
  duration_minutes: number
  minutes_by_class: ByClass
}

/** One calendar month. Months do NOT re-band: bands belong to the
 *  Monday-to-Sunday pay-week, so a week spanning a month boundary contributes
 *  minutes to both months carrying the bands its week assigned. */
export interface MonthSummary {
  month: string
  day_count: number
  total_minutes: number
  minutes_by_band: ByBand
  minutes_by_class: ByClass
}

/** One payment, as the page sees it. There is deliberately no `note` field:
 *  the spreadsheet's free text never reaches this file (engine decision, so
 *  that no free text can put a pay figure on a public page). */
export interface LedgerEntry {
  date: string
  minutes_paid: number
  cumulative_paid_minutes: number
}

export interface WeekSettlement {
  iso_week: string
  monday: string
  extra_minutes: number
  unpaid_minutes: number
}

export interface Payments {
  paid_minutes: number
  unpaid_minutes: number
  overpaid_minutes: number
  /** null means nothing is settled yet — not "unknown". */
  paid_up_to: string | null
  ledger: LedgerEntry[]
  unpaid_weeks: WeekSettlement[]
  /** Payment warnings only. Engine integrity warnings live on Integrity and
   *  are the ones that block publishing; these never do. */
  warnings: string[]
}

export interface Integrity {
  conservation_ok: boolean
  partitions_ok: boolean
  uniqueness_ok: boolean
  banding_formula_ok: boolean
  crosstab_ok: boolean
  span_ok: boolean
  /** Added in schema 1.2.0. Optional so a 1.1.x file still type-checks. */
  monthly_ok?: boolean
  total_raw_minutes: number
  total_segment_minutes: number
  unsocial_within_baseline_minutes: number
  warnings: string[]
}

export interface WebData {
  meta: Meta
  content: {
    period: { start: string; end: string }
    totals: {
      total_minutes: number
      day_count: number
      week_count: number
      minutes_by_band: ByBand
      minutes_by_class: ByClass
      unsocial_within_baseline_minutes: number
      /** Additional + overtime, computed by the engine. Optional because a
       *  1.1.x file does not carry it; the header falls back to hiding the
       *  figure rather than rendering NaN (see lib/validate.ts). */
      above_contract_minutes?: number
    }
    weekly: WeekSummary[]
    daily: DayRecord[]
    /** Schema 1.2.0. Optional on purpose: a missing block hides its panel and
     *  raises a warning, it never takes the page down. */
    monthly?: MonthSummary[]
    /** Schema 1.2.0. Optional for the same reason as `monthly`. */
    payments?: Payments
    cross_tab: Record<Band, ByClass>
    cumulative: { date: string; cumulative_minutes: number }[]
    statistics: {
      pct_by_band: ByBand
      pct_by_class: ByClass
      mean_minutes_per_day: number
      mean_minutes_per_week: number
      mean_start_minute: number
      mean_end_minute: number
      longest_day: { date: string; minutes: number }
      shortest_day: { date: string; minutes: number }
      days_touching_class: ByClass
    }
    integrity: Integrity
  }
}
