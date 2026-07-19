<script setup lang="ts">
import type { WebData } from '../types/web-data'
import { minutesToHours, minuteToClock, labelForWeekday, labelForDayType } from '../lib/format'

const props = defineProps<{ data: WebData }>()
const days = props.data.content.daily
</script>

<template>
  <section aria-labelledby="daily-heading">
    <h2 id="daily-heading" class="text-lg font-semibold text-gray-900">Daily log</h2>
    <div class="mt-3 max-h-96 overflow-y-auto rounded border border-gray-200">
      <table class="w-full text-sm">
        <thead class="sticky top-0 bg-white">
          <tr class="border-b border-gray-300 text-left text-gray-600">
            <th scope="col" class="px-3 py-1.5 font-medium">Date</th>
            <th scope="col" class="px-3 py-1.5 font-medium">Day</th>
            <th scope="col" class="px-3 py-1.5 font-medium">Type</th>
            <th scope="col" class="px-3 py-1.5 text-right font-medium">Start</th>
            <th scope="col" class="px-3 py-1.5 text-right font-medium">End</th>
            <th scope="col" class="px-3 py-1.5 text-right font-medium">Hours</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in days" :key="d.date" class="border-b border-gray-100">
            <td class="px-3 py-1.5 tabular-nums">{{ d.date }}</td>
            <td class="px-3 py-1.5">{{ labelForWeekday(d.iso_weekday) }}</td>
            <td class="px-3 py-1.5">
              <span
                :class="d.day_type === 'weekday'
                  ? 'text-gray-500'
                  : 'rounded bg-nhs-blue/10 px-1.5 py-0.5 text-xs font-medium text-nhs-blue'"
              >
                {{ labelForDayType(d.day_type) }}
              </span>
            </td>
            <td class="px-3 py-1.5 text-right tabular-nums">{{ minuteToClock(d.start_minute) }}</td>
            <td class="px-3 py-1.5 text-right tabular-nums">{{ minuteToClock(d.end_minute) }}</td>
            <td class="px-3 py-1.5 text-right tabular-nums">{{ minutesToHours(d.duration_minutes) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
