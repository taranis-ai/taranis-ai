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
      <v-row no-gutters class="my-2 mr-0 px-2">
        <v-col cols="12" class="pb-0">
          <h4 class="text-center">Source</h4>
        </v-col>

        <v-col cols="12" class="pt-1">
          <v-select
            v-model="newsItemsFilter.group"
            :items="getOSINTSourceGroupsList"
            item-title="title"
            item-value="id"
            label="Source Group"
            :hide-details="true"
            variant="solo"
            clearable
            density="compact"
          ></v-select>
        </v-col>

        <v-col cols="12" class="pt-2">
          <v-select
            v-model="newsItemsFilter.source"
            :items="getOSINTSourcesList"
            item-title="title"
            item-value="id"
            label="Source"
            :hide-details="true"
            variant="solo"
            clearable
            density="compact"
          ></v-select>
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <v-row no-gutters class="my-2 mr-0 px-2">
        <v-col cols="12" class="py-0">
          <h4 class="text-center">Filter</h4>
        </v-col>

        <v-col cols="12" class="pt-1">
          <date-chips v-model="newsItemsFilter.range" />
        </v-col>

        <v-col cols="12" class="pt-1">
          <tag-filter v-model="newsItemsFilter.tags" />
        </v-col>
      </v-row>

      <v-divider class="mt-0 mb-0"></v-divider>

      <v-row no-gutters class="my-2 mr-0 px-2">
        <v-col cols="12" class="pt-1">
          <filter-select-list
            v-model="filterAttribute"
            :filter-attribute-options="filterAttributeOptions"
          />
        </v-col>
      </v-row>
      <v-divider class="mt-0 mb-0"></v-divider>

      <v-row no-gutters class="my-2 mr-0 px-2">
        <v-col cols="12" class="py-0">
          <h4 class="text-center">Sort</h4>
        </v-col>

        <v-col cols="12" class="pt-2">
          <filter-sort-list v-model="newsItemsFilter.sort" />
        </v-col>
      </v-row>

      <v-divider class="mt-1 mb-0"></v-divider>
      <v-row no-gutters class="my-2 mr-0 px-2">
        <v-col cols="12" class="py-0">
          <h4 class="text-center">Debug</h4>
        </v-col>
        <v-col cols="8" class="pt-2">chart threshold:</v-col>
        <v-col cols="4" class="pt-2">
          <input v-model="chartFilter.threshold" type="number" min="0"
        /></v-col>
        <v-col cols="8" class="pt-2">chart y2 Max:</v-col>
        <v-col cols="4" class="pt-2">
          <input v-model="chartFilter.y2max" type="number" min="0" />
        </v-col>
      </v-row>

      <v-divider class="mt-2 mb-0"></v-divider>
      <v-row no-gutters class="my-2 mr-0 px-2 pb-5">
        <v-col cols="12" class="py-2">
          <v-btn color="primary" block @click="resetFilter()">
            Reset Filter
            <v-icon right dark> mdi-reload </v-icon>
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
    const { newsItemsFilter, chartFilter } = storeToRefs(filterStore)

    const { setFilter, updateFilter } = useFilterStore()

    const route = useRoute()

    const filterAttributeOptions = [
      { value: 'read', label: 'read', icon: 'mdi-email-mark-as-unread' },
      {
        value: 'important',
        label: 'important',
        icon: 'mdi-exclamation'
      },
      {
        value: 'in_report',
        label: 'items in reports',
        icon: 'mdi-share-outline'
      },
      {
        value: 'relevant',
        label: 'relevant',
        icon: 'mdi-bullhorn-outline'
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
      updateQuery()
    })

    onUnmounted(() => {
      setFilter({})
    })

    const resetFilter = () => {
      filterStore.$reset()
      updateNewsItems()
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
      getOSINTSourceGroupsList,
      getOSINTSourcesList,
      newsItemsFilter,
      filterAttribute,
      filterAttributeOptions,
      updateNewsItems,
      resetFilter
    }
  }
}
</script>
