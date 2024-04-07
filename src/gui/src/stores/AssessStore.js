import {
  getStories,
  getOSINTSourceGroupsList,
  getOSINTSourcesList,
  readNewsItemAggregate,
  importantNewsItemAggregate,
  voteNewsItemAggregate,
  deleteNewsItemAggregate,
  updateStoryTags,
  groupAction,
  unGroupAction,
  getStory
} from '@/api/assess'
import { defineStore } from 'pinia'
import { xorConcat, notifyFailure, notifySuccess } from '@/utils/helpers'
import { useFilterStore } from './FilterStore'
import { stringify, parse } from 'zipson'
import { ref, computed } from 'vue'
import { staticWeekChartOptions } from '@/utils/helpers'

export const useAssessStore = defineStore(
  'assess',
  () => {
    const osint_sources = ref({ total_count: 0, items: [] })
    const osint_source_groups = ref({ total_count: 0, items: [] })
    const stories = ref({ total_count: 0, items: [] })
    const newsItemSelection = ref([])
    const storySelection = ref([])
    const loading = ref(false)
    const new_news_items = ref(false)
    const weekChartOptions = ref(staticWeekChartOptions)

    const OSINTSourceGroupsList = computed(() =>
      Array.isArray(osint_source_groups.value.items)
        ? osint_source_groups.value.items.map((value) => ({
            id: value.id,
            title: value.name
          }))
        : []
    )

    const OSINTSourcesList = computed(() =>
      Array.isArray(osint_sources.value.items)
        ? osint_sources.value.items.map((value) => ({
            id: value.id,
            title: value.name
          }))
        : []
    )

    const activeSelection = computed(
      () =>
        newsItemSelection.value.length > 0 || storySelection.value.length > 0
    )

    async function updateStories() {
      try {
        loading.value = true
        const filter = useFilterStore()
        console.debug('Updating Stories with Filter', filter.filterQuery)
        const response = await getStories(filter.filterQuery)
        stories.value.items = response.data.items
        stories.value.total_count = response.data.total_count
        weekChartOptions.value.scales.y2.max = response.data.max_item
        loading.value = false
      } catch (error) {
        loading.value = false
        notifyFailure(error.message)
      }
    }
    async function appendStories() {
      try {
        loading.value = true
        const filter = useFilterStore()

        const page = filter.nextPage()

        let { filterQuery } = filter
        if (filterQuery === '') {
          filterQuery += `page=${page}&no_count=true`
        } else if (filterQuery.includes('page')) {
          filterQuery = filterQuery.replace(/page=\d+/, `page=${page}`)
          filterQuery += '&no_count=true'
        } else {
          filterQuery += `&page=${page}&no_count=true`
        }

        const response = await getStories(filterQuery)
        const existingItemIds = new Set(
          stories.value.items.map((item) => item.id)
        )
        const uniqueNewItems = response.data.items.filter(
          (item) => !existingItemIds.has(item.id)
        )
        if (uniqueNewItems.length === 0) {
          notifySuccess('No more stories to load')
          loading.value = false
          return false
        }

        stories.value.items = [...stories.value.items, ...uniqueNewItems]

        weekChartOptions.value.scales.y2.max = response.data.max_item
        loading.value = false
        return true
      } catch (error) {
        loading.value = false
        console.error(error)
        notifyFailure(error.message)
      }
    }

    function getStoryByID(id) {
      return stories.value.items.filter((item) => item.id === id)[0]
    }
    function removeStoryByID(id) {
      deleteNewsItemAggregate(id)
      stories.value.items = stories.value.items.filter((item) => item.id !== id)
    }
    async function updateStoryByID(id) {
      const response = await getStory(id)
      const updated_item = response.data
      let found = false

      stories.value.items = stories.value.items.map((item) => {
        if (item.id === id) {
          found = true
          return { ...item, ...updated_item }
        }
        return item
      })

      if (!found) {
        stories.value.items.push(updated_item)
      }
    }
    async function voteOnNewsItemAggregate(id, vote) {
      try {
        await voteNewsItemAggregate(id, vote)
      } catch (error) {
        notifyFailure(error)
      }
    }
    async function updateTags(id, tags) {
      try {
        const result = await updateStoryTags(id, tags)
        updateStoryByID(id)
        notifySuccess(result)
      } catch (error) {
        notifyFailure(error)
      }
    }
    async function updateOSINTSources() {
      if (osint_sources.value.items.length > 0) {
        return
      }
      const response = await getOSINTSourcesList()
      osint_sources.value = response.data
    }
    async function updateOSINTSourceGroupsList() {
      if (osint_source_groups.value.items.length > 0) {
        return
      }
      const response = await getOSINTSourceGroupsList()
      osint_source_groups.value = response.data
    }

    async function ungroupStories(stories = storySelection.value) {
      try {
        if (stories.length < 1) {
          notifyFailure('Select at least 1 story to ungroup')
          return
        }
        await unGroupAction(stories)
        clearSelection()
        await updateStories()
      } catch (error) {
        notifyFailure(error)
      }
    }

    function groupStories() {
      try {
        if (storySelection.value.length < 2) {
          notifyFailure('Select at least 2 stories to group')
          return
        }
        groupAction(storySelection.value)
        // Take all the elements from stories.value where the id matches the storySelection.value except the first one and remove them from stories.value, and add them to the first one
        const firstID = storySelection.value.shift()
        const firstStory = stories.value.items.find(
          (item) => item.id === firstID
        )
        const storiesToMerge = stories.value.items.filter((item) =>
          storySelection.value.includes(item.id)
        )
        firstStory.news_items = [
          ...firstStory.news_items,
          ...storiesToMerge.map((item) => item.news_items).flat()
        ]
        firstStory.news_items = firstStory.news_items.sort(
          (a, b) => new Date(b.published_at) - new Date(a.published_at)
        )
        stories.value.items = stories.value.items.filter(
          (item) => !storySelection.value.includes(item.id)
        )

        notifySuccess(`Merged stories: ${storySelection.value.join(', ')}`)
        clearSelection()
      } catch (error) {
        console.error(error)
        notifyFailure(error)
      }
    }

    function selectNewsItem(id) {
      newsItemSelection.value = xorConcat(newsItemSelection.value, id)
    }
    function clearSelection() {
      newsItemSelection.value = []
      storySelection.value = []
    }
    function clearNewsItemSelection() {
      newsItemSelection.value = []
    }
    function selectStory(id) {
      storySelection.value = xorConcat(storySelection.value, id)
    }
    function storyAddedToReport(story_id) {
      const item = stories.value.items.find((item) => item.id === story_id)
      item.in_reports_count += 1
    }
    function selectAllItems() {
      storySelection.value = stories.value.items.map((item) => item.id)
    }
    function clearStorySelection() {
      storySelection.value = []
    }
    function markSelectionAsRead() {
      console.debug('Mark as Read: ', storySelection.value)

      storySelection.value.forEach((id) => {
        markStoryAsRead(id)
      })
    }
    function markSelectionAsImportant() {
      storySelection.value.forEach((id) => {
        markStoryAsImportant(id)
      })
    }
    function sseNewsItemsUpdated() {
      console.debug('Triggerd News items update')
      new_news_items.value = true
    }
    function markStoryAsRead(id) {
      const item = stories.value.items.find((item) => item.id === id)
      item.read = !item.read
      readNewsItemAggregate(id, item.read)
    }

    function markStoryAsImportant(id) {
      const item = stories.value.items.find((item) => item.id === id)
      item.important = !item.important
      importantNewsItemAggregate(id, item.important)
    }

    function reset() {
      osint_sources.value = { total_count: 0, items: [] }
      osint_source_groups.value = { total_count: 0, items: [] }
      stories.value = { total_count: 0, items: [] }
      newsItemSelection.value = []
      storySelection.value = []
      weekChartOptions.value = staticWeekChartOptions
      loading.value = false
      new_news_items.value = false
    }

    return {
      osint_sources,
      osint_source_groups,
      stories,
      newsItemSelection,
      storySelection,
      weekChartOptions,
      loading,
      new_news_items,
      OSINTSourceGroupsList,
      OSINTSourcesList,
      activeSelection,
      reset,
      updateStories,
      groupStories,
      ungroupStories,
      appendStories,
      getStoryByID,
      removeStoryByID,
      updateStoryByID,
      voteOnNewsItemAggregate,
      updateTags,
      updateOSINTSources,
      updateOSINTSourceGroupsList,
      selectNewsItem,
      clearSelection,
      clearNewsItemSelection,
      selectStory,
      storyAddedToReport,
      selectAllItems,
      clearStorySelection,
      markSelectionAsRead,
      markSelectionAsImportant,
      sseNewsItemsUpdated,
      markStoryAsRead,
      markStoryAsImportant
    }
  },
  {
    persist: {
      paths: ['osint_sources', 'osint_source_groups', 'stories'],
      serializer: {
        deserialize: (value) => parse(value),
        serialize: (value) => stringify(value)
      }
    }
  }
)
