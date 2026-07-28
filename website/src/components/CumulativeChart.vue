<script setup lang="ts">
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  LineController,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  type ChartData,
  type ChartOptions,
} from 'chart.js'
import type { WebData } from '../types/web-data'
import { minutesToHours, minutesToHoursValue } from '../lib/format'

ChartJS.register(LineController, CategoryScale, LinearScale, PointElement, LineElement, Tooltip)

const props = defineProps<{ data: WebData }>()

// Read props inside the computed, not once at setup: a snapshot taken here
// would make this computed unable to ever recompute, which is misleading in a
// wrapper whose whole purpose is to track its source. The other components
// snapshot deliberately — they do not claim reactivity.
const chartData = computed<ChartData<'line'>>(() => ({
  labels: props.data.content.cumulative.map((p) => p.date),
  datasets: [
    {
      label: 'Cumulative hours',
      // Plotted in hours, not minutes, so Chart.js picks round-hour ticks.
      data: props.data.content.cumulative.map((p) => minutesToHoursValue(p.cumulative_minutes)),
      borderColor: '#005eb8',
      backgroundColor: '#005eb8',
      pointRadius: 2,
      tension: 0,
    },
  ],
}))

/** Text equivalent of the chart. The running total appears in no table on the
 *  page, so without this a screen reader gets the heading and nothing else. */
const summary = computed(() => {
  const points = props.data.content.cumulative
  const first = points[0]
  const last = points[points.length - 1]
  if (!first || !last) return 'No cumulative data available.'
  return (
    `Running total over ${points.length} days: ` +
    `${minutesToHours(first.cumulative_minutes)} hours on ${first.date}, ` +
    `rising to ${minutesToHours(last.cumulative_minutes)} hours on ${last.date}.`
  )
})

const chartOptions: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        // Formatted from the original minutes, so the exact 2 dp figure comes
        // from format.ts rather than from the plotted (already divided) value.
        label: (ctx) => {
          const point = props.data.content.cumulative[ctx.dataIndex]
          return point ? `${minutesToHours(point.cumulative_minutes)} h` : ''
        },
      },
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        callback: (value) => `${value} h`,
      },
    },
  },
}
</script>

<template>
  <section aria-labelledby="cumulative-heading">
    <h2 id="cumulative-heading" class="text-lg font-semibold text-gray-900">Cumulative hours</h2>
    <p class="mt-1 text-sm text-gray-600">Running total of hours worked over the period.</p>
    <p class="sr-only">{{ summary }}</p>
    <div class="mt-3 h-64">
      <Line :data="chartData" :options="chartOptions" />
    </div>
  </section>
</template>
