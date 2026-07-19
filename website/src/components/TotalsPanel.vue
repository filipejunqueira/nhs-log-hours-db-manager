<script setup lang="ts">
import type { WebData } from '../types/web-data'
import { minutesToHours, labelForBand, labelForClass } from '../lib/format'

const props = defineProps<{ data: WebData }>()

const bands = ['contracted', 'additional', 'overtime'] as const
const classes = ['daytime', 'weekday_night', 'saturday', 'sunday', 'bank_holiday'] as const
const totals = props.data.content.totals
</script>

<template>
  <section aria-labelledby="totals-heading">
    <h2 id="totals-heading" class="text-lg font-semibold text-gray-900">Totals</h2>
    <div class="mt-3 grid gap-6 sm:grid-cols-2">
      <table class="w-full text-sm">
        <caption class="pb-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
          By threshold band
        </caption>
        <thead>
          <tr class="border-b border-gray-300 text-left text-gray-600">
            <th scope="col" class="py-1.5 font-medium">Band</th>
            <th scope="col" class="py-1.5 text-right font-medium">Hours</th>
            <th scope="col" class="py-1.5 text-right font-medium">Minutes</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in bands" :key="b" class="border-b border-gray-100">
            <td class="py-1.5">{{ labelForBand(b) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(totals.minutes_by_band[b]) }}</td>
            <td class="py-1.5 text-right tabular-nums text-gray-500">{{ totals.minutes_by_band[b] }}</td>
          </tr>
          <tr class="font-semibold">
            <td class="py-1.5">Total</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(totals.total_minutes) }}</td>
            <td class="py-1.5 text-right tabular-nums text-gray-500">{{ totals.total_minutes }}</td>
          </tr>
        </tbody>
      </table>

      <table class="w-full text-sm">
        <caption class="pb-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
          By clock classification
        </caption>
        <thead>
          <tr class="border-b border-gray-300 text-left text-gray-600">
            <th scope="col" class="py-1.5 font-medium">Class</th>
            <th scope="col" class="py-1.5 text-right font-medium">Hours</th>
            <th scope="col" class="py-1.5 text-right font-medium">Minutes</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in classes" :key="c" class="border-b border-gray-100">
            <td class="py-1.5">{{ labelForClass(c) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(totals.minutes_by_class[c]) }}</td>
            <td class="py-1.5 text-right tabular-nums text-gray-500">{{ totals.minutes_by_class[c] }}</td>
          </tr>
          <tr class="font-semibold">
            <td class="py-1.5">Total</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(totals.total_minutes) }}</td>
            <td class="py-1.5 text-right tabular-nums text-gray-500">{{ totals.total_minutes }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
