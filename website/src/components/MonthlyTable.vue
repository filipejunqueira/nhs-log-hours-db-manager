<script setup lang="ts">
// Calendar-month breakdown, mirroring WeeklyTable.
import type { WebData } from '../types/web-data'
import { minutesToHours } from '../lib/format'

const props = defineProps<{ data: WebData }>()

const months = props.data.content.monthly
</script>

<template>
  <section v-if="months" aria-labelledby="monthly-heading">
    <h2 id="monthly-heading" class="text-lg font-semibold text-gray-900">Monthly breakdown</h2>
    <p class="mt-1 text-sm text-gray-600">
      Each minute counts towards the calendar month it was worked in. Bands are always
      decided by the Monday-to-Sunday pay-week, so a week spanning the end of a month
      contributes minutes to both months carrying the bands its week assigned. Months are
      never re-banded against a monthly baseline.
    </p>
    <div class="mt-3 overflow-x-auto">
      <table class="w-full min-w-[40rem] text-sm">
        <thead>
          <tr class="border-b border-gray-300 text-left text-gray-600">
            <th scope="col" class="py-1.5 pr-2 font-medium">Month</th>
            <th scope="col" class="py-1.5 text-right font-medium">Days</th>
            <th scope="col" class="py-1.5 text-right font-medium">Total h</th>
            <th scope="col" class="py-1.5 text-right font-medium">Contracted</th>
            <th scope="col" class="py-1.5 text-right font-medium">Additional</th>
            <th scope="col" class="py-1.5 text-right font-medium">Overtime</th>
            <th scope="col" class="py-1.5 text-right font-medium">Night</th>
            <th scope="col" class="py-1.5 text-right font-medium">Sat</th>
            <th scope="col" class="py-1.5 text-right font-medium">Sun</th>
            <th scope="col" class="py-1.5 text-right font-medium">Bank hol.</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in months" :key="m.month" class="border-b border-gray-100">
            <td class="py-1.5 pr-2 tabular-nums">{{ m.month }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ m.day_count }}</td>
            <td class="py-1.5 text-right font-medium tabular-nums">{{ minutesToHours(m.total_minutes) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(m.minutes_by_band.contracted) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(m.minutes_by_band.additional) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(m.minutes_by_band.overtime) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(m.minutes_by_class.weekday_night) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(m.minutes_by_class.saturday) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(m.minutes_by_class.sunday) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(m.minutes_by_class.bank_holiday) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
