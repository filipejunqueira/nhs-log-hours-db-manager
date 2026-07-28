// Shape check for web_data.json, run after the schema-version gate in
// composables/useHoursData.ts.
//
// The version gate accepts any 1.x with minor >= 1, so a future engine release
// can legitimately hand this page data it only partly understands. Two failures
// are possible and they want different answers:
//
//   fatal    - a whole block the page reads is absent. Every component would
//              throw on first property access, which unmounts the app and
//              leaves a blank white page. Better to fail through App.vue's
//              existing error panel.
//   warnings - a band or clock class the page does not know about. The column
//              would silently vanish and the cross-tab rows would stop adding
//              up to the totals printed directly above them. The page still
//              renders everything it does recognise, above a visible banner.
//
// Deliberately NOT a hard refusal on unknown keys: a future engine release must
// not be able to take the live page down.

import type { WebData } from "../types/web-data"
import { BANDS, CLASSES } from "./format"

export interface DataCheck {
  /** Non-null means: do not render, show this in the error panel. */
  fatal: string | null
  /** Render anyway, but show these above the page. */
  warnings: string[]
}

/** Blocks of content that a component reads directly. */
const REQUIRED_BLOCKS = [
  "period",
  "totals",
  "weekly",
  "daily",
  "cross_tab",
  "cumulative",
  "statistics",
  "integrity",
] as const

function keysOf(value: unknown): string[] {
  return value !== null && typeof value === "object" ? Object.keys(value) : []
}

function quoteList(items: string[]): string {
  return items.map((i) => `"${i}"`).join(", ")
}

export function checkData(json: WebData): DataCheck {
  const content = (json as { content?: Record<string, unknown> }).content
  if (content === undefined || content === null) {
    return { fatal: "The data file has no content block.", warnings: [] }
  }

  const missingBlocks = REQUIRED_BLOCKS.filter((b) => content[b] === undefined || content[b] === null)
  if (missingBlocks.length > 0) {
    const plural = missingBlocks.length > 1
    return {
      fatal:
        `The data file is missing ${plural ? "blocks" : "the block"} ${quoteList(missingBlocks)}. ` +
        `This page cannot render without ${plural ? "them" : "it"}. ` +
        `Regenerate web_data.json with the current engine.`,
      warnings: [],
    }
  }

  // Every block whose keys are band names, and every block whose keys are
  // clock-classification names. cross_tab is both: bands at the top level,
  // classes inside each row.
  const totals = content.totals as Record<string, unknown>
  const statistics = content.statistics as Record<string, unknown>
  const crossTab = content.cross_tab as Record<string, unknown>

  const bandKeys = new Set<string>([
    ...keysOf(crossTab),
    ...keysOf(totals.minutes_by_band),
    ...keysOf(statistics.pct_by_band),
  ])

  const classKeys = new Set<string>([
    ...keysOf(totals.minutes_by_class),
    ...keysOf(statistics.pct_by_class),
    ...keysOf(statistics.days_touching_class),
    ...Object.values(crossTab).flatMap((row) => keysOf(row)),
  ])

  const knownBands: readonly string[] = BANDS
  const knownClasses: readonly string[] = CLASSES

  const warnings: string[] = []

  const unknownBands = [...bandKeys].filter((k) => !knownBands.includes(k))
  if (unknownBands.length > 0) {
    warnings.push(
      `The data contains ${unknownBands.length > 1 ? "bands" : "a band"} this page does not ` +
        `recognise: ${quoteList(unknownBands)}. Those hours are not shown in the tables below, ` +
        `so the band figures do not add up to the total.`,
    )
  }

  const unknownClasses = [...classKeys].filter((k) => !knownClasses.includes(k))
  if (unknownClasses.length > 0) {
    const noun = unknownClasses.length > 1 ? "clock classifications" : "a clock classification"
    warnings.push(
      `The data contains ${noun} this page does not recognise: ${quoteList(unknownClasses)}. ` +
        `Those hours are not shown in the tables below, so the classification figures do not ` +
        `add up to the total.`,
    )
  }

  const absentBands = knownBands.filter((k) => !bandKeys.has(k))
  if (absentBands.length > 0) {
    warnings.push(
      `The data does not contain ${quoteList(absentBands)}, which this page expects. ` +
        `Those rows show as blank.`,
    )
  }

  const absentClasses = knownClasses.filter((k) => !classKeys.has(k))
  if (absentClasses.length > 0) {
    warnings.push(
      `The data does not contain ${quoteList(absentClasses)}, which this page expects. ` +
        `Those columns show as blank.`,
    )
  }

  return { fatal: null, warnings }
}
