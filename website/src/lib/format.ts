// The ONLY arithmetic the front end performs: minutes ÷ 60 for display.

/** Duration in minutes → "X.XX" hours string (2 dp). */
export function minutesToHours(min: number): string {
  return (min / 60).toFixed(2)
}

/** Minutes-from-midnight → "HH:MM" clock string. */
export function minuteToClock(min: number): string {
  const h = Math.floor(min / 60)
  const m = min % 60
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
}

/** Sum already-computed minute values for display (e.g. additional +
 *  overtime = "hours above contract"). Presentation-only and sanctioned by
 *  plan.md (option a, 2026-07-19): inputs are engine-banded figures, so this
 *  can never reclassify or re-band anything. Replaced by an engine-emitted
 *  above_contract_minutes at the next schema bump. */
export function sumMinutes(...mins: number[]): number {
  return mins.reduce((a, b) => a + b, 0)
}

/** Human-readable label for a Band key. */
export function labelForBand(band: string): string {
  const labels: Record<string, string> = {
    contracted: "Contracted",
    additional: "Additional",
    overtime: "Overtime",
  }
  return labels[band] ?? band
}

/** Human-readable label for an UnsocialClass key. */
export function labelForClass(cls: string): string {
  const labels: Record<string, string> = {
    daytime: "Daytime",
    weekday_night: "Weekday Night",
    saturday: "Saturday",
    sunday: "Sunday",
    bank_holiday: "Bank Holiday",
  }
  return labels[cls] ?? cls
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
