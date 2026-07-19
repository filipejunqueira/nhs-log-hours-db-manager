<script setup lang="ts">
import type { WebData } from '../types/web-data'
import { minutesToHours } from '../lib/format'

const props = defineProps<{ data: WebData }>()
const ig = props.data.content.integrity

const checks: { key: keyof typeof ig; label: string; detail: string }[] = [
  { key: 'conservation_ok', label: 'Conservation', detail: 'Raw minutes equal segmented minutes' },
  { key: 'partitions_ok', label: 'Partitions', detail: 'Band and class splits each sum to the total' },
  { key: 'uniqueness_ok', label: 'Uniqueness', detail: 'Every segment counted exactly once' },
  { key: 'banding_formula_ok', label: 'Banding formula', detail: 'Weekly banding follows the 22.5 h-first rule' },
  { key: 'crosstab_ok', label: 'Cross-tab', detail: 'Band × class table reconciles to both margins' },
  { key: 'span_ok', label: 'Day span', detail: 'No day exceeds its clock span; no overlapping periods' },
]
</script>

<template>
  <section aria-labelledby="integrity-heading">
    <h2 id="integrity-heading" class="text-lg font-semibold text-gray-900">Integrity checks</h2>
    <p class="mt-1 text-sm text-gray-600">
      These checks are computed by the engine on every run, not asserted by this page.
    </p>
    <ul class="mt-3 grid gap-2 sm:grid-cols-2">
      <li
        v-for="c in checks"
        :key="c.key"
        class="flex items-start gap-2 rounded border border-gray-200 p-3 text-sm"
      >
        <span
          :class="ig[c.key] ? 'text-green-700' : 'text-red-700'"
          aria-hidden="true"
          class="font-bold"
        >{{ ig[c.key] ? '✓' : '✗' }}</span>
        <span>
          <span class="font-medium text-gray-900">{{ c.label }}</span>
          <span class="sr-only">: {{ ig[c.key] ? 'passed' : 'FAILED' }}</span>
          <br />
          <span class="text-gray-600">{{ c.detail }}</span>
        </span>
      </li>
    </ul>
    <dl class="mt-3 space-y-1 text-sm text-gray-700">
      <div>
        <dt class="inline font-medium">Raw vs segmented total:</dt>
        <dd class="inline tabular-nums">
          {{ ig.total_raw_minutes }} min = {{ ig.total_segment_minutes }} min
          ({{ minutesToHours(ig.total_raw_minutes) }} h)
        </dd>
      </div>
      <div>
        <dt class="inline font-medium">Unsocial minutes within the contracted baseline:</dt>
        <dd class="inline tabular-nums">{{ ig.unsocial_within_baseline_minutes }}</dd>
      </div>
      <div>
        <dt class="inline font-medium">Engine warnings:</dt>
        <dd class="inline">
          <template v-if="ig.warnings.length === 0">none</template>
          <ul v-else class="mt-1 list-disc pl-5 text-amber-900">
            <li v-for="(w, i) in ig.warnings" :key="i">{{ w }}</li>
          </ul>
        </dd>
      </div>
    </dl>
  </section>
</template>
