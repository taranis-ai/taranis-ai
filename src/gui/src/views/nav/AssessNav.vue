<template>
  <filter-navigation
    :search="search"
    :limit="newsItemsFilter.limit"
    :offset="newsItemsFilter.offset"
    @update:search="(value) => (search = value)"
    @update:limit="(value) => (newsItemsFilter.limit = value)"
    @update:offset="(value) => (newsItemsFilter.offset = value)"
  >
    <template #appbar>
      <filter-button
        v-if="smAndUp"
        v-model="newsItemsFilter['read']"
        :label="mdAndDown ? '' : 'read'"
        icon="mdi-eye-check-outline"
      />
      <filter-button
        v-if="smAndUp"
        v-model="newsItemsFilter['in_report']"
        :label="mdAndDown ? '' : 'items in reports'"
        icon="mdi-google-circles-communities"
      />
    </template>
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
          <date-chips v-model="filter_range" />
        </v-col>

        <v-col cols="12" class="pt-1">
          <date-filter
            v-model="newsItemsFilter.timefrom"
            placeholder="From"
            :default-date="defaultFromDate"
          />
        </v-col>

        <v-col cols="12" class="pt-1">
          <date-filter
            v-model="newsItemsFilter.timeto"
            placeholder="Until"
            :default-date="new Date()"
            :max-date="
              newsItemsFilter.timefrom instanceof Date
                ? newsItemsFilter.timefrom
                : new Date()
            "
          />
        </v-col>
        <v-col cols="12" class="pt-1">
          <tag-filter v-model="newsItemsFilter.tags" />
        </v-col>
      </v-row>

      <v-row no-gutters>
        <v-col cols="12">
          <AssessFilterButtons />
        </v-col>
      </v-row>

      <v-divider class="my-2" />

      <v-row no-gutters class="ma-2 ml-0 px-2">
        <v-col cols="12" class="ml-2 py-1">
          <h4>Sort</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <filter-sort-list v-model="newsItemsFilter.sort" />
        </v-col>
      </v-row>

      <v-divider class="my-2" />

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
        <v-col cols="12" class="pt-0">
          <v-btn
            class="vertical-button toggle-button py-2 px-4 mb-1"
            :class="
              compactView ? 'toggle-button-checked' : 'toggle-button-unchecked'
            "
            value="compactView"
            prepend-icon="mdi-view-compact-outline"
            :append-icon="compactView ? 'mdi-check-bold' : undefined"
            :variant="compactView ? 'tonal' : 'text'"
            color="primary"
            @click="setCompactView"
          >
            compact view
          </v-btn>
        </v-col>
      </v-row>

      <v-divider class="my-2 mt-2 mb-0"></v-divider>
      <v-row no-gutters class="my-2 mr-0 px-2 pb-1">
        <v-col cols="12" class="py-2">
          <v-btn
            color="primary"
            prepend-icon="mdi-reload"
            block
            @click="resetFilter()"
          >
            reset filter
          </v-btn>
        </v-col>
        <v-col cols="12" class="py-2">
          <v-btn color="primary" block to="enter" prepend-icon="mdi-pencil">
            create new item
          </v-btn>
        </v-col>
      </v-row>
    </template>
  </filter-navigation>
</template>

<script>
import dateChips from '@/components/common/filter/dateChips.vue'
import dateFilter from '@/components/common/filter/dateFilter.vue'
import tagFilter from '@/components/common/filter/tagFilter.vue'
import filterButton from '@/components/common/filter/filterButton.vue'
import AssessFilterButtons from '@/components/assess/AssessFilterButtons.vue'
import filterSortList from '@/components/common/filter/filterSortList.vue'
import FilterNavigation from '@/components/common/FilterNavigation.vue'
import { computed, onUnmounted, onBeforeMount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useFilterStore } from '@/stores/FilterStore'
import { useAssessStore } from '@/stores/AssessStore'
import { storeToRefs } from 'pinia'
import { useDisplay } from 'vuetify'

export default {
  name: 'AssessNav',
  components: {
    dateChips,
    dateFilter,
    tagFilter,
    filterSortList,
    filterButton,
    FilterNavigation,
    AssessFilterButtons
  },
  setup() {
    const assessStore = useAssessStore()
    const filterStore = useFilterStore()

    const { getOSINTSourceGroupsList, getOSINTSourcesList } =
      storeToRefs(assessStore)
    const { updateNewsItems } = assessStore
    const { mdAndDown, smAndUp } = useDisplay()

    const {
      newsItemsFilter,
      chartFilter,
      highlight,
      showWeekChart,
      compactView,
      compactViewSetByUser
    } = storeToRefs(filterStore)

    const { setFilter, updateFilter } = useFilterStore()

    const route = useRoute()

    const filter_range = computed({
      get() {
        return undefined
      },
      set(value) {
        console.debug('filter_range', value)
        const now = new Date()
        switch (value) {
          case 'day': {
            now.setHours(0, 0, 0, 0) // Set to today at 00:00
            newsItemsFilter.value.timefrom = now.toISOString()
            break
          }
          case 'week': {
            const dayOfWeek = now.getDay()
            const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
            now.setDate(now.getDate() + diffToMonday)
            now.setHours(0, 0, 0, 0) // Set hours to 00:00
            newsItemsFilter.value.timefrom = now.toISOString()
            break
          }
          case '24h': {
            const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000)
            newsItemsFilter.value.timefrom = yesterday.toISOString()
            break
          }
        }
      }
    })

    const now = new Date()
    now.setDate(now.getDate() - 1)
    now.setHours(18, 0, 0, 0)
    const defaultFromDate = now

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
      filterStore.resetFilter()
    })

    const resetFilter = () => {
      assessStore.$reset()
      filterStore.resetFilter()
    }

    function setCompactView() {
      compactView.value = !compactView.value
      compactViewSetByUser.value = true
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
      mdAndDown,
      smAndUp,
      highlight,
      showWeekChart,
      compactView,
      filter_range,
      defaultFromDate,
      getOSINTSourceGroupsList,
      getOSINTSourcesList,
      newsItemsFilter,
      resetFilter,
      setCompactView
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
