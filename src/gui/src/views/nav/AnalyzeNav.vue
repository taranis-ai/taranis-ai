<template>
  <filter-navigation
    :search="reportFilter.search"
    :limit="reportFilter.limit"
    :offset="reportFilter.offset"
    @update:search="(value) => (search = value)"
    @update:limit="(value) => (reportFilter.limit = value)"
    @update:offset="(value) => (reportFilter.offset = value)"
  >
    <template #navdrawer>
      <v-row class="my-2 mr-0 px-2 pb-5">
        <v-col cols="12" align-self="center" class="py-1">
          <v-btn color="primary" block @click="addReport()">
            <v-icon left dark> mdi-file-document-plus-outline </v-icon>
            New Report
          </v-btn>
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>
      <v-row class="my-2 mr-0 px-2">
        <v-col cols="12" class="py-0">
          <h4>Filter</h4>
        </v-col>

        <v-col cols="12" class="pb-0">
          <date-chips v-model="reportFilter.range" />
        </v-col>

        <v-divider class="mt-3 mb-3"></v-divider>

        <v-col cols="12" class="pt-1">
          <filter-select-list
            v-model="filterAttribute"
            :filter-attribute-options="filterAttributeOptions"
          />
        </v-col>
      </v-row>
    </template>
  </filter-navigation>
</template>

<script>
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { useFilterStore } from '@/stores/FilterStore'
import FilterNavigation from '@/components/common/FilterNavigation.vue'
import dateChips from '@/components/assess/filter/dateChips.vue'
import filterSelectList from '@/components/assess/filter/filterSelectList.vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import { router } from '@/router'

export default {
  name: 'AnalyzeNav',
  components: {
    dateChips,
    filterSelectList,
    FilterNavigation
  },
  setup() {
    const filterStore = useFilterStore()
    const analyzeStore = useAnalyzeStore()
    const { reportFilter } = storeToRefs(filterStore)
    const { updateReportFilter, setReportFilter } = filterStore
    const updateReportItems = analyzeStore.updateReportItems

    const route = useRoute()

    const search = computed({
      get() {
        return reportFilter.value.search
      },
      set(value) {
        updateReportFilter({ search: value })
      }
    })
    const filterAttributeOptions = [
      { value: 'completed', label: 'completed', icon: 'mdi-progress-check' },
      { value: 'incompleted', label: 'incomplete', icon: 'mdi-progress-close' }
    ]

    const filterAttribute = computed({
      get() {
        return filterAttributeOptions
          .filter((option) => reportFilter.value[option.value])
          .map((option) => option.value)
      },
      set(value) {
        updateReportFilter(value)
        console.debug('filterAttributeSelections', value)
      }
    })

    function addReport() {
      router.push('/report/0')
    }

    onMounted(() => {
      const query = Object.fromEntries(
        Object.entries(route.query).filter(([, v]) => v != null)
      )
      updateReportFilter(query)
      console.debug('loaded with query', query)
    })

    onUnmounted(() => {
      setReportFilter({})
    })

    watch(
      reportFilter,
      (filter, prevFilter) => {
        console.debug('filter changed', filter, prevFilter)
        updateReportItems()
      },
      { deep: true }
    )

    return {
      reportFilter,
      updateReportFilter,
      updateReportItems,
      search,
      filterAttributeOptions,
      filterAttribute,
      addReport
    }
  }
}
</script>
