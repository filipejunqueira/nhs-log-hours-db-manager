<script setup lang="ts">
import type { WebData } from '../types/web-data'
import { minutesToHours, minuteToClock, labelForBand, labelForClass } from '../lib/format'

const props = defineProps<{ data: WebData }>()

const bands = ['contracted', 'additional', 'overtime'] as const
const classes = ['daytime', 'weekday_night', 'saturday', 'sunday', 'bank_holiday'] as const
const stats = props.data.content.statistics
</script>

<template>
  <section aria-labelledby="stats-heading">
    <h2 id="stats-heading" class="text-lg font-semibold text-gray-900">Distribution &amp; averages</h2>

    <div class="mt-3 grid gap-6 sm:grid-cols-2">
      <table class="w-full text-sm">
        <caption class="pb-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
          Share of hours by band
        </caption>
        <thead>
          <tr class="border-b border-gray-300 text-left text-gray-600">
            <th scope="col" class="py-1.5 font-medium">Band</th>
            <th scope="col" class="py-1.5 text-right font-medium">Share</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in bands" :key="b" class="border-b border-gray-100">
            <td class="py-1.5">{{ labelForBand(b) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ stats.pct_by_band[b] }}%</td>
          </tr>
        </tbody>
      </table>

      <table class="w-full text-sm">
        <caption class="pb-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
          Share of hours by clock classification
        </caption>
        <thead>
          <tr class="border-b border-gray-300 text-left text-gray-600">
            <th scope="col" class="py-1.5 font-medium">Class</th>
            <th scope="col" class="py-1.5 text-right font-medium">Share</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in classes" :key="c" class="border-b border-gray-100">
            <td class="py-1.5">{{ labelForClass(c) }}</td>
            <td class="py-1.5 text-right tabular-nums">{{ stats.pct_by_class[c] }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <dl class="mt-6 grid gap-x-6 gap-y-1 text-sm text-gray-700 sm:grid-cols-2">
      <div>
        <dt class="inline font-medium">Mean hours per day:</dt>
        <dd class="inline tabular-nums">{{ minutesToHours(stats.mean_minutes_per_day) }} h</dd>
      </div>
      <div>
        <dt class="inline font-medium">Mean hours per week:</dt>
        <dd class="inline tabular-nums">{{ minutesToHours(stats.mean_minutes_per_week) }} h</dd>
      </div>
      <div>
        <dt class="inline font-medium">Mean start time:</dt>
        <dd class="inline tabular-nums">{{ minuteToClock(stats.mean_start_minute) }}</dd>
      </div>
      <div>
        <dt class="inline font-medium">Mean end time:</dt>
        <dd class="inline tabular-nums">{{ minuteToClock(stats.mean_end_minute) }}</dd>
      </div>
      <div>
        <dt class="inline font-medium">Longest day:</dt>
        <dd class="inline tabular-nums">
          {{ stats.longest_day.date }} ({{ minutesToHours(stats.longest_day.minutes) }} h)
        </dd>
      </div>
      <div>
        <dt class="inline font-medium">Shortest day:</dt>
        <dd class="inline tabular-nums">
          {{ stats.shortest_day.date }} ({{ minutesToHours(stats.shortest_day.minutes) }} h)
        </dd>
      </div>
    </dl>

    <table class="mt-6 w-full text-sm">
      <caption class="pb-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
        Days touching each clock classification
      </caption>
      <thead>
        <tr class="border-b border-gray-300 text-left text-gray-600">
          <th v-for="c in classes" :key="c" scope="col" class="py-1.5 text-right font-medium">
            {{ labelForClass(c) }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td v-for="c in classes" :key="c" class="py-1.5 text-right tabular-nums">
            {{ stats.days_touching_class[c] }}
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
