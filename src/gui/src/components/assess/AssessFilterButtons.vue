<template>
  <div class="ml-2 vertical-button-group">
    <filter-button
      v-model="storyFilter['read']"
      label="read"
      icon="mdi-eye-check-outline"
      data-testid="filter-read-btn"
    />
    <filter-button
      v-model="storyFilter['important']"
      label="important"
      icon="mdi-star-check-outline"
      data-testid="filter-important-btn"
    />
    <filter-button
      v-model="storyFilter['in_report']"
      label="in reports"
      icon="mdi-google-circles-communities"
      data-testid="filter-in-report-btn"
    />
    <filter-button
      v-model="storyFilter['relevant']"
      label="relevant"
      icon="mdi-bullseye-arrow"
      data-testid="filter-relevance-btn"
    />
    <multi-state-filter-button
      v-model="storyFilter['cybersecurity']"
      label="cybersecurity"
      icon="mdi-shield-outline"
      :values="['yes', 'no', 'mixed', 'incomplete']"
      data-testid="filter-cybersecurity-btn"
    />
  </div>
</template>

<script>
import filterButton from '@/components/common/filter/filterButton.vue'
import multiStateFilterButton from '@/components/common/filter/multiStateFilterButton.vue'
import { useFilterStore } from '@/stores/FilterStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'AssessFilterButtons',
  components: {
    filterButton,
    multiStateFilterButton
  },
  props: {},
  setup() {
    const filterStore = useFilterStore()
    const { storyFilter } = storeToRefs(filterStore)

    return {
      storyFilter
    }
  }
}
</script>
