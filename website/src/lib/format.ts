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
