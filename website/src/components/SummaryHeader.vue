<script setup lang="ts">
import type { WebData } from '../types/web-data'
import { minutesToHours } from '../lib/format'

const props = defineProps<{ data: WebData }>()

const totals = props.data.content.totals
// The engine computes this now (schema 1.2.0). It used to be additional +
// overtime added up here via sumMinutes, which was the browser's only piece of
// real arithmetic; that function is gone. Undefined means a file predating
// 1.2.0: show a dash rather than "NaN h", with lib/validate.ts explaining why.
const aboveContract = totals.above_contract_minutes
const subjectLine = props.data.meta.subject?.name
  ? [props.data.meta.subject.name, props.data.meta.subject.post].filter(Boolean).join(' — ')
  : 'Working-hours record'
const lastUpdated = props.data.meta.generated_at.replace('T', ' ').replace('Z', ' UTC')
</script>

<template>
  <header>
    <h1 class="text-2xl font-semibold text-gray-900">NHS Hours Dashboard</h1>
    <p class="mt-1 text-sm text-gray-600">
      {{ subjectLine }} ·
      {{ data.content.period.start }} to {{ data.content.period.end }} ·
      last updated {{ lastUpdated }}
    </p>

    <dl class="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div class="rounded border border-gray-200 p-4">
        <dt class="text-xs font-medium uppercase tracking-wide text-gray-500">Total hours</dt>
        <dd class="mt-1 text-2xl font-semibold tabular-nums text-gray-900">
          {{ minutesToHours(totals.total_minutes) }}
        </dd>
      </div>
      <div class="rounded border border-nhs-blue/40 bg-nhs-blue/5 p-4">
        <dt class="text-xs font-medium uppercase tracking-wide text-nhs-blue">Hours above contract</dt>
        <dd class="mt-1 text-2xl font-semibold tabular-nums text-nhs-blue">
          {{ aboveContract === undefined ? '—' : minutesToHours(aboveContract) }}
        </dd>
      </div>
      <div class="rounded border border-gray-200 p-4">
        <dt class="text-xs font-medium uppercase tracking-wide text-gray-500">Days worked</dt>
        <dd class="mt-1 text-2xl font-semibold tabular-nums text-gray-900">
          {{ totals.day_count }}
        </dd>
      </div>
      <div class="rounded border border-gray-200 p-4">
        <dt class="text-xs font-medium uppercase tracking-wide text-gray-500">Weeks active</dt>
        <dd class="mt-1 text-2xl font-semibold tabular-nums text-gray-900">
          {{ totals.week_count }}
        </dd>
      </div>
    </dl>
  </header>
</template>
