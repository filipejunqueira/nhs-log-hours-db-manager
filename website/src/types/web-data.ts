// Types mirroring engine_v2/web_data.json (schema 1.1.0).
// Source of truth is the engine output; these track it.

export type Band = "contracted" | "additional" | "overtime"
export type UnsocialClass = "daytime" | "weekday_night" | "saturday" | "sunday" | "bank_holiday"
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

export interface Integrity {
  conservation_ok: boolean
  partitions_ok: boolean
  uniqueness_ok: boolean
  banding_formula_ok: boolean
  crosstab_ok: boolean
  span_ok: boolean
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
    }
    weekly: WeekSummary[]
    daily: DayRecord[]
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
