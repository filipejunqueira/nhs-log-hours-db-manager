<script setup lang="ts">
// The payment ledger, and the weeks still owing.
//
// No note column, deliberately: the spreadsheet's free text never reaches
// web_data.json, so there is nothing here that could carry an amount onto a
// public page.
import type { WebData } from '../types/web-data'
import { minutesToHours } from '../lib/format'

const props = defineProps<{ data: WebData }>()

const payments = props.data.content.payments
</script>

<template>
  <section v-if="payments" aria-labelledby="payments-heading">
    <h2 id="payments-heading" class="text-lg font-semibold text-gray-900">Payments</h2>
    <p class="mt-1 text-sm text-gray-600">
      One row per payment received. Each payment settles the oldest unsettled pay-week
      first; the total still owed does not depend on that ordering.
    </p>

    <p v-if="payments.ledger.length === 0" class="mt-3 text-sm text-gray-600">
      No payments have been recorded, so every hour worked above contract is still
      outstanding.
    </p>

    <div v-else class="mt-3 overflow-x-auto">
      <table class="w-full min-w-[24rem] text-sm">
        <thead>
          <tr class="border-b border-gray-300 text-left text-gray-600">
            <th scope="col" class="py-1.5 pr-2 font-medium">Date</th>
            <th scope="col" class="py-1.5 text-right font-medium">Hours paid</th>
            <th scope="col" class="py-1.5 text-right font-medium">Running total</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in payments.ledger" :key="`${e.date}-${e.cumulative_paid_minutes}`" class="border-b border-gray-100">
            <td class="py-1.5 pr-2 tabular-nums">{{ e.date }}</td>
            <td class="py-1.5 text-right font-medium tabular-nums">{{ minutesToHours(e.minutes_paid) }}</td>
            <td class="py-1.5 text-right tabular-nums text-gray-500">{{ minutesToHours(e.cumulative_paid_minutes) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <template v-if="payments.unpaid_weeks.length">
      <h3 class="mt-6 text-base font-semibold text-gray-900">Weeks still owing</h3>
      <p class="mt-1 text-sm text-gray-600">
        Extra hours are those above the contracted
        {{ minutesToHours(data.meta.contract.contracted_weekly_minutes) }} h a week, that is
        additional plus overtime.
      </p>
      <div class="mt-3 overflow-x-auto">
        <table class="w-full min-w-[28rem] text-sm">
          <thead>
            <tr class="border-b border-gray-300 text-left text-gray-600">
              <th scope="col" class="py-1.5 pr-2 font-medium">Week</th>
              <th scope="col" class="py-1.5 pr-2 font-medium">w/c</th>
              <th scope="col" class="py-1.5 text-right font-medium">Extra h</th>
              <th scope="col" class="py-1.5 text-right font-medium">Still owing</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="w in payments.unpaid_weeks" :key="w.iso_week" class="border-b border-gray-100">
              <td class="py-1.5 pr-2 tabular-nums">{{ w.iso_week }}</td>
              <td class="py-1.5 pr-2 tabular-nums text-gray-500">{{ w.monday }}</td>
              <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(w.extra_minutes) }}</td>
              <td class="py-1.5 text-right font-medium tabular-nums">{{ minutesToHours(w.unpaid_minutes) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>
