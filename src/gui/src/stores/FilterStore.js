import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import { useAssessStore } from './AssessStore'
import { router } from '@/router'
import { getQueryStringFromNestedObject } from '@/utils/query'

export const useFilterStore = defineStore(
  'filter',
  () => {
    const newsItemsFilter = ref({
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

    const filterQuery = ref(null)

    watch(
      newsItemsFilter,
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
      if (typeof newsItemsFilter.value.tags === 'string') {
        return [newsItemsFilter.value.tags]
      }
      return newsItemsFilter.value.tags
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
      newsItemsFilter.value = filter
    }

    function appendTag(tag) {
      if (newsItemsFilter.value.tags) {
        if (typeof newsItemsFilter.value.tags === 'string') {
          newsItemsFilter.value.tags = [newsItemsFilter.value.tags]
        }
        if (!newsItemsFilter.value.tags.includes(tag)) {
          newsItemsFilter.value.tags.push(tag)
        }
      } else {
        newsItemsFilter.value.tags = [tag]
      }
    }

    function nextPage() {
      const offset = newsItemsFilter.value.offset || 0
      const limit = newsItemsFilter.value.limit || 20

      newsItemsFilter.value.offset = offset + limit
    }

    function updateFilter(filter) {
      Object.keys(filter).forEach((element) => {
        if (element == 'tags' && typeof filter[element] === 'string') {
          newsItemsFilter.value[element] = [filter[element]]
        } else {
          newsItemsFilter.value[element] = filter[element]
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
      newsItemsFilter.value = {
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
      }
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
      newsItemsFilter,
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
