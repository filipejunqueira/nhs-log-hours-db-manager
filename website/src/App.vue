<script setup lang="ts">
import { useHoursData } from './composables/useHoursData'
import SummaryHeader from './components/SummaryHeader.vue'
import TotalsPanel from './components/TotalsPanel.vue'
import WeeklyTable from './components/WeeklyTable.vue'
import DailyTable from './components/DailyTable.vue'
import MethodologyPanel from './components/MethodologyPanel.vue'
import IntegrityPanel from './components/IntegrityPanel.vue'
import CrossTab from './components/CrossTab.vue'
import CumulativeChart from './components/CumulativeChart.vue'
import StatsPanel from './components/StatsPanel.vue'

const { data, loading, error } = useHoursData()
const appVersion = __APP_VERSION__
</script>

<template>
  <main class="mx-auto max-w-5xl px-4 py-8 text-gray-900 sm:px-6">
    <p v-if="loading" class="text-sm text-gray-600" role="status">Loading hours data…</p>

    <div
      v-else-if="error"
      class="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900"
      role="alert"
    >
      <p class="font-semibold">Could not load the hours data.</p>
      <p class="mt-1">{{ error }}</p>
    </div>

    <template v-else-if="data">
      <SummaryHeader :data="data" />
      <div class="mt-10 space-y-10">
        <TotalsPanel :data="data" />
        <WeeklyTable :data="data" />
        <DailyTable :data="data" />
        <MethodologyPanel :data="data" />
        <IntegrityPanel :data="data" />
        <CrossTab :data="data" />
        <CumulativeChart :data="data" />
        <StatsPanel :data="data" />
      </div>
      <footer class="mt-10 border-t border-gray-200 pt-4 text-xs text-gray-500">
        Website v{{ appVersion }} · Schema {{ data.meta.schema_version }} · all durations recorded
        in integer minutes · this page shows hours only; rates and pay are determined separately.
      </footer>
    </template>
  </main>
</template>
