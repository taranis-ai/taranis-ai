import {
  getNewsItemsAggregates,
  getOSINTSourceGroupsList,
  getOSINTSourcesList
} from '@/api/assess'
import { defineStore } from 'pinia'
import { xorConcat, notifyFailure } from '@/utils/helpers'

import { useFilterStore } from './FilterStore'

export const useAssessStore = defineStore('assess', {
  state: () => ({
    multi_select: false,
    selection: [],
    osint_sources: [],
    osint_source_groups: [],
    default_source_group_id: '',
    newsItems: { total_count: 0, items: [] },
    newsItemsSelection: [],
    top_stories: [],
    max_item: null
  }),
  getters: {
    getMultiSelect() {
      return this.multi_select
    },
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
      try {
        const filter = useFilterStore()
        const response = await getNewsItemsAggregates(filter.newsItemsFilter)
        this.newsItems = response.data
        // this.updateMaxItem()
      } catch (error) {
        notifyFailure(error.message)
      }
    },
    async updateOSINTSources() {
      const response = await getOSINTSourcesList()
      this.osint_sources = response.data
    },
    async updateOSINTSourceGroupsList() {
      const response = await getOSINTSourceGroupsList()
      this.osint_source_groups = response.data
      this.default_source_group_id = response.data.items.filter(
        (value) => value.default
      )[0].id
    },
    updateMaxItem() {
      const countsArray = this.newsItems.items.map((item) =>
        Math.max(
          ...Object.values(
            item.news_items.reduce((acc, item) => {
              const day = new Date(
                item.news_item_data.published
              ).toLocaleDateString(undefined, {
                day: '2-digit',
                month: '2-digit'
              })
              acc[day] = (acc[day] || 0) + 1
              return acc
            }, {})
          )
        )
      )
      this.max_item = Math.max(...countsArray)
    },
    selectNewsItem(id) {
      this.newsItemsSelection = xorConcat(this.newsItemsSelection, id)
    },
    clearNewsItemSelection() {
      this.newsItemsSelection = []
    },

    multiSelect(data) {
      this.multi_select = data
      this.selection = []
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
  }
})
