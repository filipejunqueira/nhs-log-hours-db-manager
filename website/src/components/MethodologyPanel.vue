<script setup lang="ts">
import type { WebData } from '../types/web-data'

const props = defineProps<{ data: WebData }>()
const meta = props.data.meta
</script>

<template>
  <section aria-labelledby="methodology-heading">
    <h2 id="methodology-heading" class="text-lg font-semibold text-gray-900">
      How these hours are computed
    </h2>
    <ol class="mt-3 list-decimal space-y-1.5 pl-5 text-sm text-gray-800">
      <li v-for="(line, i) in meta.methodology" :key="i">{{ line }}</li>
    </ol>
    <p class="mt-3 text-xs text-gray-500">
      {{ meta.unit_note }} All figures on this page are computed by the hours engine;
      the page itself only formats them for display.
    </p>
  </section>
</template>
