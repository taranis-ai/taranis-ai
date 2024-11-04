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
            {{ $t('analyze.new_report') }}
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
import { computed, onUnmounted } from 'vue'
import { useFilterStore } from '@/stores/FilterStore'
import FilterNavigation from '@/components/common/FilterNavigation.vue'
import dateChips from '@/components/analyze/dateChips.vue'
import filterButton from '@/components/common/filter/filterButton.vue'
import { storeToRefs } from 'pinia'
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
    const { reportFilter } = storeToRefs(filterStore)

    const search = computed({
      get() {
        return reportFilter.value.search
      },
      set(value) {
        filterStore.updateReportFilter({ search: value })
      }
    })

    function addReport() {
      router.push('/report/')
    }

    onUnmounted(() => {
      filterStore.setReportFilter({})
    })

    return {
      search,
      reportFilter,
      addReport
    }
  }
}
</script>

<style lang="scss">
button {
  display: flex !important;
}
</style>
