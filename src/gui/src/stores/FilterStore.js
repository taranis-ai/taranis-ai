import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import { useAssessStore } from './AssessStore'
import { router } from '@/router'
import { getQueryStringFromNestedObject } from '@/utils/query'

export const useFilterStore = defineStore(
  'filter',
  () => {
    const storyFilter = ref({
      offset: undefined,
      limit: undefined,
      page: undefined,
      search: undefined,
      sort: undefined,
      range: undefined,
      timefrom: undefined,
      timeto: undefined,
      read: undefined,
      tags: undefined,
      group: undefined,
      source: undefined,
      in_report: undefined,
      relevant: undefined,
      important: undefined
    })

    const storyPage = ref(0)
    const filterQuery = ref(null)

    watch(
      storyFilter,
      (filter) => {
        const newFilterQuery = getQueryStringFromNestedObject(filter)

        if (newFilterQuery === filterQuery.value) {
          return
        }
        filterQuery.value = newFilterQuery
        router.push({ query: filter })
        const assessStore = useAssessStore()
        assessStore.updateStories()
      },
      { deep: true }
    )

    const assetFilter = ref({
      offset: undefined,
      limit: undefined,
      search: undefined,
      sort: undefined
    })

    const reportFilter = ref({
      offset: undefined,
      limit: undefined,
      search: undefined,
      sort: undefined,
      range: undefined,
      completed: undefined,
      incompleted: undefined
    })

    const productFilter = ref({
      offset: undefined,
      limit: undefined,
      search: undefined,
      sort: undefined,
      range: undefined
    })

    const highlight = ref(true)
    const showWeekChart = ref(false)
    const compactView = ref(false)
    const compactViewSetByUser = ref(false)

    // Getters
    const getFilterTags = computed(() => {
      if (typeof storyFilter.value.tags === 'string') {
        return [storyFilter.value.tags]
      }
      return storyFilter.value.tags
    })

    // Actions
    function setFilter(filter) {
      if (filter.tags && typeof filter.tags === 'string') {
        filter.tags = [filter.tags]
      }
      if (filter.offset && typeof filter.offset === 'string') {
        filter.offset = parseInt(filter.offset)
      }
      if (filter.limit && typeof filter.limit === 'string') {
        filter.limit = parseInt(filter.limit)
      }
      if (filter.page && typeof filter.page === 'string') {
        storyPage.value = parseInt(filter.page)
      }
      storyFilter.value = filter
    }

    function appendTag(tag) {
      if (storyFilter.value.tags) {
        if (typeof storyFilter.value.tags === 'string') {
          storyFilter.value.tags = [storyFilter.value.tags]
        }
        if (!storyFilter.value.tags.includes(tag)) {
          storyFilter.value.tags.push(tag)
        }
      } else {
        storyFilter.value.tags = [tag]
      }
    }

    function nextPage() {
      if (typeof storyPage.value === 'number') {
        storyPage.value += 1
      } else {
        storyPage.value = 2
      }
      return storyPage.value
    }

    function updateFilter(filter) {
      Object.keys(filter).forEach((element) => {
        if (element == 'tags' && typeof filter[element] === 'string') {
          storyFilter.value[element] = [filter[element]]
        } else {
          storyFilter.value[element] = filter[element]
        }
      })
    }

    function updateAssetFilter(filter) {
      Object.keys(filter).forEach((element) => {
        assetFilter.value[element] = filter[element]
      })
    }

    function updateReportFilter(filter) {
      Object.keys(filter).forEach((element) => {
        reportFilter.value[element] = filter[element]
      })
    }

    function setReportFilter(filter) {
      reportFilter.value = filter
    }

    function updateProductFilter(filter) {
      Object.keys(filter).forEach((element) => {
        productFilter.value[element] = filter[element]
      })
    }

    function setProductFilter(filter) {
      productFilter.value = filter
    }

    function setUserFilters(profile) {
      compactView.value = profile.compact_view
      showWeekChart.value = profile.show_charts
    }

    function resetFilter() {
      storyFilter.value = {
        offset: undefined,
        limit: undefined,
        search: undefined,
        page: undefined,
        sort: undefined,
        range: undefined,
        timefrom: undefined,
        timeto: undefined,
        read: undefined,
        tags: undefined,
        group: undefined,
        source: undefined,
        in_report: undefined,
        relevant: undefined,
        important: undefined
      }
      storyPage.value = 0
      assetFilter.value = {
        offset: undefined,
        limit: undefined,
        search: undefined,
        sort: undefined
      }
      reportFilter.value = {
        offset: undefined,
        limit: undefined,
        search: undefined,
        sort: undefined,
        range: undefined,
        completed: undefined,
        incompleted: undefined
      }
      productFilter.value = {
        offset: undefined,
        limit: undefined,
        search: undefined,
        sort: undefined,
        range: undefined
      }
    }

    // Return state, getters, and actions
    return {
      storyFilter,
      storyPage,
      filterQuery,
      assetFilter,
      reportFilter,
      productFilter,
      highlight,
      showWeekChart,
      compactView,
      compactViewSetByUser,
      getFilterTags,
      setFilter,
      appendTag,
      nextPage,
      updateFilter,
      updateAssetFilter,
      updateReportFilter,
      setReportFilter,
      updateProductFilter,
      setProductFilter,
      setUserFilters,
      resetFilter
    }
  },
  {
    persist: {
      paths: [
        'showWeekChart',
        'compactView',
        'compactViewSetByUser',
        'highlight'
      ]
    }
  }
)
