// Criterion 7: does the number ON THE PAGE equal the number in the JSON?
//
// Serves each scenario from dist/ and reads the rendered DOM. The scenarios sit
// next to this file so the check needs no setup beyond a built site:
//
//   cd website && npm run build && npx vite preview --port 4177 &
//   node scripts/check-render.mjs
//
// Every expected value is read from the scenario's own JSON. Nothing is
// hard-coded, so the check keeps meaning what it says when the data moves.
import { chromium } from 'playwright'
import { readFileSync, copyFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const SCENARIOS_DIR = join(HERE, 'scenarios')
const DIST = join(HERE, '..', 'dist', 'web_data.json')
const URL = 'http://localhost:4177/nhs-log-hours-db-manager/'

const hours = (min) => (min / 60).toFixed(2)

// expectBanner is the amber "does not fully understand" banner at the top of the
// page, driven by lib/validate.ts. It reads missing blocks and unknown band or
// class keys ONLY -- never payment warnings -- so `overpaid` expects no banner
// even though the engine warns about it. Those warnings surface inside the owed
// panel instead, and are checked there.
const SCENARIOS = [
  { name: 'real (no payments recorded)', file: 'scenario-real.json', expectBanner: false },
  { name: 'partial payment (5400 min paid)', file: 'scenario-partial.json', expectBanner: false },
  { name: 'overpaid (15000 min paid)', file: 'scenario-overpaid.json', expectBanner: false },
  { name: 'no payments block', file: 'scenario-no-payments.json', expectBanner: true },
  { name: 'no above_contract_minutes', file: 'scenario-no-above-contract.json', expectBanner: true },
  { name: 'no monthly block', file: 'scenario-no-monthly.json', expectBanner: true },
]

let failures = 0
const check = (label, ok, detail) => {
  console.log(`   ${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? ` — ${detail}` : ''}`)
  if (!ok) failures++
}

const browser = await chromium.launch()

for (const sc of SCENARIOS) {
  const path = join(SCENARIOS_DIR, sc.file)
  copyFileSync(path, DIST)
  const json = JSON.parse(readFileSync(path, 'utf8'))
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()))

  await page.goto(URL, { waitUntil: 'networkidle' })
  await page.waitForSelector('h1', { timeout: 5000 })

  console.log(`\n=== ${sc.name} ===`)
  check('page has no JavaScript errors', errors.length === 0, errors[0])
  check('error panel absent (page rendered)',
    (await page.locator('[role=alert] >> text=Could not load').count()) === 0)

  const bannerCount = await page.locator('text=does not fully understand').count()
  check(`amber banner ${sc.expectBanner ? 'present' : 'absent'}`,
    (bannerCount > 0) === sc.expectBanner, `banner elements: ${bannerCount}`)

  // ── the owed panel ────────────────────────────────────────────────────────
  const pay = json.content.payments
  const owed = page.locator('section[aria-labelledby=owed-heading]')
  let shown = null

  if (!pay) {
    check('owed panel hidden when there is no payments block', (await owed.count()) === 0)
  } else {
    shown = (await owed.locator('p.text-4xl').innerText()).trim()
    check('owed headline matches JSON unpaid_minutes',
      shown === `${hours(pay.unpaid_minutes)} h`,
      `page "${shown}" vs json "${hours(pay.unpaid_minutes)} h" (${pay.unpaid_minutes} min)`)

    // The sentence carrying accrued and paid. Read whole, so a markup change
    // cannot make this pass by matching nothing.
    const sentence = (await owed.locator('p.text-gray-700').first().innerText()).replace(/\s+/g, ' ')
    const accrued = json.content.totals.above_contract_minutes
    // A dash, not a zero, when the engine did not emit the key -- the panel
    // must not claim 0 h were worked above contract while the headline says
    // hours are owed. Mirrors what SummaryHeader shows for the same key.
    const accruedText = accrued === undefined ? '— h' : `${hours(accrued)} h`
    check('paid figure appears in the owed sentence',
      sentence.includes(`${hours(pay.paid_minutes)} h`),
      `looking for "${hours(pay.paid_minutes)} h" in: ${sentence}`)
    check('accrued reads as a dash when the key is absent, else the figure',
      sentence.includes(accruedText), `looking for "${accruedText}" in: ${sentence}`)

    const settledTo = (await owed.locator('dt:text-is("Settled up to") + dd').innerText()).trim()
    check('settled-up-to matches JSON paid_up_to',
      settledTo === (pay.paid_up_to ?? 'nothing settled yet'),
      `page "${settledTo}" vs json ${JSON.stringify(pay.paid_up_to)}`)

    const lastPay = (await owed.locator('dt:text-is("Last payment") + dd').innerText()).replace(/\s+/g, ' ').trim()
    const lastEntry = pay.ledger.at(-1)
    check('last payment matches the final ledger row',
      lastPay === (lastEntry
        ? `${lastEntry.date} · ${hours(lastEntry.minutes_paid)} h`
        : 'none recorded'),
      `page "${lastPay}"`)

    const weeksShown = (await owed.locator('dt:text-is("Weeks still owing") + dd').innerText()).trim()
    check('weeks-still-owing count matches JSON',
      weeksShown === String(pay.unpaid_weeks.length),
      `page "${weeksShown}" vs json ${pay.unpaid_weeks.length}`)

    // The overpayment block, and the engine's own warning text beneath it.
    const overBlock = owed.locator('p.bg-amber-50')
    const wantOver = pay.overpaid_minutes > 0
    check(`overpayment block ${wantOver ? 'present' : 'absent'}`,
      (await overBlock.count() > 0) === wantOver)
    if (wantOver) {
      const overText = (await overBlock.innerText()).replace(/\s+/g, ' ')
      check('overpaid figure on page matches JSON',
        overText.includes(`${hours(pay.overpaid_minutes)} h more has been paid`),
        `page: ${overText.slice(0, 90)}`)
      check('owed headline is floored at zero, never negative',
        pay.unpaid_minutes === 0 && shown === '0.00 h', `page "${shown}"`)
    }
    check(`engine payment warnings shown (${pay.warnings.length})`,
      (await owed.locator('ul.bg-amber-50 li').count()) === pay.warnings.length)
  }

  // ── the header tile, which reads the engine's key instead of adding up ────
  const tile = (await page.locator('dt:text-is("Hours above contract") + dd').innerText()).trim()
  const above = json.content.totals.above_contract_minutes
  if (above === undefined) {
    check('header shows a dash, not NaN, when the key is absent', tile === '—', `got "${tile}"`)
  } else {
    check('header above-contract matches JSON', tile === hours(above),
      `page "${tile}" vs json "${hours(above)}"`)
  }

  // ── the tables ───────────────────────────────────────────────────────────
  // Anchored on their own column headings. Taking .last() of the tables in the
  // payments section breaks when a scenario has a ledger but no weeks owing --
  // exactly the overpaid case -- because then the ledger table IS the last one.
  const rows = (sel) => page.locator(sel).locator('tbody tr').count()
  const PAY_SECTION = 'section[aria-labelledby=payments-heading]'

  const wantMonths = json.content.monthly?.length ?? 0
  check(`monthly table has ${wantMonths} rows`,
    (await rows('section[aria-labelledby=monthly-heading]')) === wantMonths)

  const wantLedger = pay?.ledger.length ?? 0
  check(`payment ledger has ${wantLedger} rows`,
    (await rows(`${PAY_SECTION} table:has(th:text-is("Running total"))`)) === wantLedger)

  const wantOwing = pay?.unpaid_weeks.length ?? 0
  check(`weeks-owing table has ${wantOwing} rows`,
    (await rows(`${PAY_SECTION} table:has(th:text-is("Still owing"))`)) === wantOwing)

  // ── the point of the whole exercise ──────────────────────────────────────
  // With no payments, owed and accrued are the same number, so every check
  // above passes whether or not the panel reads the right key. Only a scenario
  // with a payment in it can tell them apart.
  if (pay && pay.paid_minutes > 0 && pay.unpaid_minutes > 0) {
    const accrued = json.content.totals.above_contract_minutes
    const three = new Set([hours(accrued), hours(pay.paid_minutes), hours(pay.unpaid_minutes)])
    check('accrued, paid and owed read as three different numbers', three.size === 3,
      `${[...three].join(' / ')}`)
    check('owed headline is NOT the accrued figure', shown !== `${hours(accrued)} h`, `page "${shown}"`)
  }

  await page.close()
}

await browser.close()
copyFileSync(join(SCENARIOS_DIR, 'scenario-real.json'), DIST)
console.log(`\n${failures === 0 ? 'ALL CHECKS PASSED' : `${failures} CHECK(S) FAILED`}`)
process.exit(failures === 0 ? 0 : 1)
