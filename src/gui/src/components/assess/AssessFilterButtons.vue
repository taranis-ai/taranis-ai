<template>
  <div class="vertical-button-group ml-2">
    <filter-button
      v-model="newsItemsFilter['read']"
      label="read"
      icon="mdi-eye-check-outline"
    />
    <filter-button
      v-model="newsItemsFilter['important']"
      label="important"
      icon="mdi-star-check-outline"
    />
    <filter-button
      v-model="newsItemsFilter['in_report']"
      label="items in reports"
      icon="mdi-google-circles-communities"
    />
    <filter-button
      v-model="newsItemsFilter['relevant']"
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
    const { newsItemsFilter } = storeToRefs(filterStore)

    return {
      newsItemsFilter
    }
  }
}
</script>
