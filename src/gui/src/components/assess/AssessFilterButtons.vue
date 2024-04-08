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
      label="items in reports"
      icon="mdi-google-circles-communities"
    />
    <filter-button
      v-model="storyFilter['relevant']"
      label="relevant"
      icon="mdi-bullseye-arrow"
    />
  </div>
</template>

<script>
import filterButton from '@/components/common/filter/filterButton.vue'
import { useFilterStore } from '@/stores/FilterStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'AssessFilterButtons',
  components: {
    filterButton
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
