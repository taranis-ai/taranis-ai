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

export const useAssessStore = defineStore('assess', {
  state: () => ({
    osint_sources: { total_count: 0, items: [] },
    osint_source_groups: { total_count: 0, items: [] },
    newsItems: { total_count: 0, items: [] },
    newsItemSelection: [],
    storySelection: [],
    max_item: 0,
    loading: false,
    new_news_items: false
  }),
  getters: {
    getOSINTSourceGroupsList() {
      return Array.isArray(this.osint_source_groups.items)
        ? this.osint_source_groups.items.map((value) => ({
            id: value.id,
            title: value.name
          }))
        : []
    },
    getOSINTSourcesList() {
      return Array.isArray(this.osint_sources.items)
        ? this.osint_sources.items.map((value) => ({
            id: value.id,
            title: value.name
          }))
        : []
    },
    activeSelection() {
      return this.newsItemSelection.length > 0 || this.storySelection.length > 0
    }
  },
  actions: {
    async updateNewsItems() {
      try {
        this.loading = true
        const filter = useFilterStore()
        const response = await getStories(filter.newsItemsFilter)
        this.newsItems.items = response.data.items
        this.newsItems.total_count = response.data.total_count
        this.max_item = response.data.max_item
        this.loading = false
      } catch (error) {
        notifyFailure(error.message)
      }
    },
    async modifyNewsItemsList(action = 'append') {
      try {
        this.loading = true
        // Make a copy of the original filter and adjust the offset based on the action
        const filter = { ...useFilterStore().newsItemsFilter }
        filter.offset = action === 'prepend' ? 0 : this.newsItems.items.length

        const response = await getStories(filter)
        const existingItemIds = new Set(
          this.newsItems.items.map((item) => item.id)
        )
        const uniqueNewItems = response.data.items.filter(
          (item) => !existingItemIds.has(item.id)
        )

        // Adjust the items array based on the action
        this.newsItems.items =
          action === 'append'
            ? [...this.newsItems.items, ...uniqueNewItems]
            : [...uniqueNewItems, ...this.newsItems.items]

        this.newsItems.total_count = response.data.total_count
        this.max_item = response.data.max_item
        this.loading = false
      } catch (error) {
        console.error(error)
        notifyFailure(error.message)
      }
    },

    async appendNewsItems() {
      await this.modifyNewsItemsList('append')
    },
    async prependNewsItems() {
      await this.modifyNewsItemsList('prepend')
    },

    removeStoryByID(id) {
      deleteNewsItemAggregate(id)
      this.newsItems.items = this.newsItems.items.filter(
        (item) => item.id !== id
      )
    },
    async updateStoryByID(id) {
      const response = await getStory(id)
      const updated_item = response.data
      let found = false

      this.newsItems.items = this.newsItems.items.map((item) => {
        if (item.id === id) {
          found = true
          return { ...item, ...updated_item }
        }
        return item
      })

      if (!found) {
        this.newsItems.items.push(updated_item)
      }
    },
    async voteOnNewsItemAggregate(id, vote) {
      try {
        await voteNewsItemAggregate(id, vote)
      } catch (error) {
        notifyFailure(error)
      }
    },
    async updateTags(id, tags) {
      try {
        const result = await updateStoryTags(id, tags)
        this.updateStoryByID(id)
        notifySuccess(result)
      } catch (error) {
        notifyFailure(error)
      }
    },
    async updateOSINTSources() {
      if (this.osint_sources.items.length > 0) {
        return
      }
      const response = await getOSINTSourcesList()
      this.osint_sources = response.data
    },
    async updateOSINTSourceGroupsList() {
      if (this.osint_source_groups.items.length > 0) {
        return
      }
      const response = await getOSINTSourceGroupsList()
      this.osint_source_groups = response.data
    },
    selectNewsItem(id) {
      this.newsItemSelection = xorConcat(this.newsItemSelection, id)
    },
    clearSelection() {
      this.newsItemSelection = []
      this.storySelection = []
    },
    clearNewsItemSelection() {
      this.newsItemSelection = []
    },
    selectStory(id) {
      this.storySelection = xorConcat(this.storySelection, id)
    },
    storyAddedToReport(story_id) {
      const item = this.newsItems.items.find((item) => item.id === story_id)
      item.in_reports_count += 1
    },
    selectAllItems() {
      this.storySelection = this.newsItems.items.map((item) => item.id)
    },
    clearStorySelection() {
      this.storySelection = []
    },
    markSelectionAsRead() {
      console.debug('Mark as Read: ', this.storySelection)

      this.storySelection.forEach((id) => {
        this.readNewsItemAggregate(id)
      })
    },
    markSelectionAsImportant() {
      this.storySelection.forEach((id) => {
        this.importantNewsItemAggregate(id)
      })
    },
    sseNewsItemsUpdated() {
      console.debug('Triggerd News items update')
      this.new_news_items = true
    },
    readNewsItemAggregate(id) {
      const item = this.newsItems.items.find((item) => item.id === id)
      item.read = !item.read
      readNewsItemAggregate(id, item.read)
    },

    importantNewsItemAggregate(id) {
      const item = this.newsItems.items.find((item) => item.id === id)
      item.important = !item.important
      importantNewsItemAggregate(id, item.important)
    }
  },
  persist: {
    paths: ['osint_sources', 'osint_source_groups']
  }
})
