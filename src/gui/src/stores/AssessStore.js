import {
  getNewsItemsAggregates,
  getNewsItemAggregate,
  getOSINTSourceGroupsList,
  getOSINTSourcesList,
  readNewsItemAggregate,
  importantNewsItemAggregate,
  voteNewsItemAggregate,
  deleteNewsItemAggregate
} from '@/api/assess'
import { defineStore } from 'pinia'
import { xorConcat, notifyFailure, getMessageFromError } from '@/utils/helpers'

import { useFilterStore } from './FilterStore'

export const useAssessStore = defineStore('assess', {
  state: () => ({
    selection: [],
    osint_sources: { total_count: 0, items: [] },
    osint_source_groups: { total_count: 0, items: [] },
    newsItems: { total_count: 0, items: [] },
    newsItemsSelection: [],
    max_item: 0,
    loading: false
  }),
  getters: {
    getSelection() {
      return this.selection
    },
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
    }
  },
  actions: {
    async updateNewsItems() {
      console.debug('updateNewsItems')
      try {
        const filter = useFilterStore()
        const response = await getNewsItemsAggregates(filter.newsItemsFilter)
        this.newsItems.items = response.data.items
        this.newsItems.total_count = response.data.total_count
        this.max_item = response.data.max_item
      } catch (error) {
        notifyFailure(error.message)
      }
    },
    async appendNewsItems() {
      console.debug('appendNewsItems')
      try {
        this.loading = true
        // filter should be a copy of the original filter
        const filter = { ...useFilterStore().newsItemsFilter }
        filter.offset = this.newsItems.items.length
        const response = await getNewsItemsAggregates(filter)
        const existingItemIds = new Set(
          this.newsItems.items.map((item) => item.id)
        )
        const uniqueNewItems = response.data.items.filter(
          (item) => !existingItemIds.has(item.id)
        )

        this.newsItems.items = [...this.newsItems.items, ...uniqueNewItems]
        this.newsItems.total_count = response.data.total_count
        this.max_item = response.data.max_item
        this.loading = false
      } catch (error) {
        console.error(error)
        notifyFailure(error.message)
      }
    },
    removeNewsItemByID(id) {
      deleteNewsItemAggregate(id)
      this.newsItems.items = this.newsItems.items.filter(
        (item) => item.id !== id
      )
    },
    async updateNewsItemByID(id) {
      const response = await getNewsItemAggregate(id)
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
        console.debug('append updateNewsItemByID')
        this.newsItems.items.push(updated_item)
      }
      console.debug('updateNewsItemByID', updated_item)
    },
    async voteOnNewsItemAggregate(id, vote) {
      try {
        this.newsItems.items = this.newsItems.items.map((item) => {
          if (item.id === id) {
            let { likes, dislikes, relevance } = item
            let voted = { ...item.user_vote }

            if (vote === 'like') {
              if (voted.like) {
                likes -= 1
                relevance -= 1
                voted.like = false
              } else if (voted.dislike) {
                dislikes -= 1
                likes += 1
                relevance += 2
                voted = { like: true, dislike: false }
              } else {
                likes += 1
                relevance += 1
                voted.like = true
              }
            }
            if (vote === 'dislike') {
              if (voted.dislike) {
                dislikes -= 1
                relevance += 1
                voted.dislike = false
              } else if (voted.like) {
                likes -= 1
                dislikes += 1
                relevance -= 2
                voted = { like: false, dislike: true }
              } else {
                dislikes += 1
                relevance -= 1
                voted.dislike = true
              }
            }

            return {
              ...item,
              user_vote: voted,
              relevance: relevance,
              likes: likes,
              dislikes: dislikes
            }
          }
          return item
        })

        await voteNewsItemAggregate(id, vote)
        this.updateNewsItemByID(id)
      } catch (error) {
        notifyFailure(getMessageFromError(error))
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
      this.newsItemsSelection = xorConcat(this.newsItemsSelection, id)
    },
    clearNewsItemSelection() {
      this.newsItemsSelection = []
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
    },

    select(data) {
      this.selection.push(data)
    },

    deselect(data) {
      for (let i = 0; i < this.selection.length; i++) {
        if (
          this.selection[i].type === data.type &&
          this.selection[i].id === data.id
        ) {
          this.selection.splice(i, 1)
          break
        }
      }
    }
  },
  persist: {
    paths: ['osint_sources', 'osint_source_groups']
  }
})
