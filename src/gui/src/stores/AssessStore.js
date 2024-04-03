import {
  getStories,
  getOSINTSourceGroupsList,
  getOSINTSourcesList,
  readNewsItemAggregate,
  importantNewsItemAggregate,
  voteNewsItemAggregate,
  deleteNewsItemAggregate,
  updateStoryTags,
  getStory
} from '@/api/assess'
import { defineStore } from 'pinia'
import { xorConcat, notifyFailure, notifySuccess } from '@/utils/helpers'
import { useFilterStore } from './FilterStore'
import { stringify, parse } from 'zipson'
import { ref, computed } from 'vue'

export const useAssessStore = defineStore(
  'assess',
  () => {
    const osint_sources = ref({ total_count: 0, items: [] })
    const osint_source_groups = ref({ total_count: 0, items: [] })
    const stories = ref({ total_count: 0, items: [] })
    const newsItemSelection = ref([])
    const storySelection = ref([])
    const maxItem = ref(0)
    const loading = ref(false)
    const new_news_items = ref(false)

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
    async function updateNewsItems() {
      try {
        loading.value = true
        const filter = useFilterStore()
        const response = await getStories(filter.newsItemsFilter)
        stories.value.items = response.data.items
        stories.value.total_count = response.data.total_count
        maxItem.value = response.data.max_item
        loading.value = false
      } catch (error) {
        notifyFailure(error.message)
      }
    }
    async function modifyNewsItemsList(action = 'append') {
      try {
        loading.value = true
        // Make a copy of the original filter and adjust the offset based on the action
        const filter = { ...useFilterStore().newsItemsFilter }
        filter.offset = action === 'prepend' ? 0 : stories.value.items.length

        const response = await getStories(filter)
        const existingItemIds = new Set(
          stories.value.items.map((item) => item.id)
        )
        const uniqueNewItems = response.data.items.filter(
          (item) => !existingItemIds.has(item.id)
        )

        // Adjust the items array based on the action
        stories.value.items =
          action === 'append'
            ? [...stories.value.items, ...uniqueNewItems]
            : [...uniqueNewItems, ...stories.value.items]

        stories.value.total_count = response.data.total_count
        maxItem.value = response.data.max_item
        loading.value = false
      } catch (error) {
        console.error(error)
        notifyFailure(error.message)
      }
    }

    async function appendNewsItems() {
      await modifyNewsItemsList('append')
    }
    async function prependNewsItems() {
      await modifyNewsItemsList('prepend')
    }
    function removeStoryByID(id) {
      deleteNewsItemAggregate(id)
      stories.value.items = stories.value.items.filter(
        (item) => item.id !== id
      )
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
      maxItem.value = 0
      loading.value = false
      new_news_items.value = false
    }

    return {
      osint_sources,
      osint_source_groups,
      stories,
      newsItemSelection,
      storySelection,
      maxItem,
      loading,
      new_news_items,
      OSINTSourceGroupsList,
      OSINTSourcesList,
      activeSelection,
      reset,
      updateNewsItems,
      modifyNewsItemsList,
      appendNewsItems,
      prependNewsItems,
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
