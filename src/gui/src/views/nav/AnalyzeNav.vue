<template>
  <filter-navigation
    :search="reportFilter.search"
    :limit="reportFilter.limit"
    @update:search="(value) => (search = value)"
    @update:limit="(value) => (reportFilter.limit = value)"
  >
    <template #navdrawer>
      <v-row no-gutters class="px-2">
        <v-col cols="12" align-self="center" class="py-1">
          <v-btn color="primary" block @click="addReport()">
            <v-icon left dark> mdi-file-document-plus-outline </v-icon>
            New Report
          </v-btn>
        </v-col>
      </v-row>

      <v-row no-gutters class="my-2 mr-0 px-2">
        <v-col cols="12" class="py-0">
          <h4 class="text-center">Filter</h4>
        </v-col>

        <v-col cols="12" class="pb-0">
          <date-chips v-model="reportFilter.range" />
        </v-col>

        <v-divider class="mt-3 mb-3"></v-divider>

        <v-col cols="12" class="pt-1">
          <filter-button
            v-model="reportFilter['completed']"
            label="completed"
            icon="mdi-progress-check"
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
import dateChips from '@/components/common/filter/dateChips.vue'
import filterButton from '@/components/common/filter/filterButton.vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import { router } from '@/router'

export default {
  name: 'AnalyzeNav',
  components: {
    dateChips,
    filterButton,
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
      addReport
    }
  }
}
</script>

<style lang="scss">
button {
  display: flex !important;
}

button.vertical-button .v-btn__append,
button.vertical-button .v-btn__append i {
  margin-left: auto;
  font-size: 100% !important;
}

.vertical-button-group {
  display: flex;
  flex-direction: column;
  height: 100% !important;
}

.vertical-button {
  width: 100%;
  justify-content: flex-start;
}

.vertical-button-group .v-icon,
.vertical-button .v-icon {
  margin-right: 0.6rem;
  color: rgb(var(--v-theme-primary)) !important;
  font-size: 1.3rem !important;
}
</style>
