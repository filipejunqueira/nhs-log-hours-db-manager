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
import { minutesToHours } from '../lib/format'

ChartJS.register(LineController, CategoryScale, LinearScale, PointElement, LineElement, Tooltip)

const props = defineProps<{ data: WebData }>()

const cumulative = props.data.content.cumulative

const chartData = computed<ChartData<'line'>>(() => ({
  labels: cumulative.map((p) => p.date),
  datasets: [
    {
      label: 'Cumulative hours',
      data: cumulative.map((p) => p.cumulative_minutes),
      borderColor: '#005eb8',
      backgroundColor: '#005eb8',
      pointRadius: 2,
      tension: 0,
    },
  ],
}))

const chartOptions: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `${minutesToHours(Number(ctx.parsed.y))} h`,
      },
    },
  },
  scales: {
    y: {
      ticks: {
        callback: (value) => `${minutesToHours(Number(value))} h`,
      },
    },
  },
}
</script>

<template>
  <section aria-labelledby="cumulative-heading">
    <h2 id="cumulative-heading" class="text-lg font-semibold text-gray-900">Cumulative hours</h2>
    <p class="mt-1 text-sm text-gray-600">Running total of hours worked over the period.</p>
    <div class="mt-3 h-64">
      <Line :data="chartData" :options="chartOptions" />
    </div>
  </section>
</template>
