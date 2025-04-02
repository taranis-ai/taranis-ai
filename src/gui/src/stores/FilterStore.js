import { ref, computed, watch } from 'vue'
import { defineStore } from 'pinia'
import { useAssessStore } from './AssessStore'
import { useAnalyzeStore } from './AnalyzeStore'
import { usePublishStore } from './PublishStore'
import { useUserStore } from './UserStore'
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
      important: undefined,
      cybersecurity: undefined
    })

    const storyPage = ref(0)
    const storyFilterQuery = ref('')
    const reportFilterQuery = ref('')
    const productFilterQuery = ref('')

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
      completed: undefined
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

    watch(
      storyFilter,
      (filter) => {
        storyPage.value = 0
        const newFilterQuery = getQueryStringFromNestedObject(filter)
        console.debug(
          `newFilterQuery: ${newFilterQuery} - created from filter: ${JSON.stringify(filter)}`
        )

        if (newFilterQuery === storyFilterQuery.value) {
          return
        }
        storyFilterQuery.value = newFilterQuery
        router.push({ query: filter })
        const assessStore = useAssessStore()
        assessStore.updateStories()
      },
      { deep: true }
    )

    watch(
      reportFilter,
      (filter) => {
        const newFilterQuery = getQueryStringFromNestedObject(filter)

        if (newFilterQuery === reportFilterQuery.value) {
          return
        }
        reportFilterQuery.value = newFilterQuery
        router.push({ query: filter })
        const analyzeStore = useAnalyzeStore()
        analyzeStore.updateReportItems()
      },
      { deep: true }
    )

    watch(
      productFilter,
      (filter) => {
        const newFilterQuery = getQueryStringFromNestedObject(filter)

        if (newFilterQuery === productFilterQuery.value) {
          return
        }
        productFilterQuery.value = newFilterQuery
        router.push({ query: filter })
        const productStore = usePublishStore()
        productStore.updateProducts()
      },
      { deep: true }
    )

    // Getters
    const getFilterTags = computed(() => {
      if (typeof storyFilter.value.tags === 'string') {
        return [storyFilter.value.tags]
      }
      return storyFilter.value.tags
    })

    const infiniteScroll = computed(() => {
      if (storyFilter.value.timeto) {
        return false
      }
      return useUserStore().infinite_scroll
    })

    // Actions

    function parseFilter(filter) {
      if (filter.tags && typeof filter.tags === 'string') {
        filter.tags = [filter.tags]
      }
      if (filter.offset && typeof filter.offset === 'string') {
        filter.offset = parseInt(filter.offset)
      }
      if (filter.limit && typeof filter.limit === 'string') {
        filter.limit = parseInt(filter.limit)
      }
      return filter
    }

    function setStoryFilter(rawFilter) {
      const filter = parseFilter(rawFilter)
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
      reportFilter.value = parseFilter(filter)
    }

    function updateProductFilter(filter) {
      Object.keys(filter).forEach((element) => {
        productFilter.value[element] = filter[element]
      })
    }

    function setProductFilter(filter) {
      productFilter.value = parseFilter(filter)
    }

    function setUserFilters(profile) {
      compactView.value = profile.compact_view
      showWeekChart.value = profile.show_charts
    }

    function setFilter(filter, type) {
      if (type === 'assess') {
        setStoryFilter(filter)
      } else if (type === 'asset') {
        updateAssetFilter(filter)
      } else if (type === 'analyze') {
        updateReportFilter(filter)
      } else if (type === 'publish') {
        updateProductFilter(filter)
      }
    }

    function getFilter(type) {
      if (type === 'assess') {
        return storyFilter.value
      } else if (type === 'asset') {
        return assetFilter.value
      } else if (type === 'analyze') {
        return reportFilter.value
      } else if (type === 'publish') {
        return productFilter.value
      }
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
        important: undefined,
        cybersecurity: undefined
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
        completed: undefined
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
      storyFilterQuery,
      reportFilterQuery,
      productFilterQuery,
      assetFilter,
      reportFilter,
      productFilter,
      highlight,
      showWeekChart,
      compactView,
      compactViewSetByUser,
      getFilterTags,
      infiniteScroll,
      setFilter,
      getFilter,
      setStoryFilter,
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
