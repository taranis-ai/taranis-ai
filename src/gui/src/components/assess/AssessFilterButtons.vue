<template>
  <div class="ml-2 vertical-button-group">
    <filter-button
      v-model="storyFilter['read']"
      label="read"
      icon="mdi-eye-check-outline"
    />
    <filter-button
      v-model="storyFilter['important']"
      label="important"
      icon="mdi-star-check-outline"
    />
    <filter-button
      v-model="storyFilter['in_report']"
      label="in reports"
      icon="mdi-google-circles-communities"
    />
    <filter-button
      v-model="storyFilter['relevant']"
      label="relevant"
      icon="mdi-bullseye-arrow"
    />
    <multi-state-filter-button
      v-model="storyFilter['cybersecurity']"
      label="cybersecurity"
      icon="mdi-shield-outline"
      :values="['yes', 'no', 'mixed']"
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
