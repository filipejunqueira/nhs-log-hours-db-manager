<script setup lang="ts">
// The five-second read: how many extra hours are still unpaid, and since when.
//
// This is the only panel that answers the question the site exists for, so it
// sits directly under the header. It renders nothing at all if the engine did
// not emit a payments block — lib/validate.ts raises the warning in that case,
// and a missing panel is far better than a wrong owed figure.
import type { WebData } from '../types/web-data'
import { minutesToHours } from '../lib/format'

const props = defineProps<{ data: WebData }>()

const payments = props.data.content.payments
const lastPayment = payments?.ledger.at(-1) ?? null
</script>

<template>
  <section v-if="payments" aria-labelledby="owed-heading">
    <h2 id="owed-heading" class="sr-only">Hours owed</h2>

    <div class="rounded border border-nhs-blue/40 bg-nhs-blue/5 p-5">
      <p class="text-xs font-medium uppercase tracking-wide text-nhs-blue">
        Extra hours worked but not yet paid
      </p>
      <p class="mt-1 text-4xl font-semibold tabular-nums text-nhs-blue">
        {{ minutesToHours(payments.unpaid_minutes) }} h
      </p>

      <p class="mt-3 text-sm text-gray-700">
        Of the {{ minutesToHours(data.content.totals.above_contract_minutes ?? 0) }} h worked
        above the contracted
        {{ minutesToHours(data.meta.contract.contracted_weekly_minutes) }} h a week,
        <span class="font-medium">{{ minutesToHours(payments.paid_minutes) }} h</span>
        {{ payments.paid_minutes === 0 ? 'have been settled so far.' : 'have been settled.' }}
      </p>

      <dl class="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt class="text-gray-500">Settled up to</dt>
          <dd class="tabular-nums font-medium text-gray-900">
            {{ payments.paid_up_to ?? 'nothing settled yet' }}
          </dd>
        </div>
        <div>
          <dt class="text-gray-500">Last payment</dt>
          <dd class="tabular-nums font-medium text-gray-900">
            <template v-if="lastPayment">
              {{ lastPayment.date }} · {{ minutesToHours(lastPayment.minutes_paid) }} h
            </template>
            <template v-else>none recorded</template>
          </dd>
        </div>
        <div>
          <dt class="text-gray-500">Weeks still owing</dt>
          <dd class="tabular-nums font-medium text-gray-900">
            {{ payments.unpaid_weeks.length }}
          </dd>
        </div>
      </dl>

      <p
        v-if="payments.overpaid_minutes > 0"
        class="mt-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
      >
        <span class="font-medium">
          {{ minutesToHours(payments.overpaid_minutes) }} h more has been paid than the log
          records as worked above contract.
        </span>
        That is either a genuine overpayment or a sign this hours log is behind the
        spreadsheet. It is reported rather than treated as an error.
      </p>

      <ul
        v-if="payments.warnings.length"
        class="mt-4 list-disc space-y-1 rounded border border-amber-300 bg-amber-50 p-3 pl-8 text-sm text-amber-900"
      >
        <li v-for="w in payments.warnings" :key="w">{{ w }}</li>
      </ul>

      <p class="mt-4 text-xs text-gray-500">
        Hours only. What those hours are worth is determined separately and is not shown
        anywhere on this page. Unsocial time falling inside the contracted
        {{ minutesToHours(data.meta.contract.contracted_weekly_minutes) }} h is enhanced but
        is not above contract, so it is not counted here.
      </p>
    </div>
  </section>
</template>
