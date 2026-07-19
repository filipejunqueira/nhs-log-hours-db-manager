<script setup lang="ts">
import type { WebData } from '../types/web-data'
import { minutesToHours, minuteToClock, labelForClass } from '../lib/format'

const props = defineProps<{ data: WebData }>()

const weeks = props.data.content.weekly
const flaggedWeeks = weeks.filter((w) => w.flagged_segments.length > 0)
</script>

<template>
  <section aria-labelledby="weekly-heading">
    <h2 id="weekly-heading" class="text-lg font-semibold text-gray-900">Weekly breakdown</h2>
    <p class="mt-1 text-sm text-gray-600">
      Pay-week is Monday to Sunday. Banding is chronological within each week:
      the first {{ minutesToHours(data.meta.contract.contracted_weekly_minutes) }} h are
      contracted, the next up to
      {{ minutesToHours(data.meta.contract.fulltime_weekly_minutes) }} h total are additional,
      the rest overtime.
    </p>
    <div class="mt-3 overflow-x-auto">
      <table class="w-full min-w-[44rem] text-sm">
        <thead>
          <tr class="border-b border-gray-300 text-left text-gray-600">
            <th scope="col" class="py-1.5 pr-2 font-medium">Week</th>
            <th scope="col" class="py-1.5 pr-2 font-medium">w/c</th>
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
          <tr v-for="w in weeks" :key="w.iso_week" class="border-b border-gray-100">
            <td class="py-1.5 pr-2 tabular-nums">{{ w.iso_week }}</td>
            <td class="py-1.5 pr-2 tabular-nums text-gray-500">{{ w.monday }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ w.day_count }}</td>
            <td class="py-1.5 text-right font-medium tabular-nums">{{ minutesToHours(w.total_minutes) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(w.minutes_by_band.contracted) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(w.minutes_by_band.additional) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(w.minutes_by_band.overtime) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(w.minutes_by_class.weekday_night) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(w.minutes_by_class.saturday) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ minutesToHours(w.minutes_by_class.sunday) }}</td>
            <td class="py-1.5 text-right tabular-nums">
              {{ minutesToHours(w.minutes_by_class.bank_holiday) }}
              <span
                v-if="w.unsocial_within_baseline_minutes > 0"
                class="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800"
                :title="`${w.unsocial_within_baseline_minutes} unsocial minutes fell within the contracted baseline this week`"
              >
                flag
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="flaggedWeeks.length > 0" class="mt-3 rounded border border-amber-300 bg-amber-50 p-3 text-sm">
      <p class="font-medium text-amber-900">
        Unsocial time inside the contracted baseline (classified strictly, flagged for the
        money layer to decide — never suppressed):
      </p>
      <ul class="mt-1 list-disc pl-5 text-amber-900">
        <li v-for="w in flaggedWeeks" :key="w.iso_week">
          {{ w.iso_week }}:
          <span v-for="(s, i) in w.flagged_segments" :key="i" class="tabular-nums">
            {{ s.date }} {{ minuteToClock(s.start_minute) }}–{{ minuteToClock(s.end_minute) }}
            ({{ minutesToHours(s.duration_minutes) }} h {{ labelForClass(s.unsocial_class) }})<span
              v-if="i < w.flagged_segments.length - 1">, </span>
          </span>
        </li>
      </ul>
    </div>
  </section>
</template>
