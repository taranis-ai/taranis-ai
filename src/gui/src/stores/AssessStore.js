import {
  getStories,
  getOSINTSourceGroupsList,
  getOSINTSourcesList,
  readStory,
  importantStory,
  voteStory,
  deleteStory,
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
import { useMainStore } from '@/stores/MainStore'

export const useAssessStore = defineStore(
  'assess',
  () => {
    const osint_sources = ref({ total_count: 0, items: [] })
    const osint_source_groups = ref({ total_count: 0, items: [] })
    const stories = ref({ items: [] })
    const storyCounts = ref({
      total_count: 0,
      read_count: 0,
      important_count: 0,
      in_reports_count: 0
    })
    const newsItemSelection = ref([])
    const storySelection = ref([])
    const loading = ref(false)
    const new_stories = ref(false)
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
        const storyFilter = useFilterStore().storyFilterQuery || ''
        console.debug('Updating Stories with Filter', storyFilter)
        const response = await getStories(storyFilter)
        stories.value.items = response.data.items
        if (response.data.counts) {
          storyCounts.value = response.data.counts
          weekChartOptions.value.scales.y2.max =
            response.data.counts.biggest_story
        }

        loading.value = false
      } catch (error) {
        loading.value = false
        stories.value = { items: [] }
        notifyFailure(error.message)
      }
    }
    async function appendStories() {
      try {
        loading.value = true
        const filter = useFilterStore()
        const mainStore = useMainStore()

        const page = filter.nextPage()

        let { storyFilterQuery } = filter
        if (!storyFilterQuery || storyFilterQuery === '') {
          storyFilterQuery += `page=${page}&no_count=true`
        } else if (storyFilterQuery.includes('page')) {
          storyFilterQuery = storyFilterQuery.replace(
            /page=\d+/,
            `page=${page}`
          )
          storyFilterQuery += '&no_count=true'
        } else {
          storyFilterQuery += `&page=${page}&no_count=true`
        }

        const response = await getStories(storyFilterQuery)
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
        mainStore.setItemCount(
          storyCounts.value.total_count,
          stories.value.items.length
        )
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
      deleteStory(id)
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
    async function voteOnStory(id, vote) {
      try {
        await voteStory(id, vote)
        updateVote(id, vote)
      } catch (error) {
        notifyFailure(error)
      }
    }

    function updateVote(id, vote) {
      const story = stories.value.items.find((item) => item.id === id)

      if (vote === 'like') {
        if (story.user_vote === 'like') {
          story.likes -= 1
          story.relevance -= 1
          story.user_vote = ''
        } else if (story.user_vote === 'dislike') {
          story.dislikes -= 1
          story.likes += 1
          story.relevance += 2
          story.user_vote = 'like'
        } else {
          story.likes += 1
          story.relevance += 1
          story.user_vote = 'like'
        }
      }
      if (vote === 'dislike') {
        if (story.user_vote === 'dislike') {
          story.dislikes -= 1
          story.relevance += 1
          story.user_vote = ''
        } else if (story.user_vote === 'like') {
          story.likes -= 1
          story.dislikes += 1
          story.relevance -= 2
          story.user_vote = 'dislike'
        } else {
          story.dislikes += 1
          story.relevance -= 1
          story.user_vote = 'dislike'
        }
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
      const response = await getOSINTSourcesList()
      osint_sources.value = response.data
    }
    async function updateOSINTSourceGroupsList() {
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
      storySelection.value.forEach((id) => {
        markStoryAsRead(id)
      })
      clearStorySelection()
    }
    function markSelectionAsImportant() {
      storySelection.value.forEach((id) => {
        markStoryAsImportant(id)
      })
      clearStorySelection()
    }
    function sseNewsItemsUpdated() {
      console.debug('Triggerd News items update')
      new_stories.value = true
    }
    function markStoryAsRead(id) {
      const item = stories.value.items.find((item) => item.id === id)
      item.read = !item.read
      filterStories()
      readStory(id, item.read)
    }

    function markStoryAsImportant(id) {
      const item = stories.value.items.find((item) => item.id === id)
      item.important = !item.important
      filterStories()
      importantStory(id, item.important)
    }

    function filterStories() {
      const filter = useFilterStore()
      const { storyFilter } = filter
      stories.value.items = stories.value.items.filter((item) => {
        if (
          (storyFilter.read === 'true' && !item.read) ||
          (storyFilter.read === 'false' && item.read)
        ) {
          return false
        }
        if (
          (storyFilter.important === 'true' && !item.important) ||
          (storyFilter.important === 'false' && item.important)
        ) {
          return false
        }
        return true
      })
      if (
        stories.value.items.length === 0 &&
        storyCounts.value.total_count > 0
      ) {
        updateStories()
      }
    }

    function reset() {
      osint_sources.value = { total_count: 0, items: [] }
      osint_source_groups.value = { total_count: 0, items: [] }
      stories.value = { items: [] }
      storyCounts.value = {
        total_count: 0,
        read_count: 0,
        important_count: 0,
        in_reports_count: 0
      }
      newsItemSelection.value = []
      storySelection.value = []
      weekChartOptions.value = staticWeekChartOptions
      loading.value = false
      new_stories.value = false
    }

    return {
      osint_sources,
      osint_source_groups,
      storyCounts,
      stories,
      newsItemSelection,
      storySelection,
      weekChartOptions,
      loading,
      new_stories,
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
      voteOnStory,
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
      paths: ['osint_sources', 'osint_source_groups', 'stories', 'storyCounts'],
      serializer: {
        deserialize: (value) => parse(value),
        serialize: (value) => stringify(value)
      }
    }
  }
)
