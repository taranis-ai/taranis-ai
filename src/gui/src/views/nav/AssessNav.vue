<template>
  <filter-navigation
    :search="search"
    :limit="newsItemsFilter.limit"
    :offset="newsItemsFilter.offset"
    @update:search="(value) => (search = value)"
    @update:limit="(value) => (newsItemsFilter.limit = value)"
    @update:offset="(value) => (newsItemsFilter.offset = value)"
  >
    <template #navdrawer>
      <!-- scope -->
      <v-row no-gutters class="ma-2 px-2">
        <v-col cols="12" class="py-1">
          <h4>Source</h4>
        </v-col>

        <v-col cols="12" class="pt-1">
          <v-autocomplete
            v-model="newsItemsFilter.group"
            :items="getOSINTSourceGroupsList"
            item-title="title"
            item-value="id"
            label="Source Group"
            :hide-details="true"
            variant="outlined"
            clearable
            clear-icon="mdi-close"
            multiple
            density="compact"
          />
        </v-col>

        <v-col cols="12" class="pt-2">
          <v-autocomplete
            v-model="newsItemsFilter.source"
            :items="getOSINTSourcesList"
            item-title="title"
            item-value="id"
            label="Source"
            :hide-details="true"
            variant="outlined"
            clearable
            clear-icon="mdi-close"
            multiple
            density="compact"
          />
        </v-col>
      </v-row>

      <v-divider class="my-2 mt-4"></v-divider>

      <v-row no-gutters class="ma-2 mb-0 px-2">
        <v-col cols="12" class="py-1">
          <h4>Filter</h4>
        </v-col>

        <v-col cols="12" class="pt-1">
          <date-chips v-model="newsItemsFilter.range" />
        </v-col>

        <v-col cols="12" class="pt-1">
          <tag-filter v-model="newsItemsFilter.tags" />
        </v-col>
      </v-row>

      <v-row no-gutters class="mt-0 mr-0 px-2">
        <v-col cols="12">
          <filter-select-list
            v-model="filterAttribute"
            :filter-attribute-options="filterAttributeOptions"
          />
        </v-col>
      </v-row>

      <v-divider class="my-2"></v-divider>

      <v-row no-gutters class="ma-2 ml-0 px-2">
        <v-col cols="12" class="ml-2 py-1">
          <h4>Sort</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <filter-sort-list v-model="newsItemsFilter.sort" />
        </v-col>
      </v-row>

      <v-divider class="my-2"></v-divider>

      <v-row no-gutters class="my-2 mb-0 px-2">
        <v-col cols="12" class="mx-2 py-1">
          <h4>Display</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <v-btn
            class="vertical-button toggle-button py-2 px-4 mb-1"
            :class="
              highlight ? 'toggle-button-checked' : 'toggle-button-unchecked'
            "
            value="highlight"
            prepend-icon="mdi-alphabetical-variant"
            :append-icon="highlight ? 'mdi-check-bold' : undefined"
            :variant="highlight ? 'tonal' : 'text'"
            color="primary"
            @click="highlight = !highlight"
          >
            highlight
          </v-btn>
        </v-col>
        <v-col cols="12" class="pt-0">
          <v-btn
            class="vertical-button toggle-button py-2 px-4 mb-1"
            :class="
              showWeekChart
                ? 'toggle-button-checked'
                : 'toggle-button-unchecked'
            "
            value="showWeekChart"
            prepend-icon="mdi-chart-bar"
            :append-icon="showWeekChart ? 'mdi-check-bold' : undefined"
            :variant="showWeekChart ? 'tonal' : 'text'"
            color="primary"
            @click="showWeekChart = !showWeekChart"
          >
            show charts
          </v-btn>
        </v-col>
      </v-row>

      <v-divider class="my-2 mt-1 mb-0"></v-divider>
      <v-row no-gutters class="ma-2 px-2">
        <v-col cols="12" class="py-0">
          <h4>Debug</h4>
        </v-col>
        <v-col cols="6" class="pt-2">chart threshold:</v-col>
        <v-col cols="6" class="pt-2">
          <input
            v-model="chartFilter.threshold"
            style="width: 100%"
            type="number"
            min="0"
        /></v-col>
        <v-col cols="6" class="pt-2">chart y2 Max:</v-col>
        <v-col cols="6" class="pt-2">
          <input
            v-model="chartFilter.y2max"
            style="width: 100%"
            type="number"
            min="0"
          />
        </v-col>
      </v-row>

      <v-divider class="my-2 mt-2 mb-0"></v-divider>
      <v-row no-gutters class="my-2 mr-0 px-2 pb-5">
        <v-col cols="12" class="py-2">
          <v-btn color="primary" block @click="resetFilter()">
            <v-icon left dark size="small" class="mr-3"> mdi-reload </v-icon>
            reset filter
          </v-btn>
        </v-col>
      </v-row>
    </template>
  </filter-navigation>
</template>

<script>
import dateChips from '@/components/assess/filter/dateChips.vue'
import tagFilter from '@/components/assess/filter/tagFilter.vue'
import filterSelectList from '@/components/assess/filter/filterSelectList.vue'
import filterSortList from '@/components/assess/filter/filterSortList.vue'
import FilterNavigation from '@/components/common/FilterNavigation.vue'
import { computed, onUnmounted, onBeforeMount } from 'vue'
import { useRoute } from 'vue-router'
import { useFilterStore } from '@/stores/FilterStore'
import { useAssessStore } from '@/stores/AssessStore'
import { storeToRefs } from 'pinia'
import { watch } from 'vue'

export default {
  name: 'AssessNav',
  components: {
    dateChips,
    tagFilter,
    filterSelectList,
    filterSortList,
    FilterNavigation
  },
  setup() {
    const assessStore = useAssessStore()
    const filterStore = useFilterStore()

    const { getOSINTSourceGroupsList, getOSINTSourcesList } =
      storeToRefs(assessStore)
    const { updateNewsItems } = assessStore
    const { newsItemsFilter, chartFilter, highlight, showWeekChart } =
      storeToRefs(filterStore)

    const { setFilter, updateFilter } = useFilterStore()

    const route = useRoute()

    const filterAttributeOptions = [
      { value: 'read', label: 'read', icon: 'mdi-eye-check-outline' },
      {
        value: 'important',
        label: 'important',
        icon: 'mdi-star-check-outline'
      },
      {
        value: 'in_report',
        label: 'items in reports',
        icon: 'mdi-google-circles-communities'
      },
      {
        value: 'relevant',
        label: 'relevant',
        icon: 'mdi-bullseye-arrow'
      }
    ]
    const filterAttribute = computed({
      get() {
        return filterAttributeOptions
          .filter((option) => newsItemsFilter.value[option.value])
          .map((option) => option.value)
      },
      set(value) {
        updateFilter(value)
        console.debug('filterAttributeSelections', value)
      }
    })

    const search = computed({
      get() {
        return newsItemsFilter.value.search
      },
      set(value) {
        updateFilter({ search: value })
      }
    })

    const updateQuery = () => {
      const query = Object.fromEntries(
        Object.entries(route.query).filter(([, v]) => v != null)
      )
      setFilter(query)
      console.debug('loaded with query', query)
    }

    onBeforeMount(() => {
      assessStore.updateOSINTSourceGroupsList()
      assessStore.updateOSINTSources()
      updateQuery()
    })

    onUnmounted(() => {
      filterStore.$reset()
    })

    const resetFilter = () => {
      assessStore.$reset()
      filterStore.$reset()
    }

    watch(
      newsItemsFilter,
      (filter, prevFilter) => {
        console.debug('filter changed', filter, prevFilter)
        updateNewsItems()
      },
      { deep: true }
    )

    return {
      search,
      chartFilter,
      highlight,
      showWeekChart,
      getOSINTSourceGroupsList,
      getOSINTSourcesList,
      newsItemsFilter,
      filterAttribute,
      filterAttributeOptions,
      resetFilter
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
  justify-content: flex-start;
}

.vertical-button-group .v-icon,
.vertical-button .v-icon {
  margin-right: 0.6rem;
  color: rgb(var(--v-theme-primary)) !important;
  font-size: 1.3rem !important;
}

.toggle-button {
  width: 100%;
}
.toggle-button-unchecked {
  color: black !important;
}
</style>
