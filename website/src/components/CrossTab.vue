<script setup lang="ts">
import type { WebData } from '../types/web-data'
import { minutesToHours, labelForBand, labelForClass } from '../lib/format'

const props = defineProps<{ data: WebData }>()

const bands = ['contracted', 'additional', 'overtime'] as const
const classes = ['daytime', 'weekday_night', 'saturday', 'sunday', 'bank_holiday'] as const
const crossTab = props.data.content.cross_tab
</script>

<template>
  <section aria-labelledby="crosstab-heading">
    <h2 id="crosstab-heading" class="text-lg font-semibold text-gray-900">
      Band &times; clock classification
    </h2>
    <p class="mt-1 text-sm text-gray-600">Hours in each band, split by clock classification.</p>
    <div class="mt-3 overflow-x-auto">
      <table class="w-full text-sm">
        <caption class="sr-only">Band by clock classification, in hours</caption>
        <thead>
          <tr class="border-b border-gray-300 text-left text-gray-600">
            <th scope="col" class="py-1.5 font-medium">Band</th>
            <th v-for="c in classes" :key="c" scope="col" class="py-1.5 text-right font-medium">
              {{ labelForClass(c) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in bands" :key="b" class="border-b border-gray-100">
            <th scope="row" class="py-1.5 text-left font-normal">{{ labelForBand(b) }}</th>
            <td v-for="c in classes" :key="c" class="py-1.5 text-right tabular-nums">
              {{ minutesToHours(crossTab[b][c]) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
