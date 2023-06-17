import { defineStore } from 'pinia'

export const useFilterStore = defineStore('filter', {
  state: () => ({
    newsItemsFilter: {
      offset: undefined,
      limit: undefined,
      search: undefined,
      sort: undefined,
      range: undefined,
      read: undefined,
      tags: undefined,
      group: undefined,
      source: undefined,
      in_report: undefined,
      relevant: undefined,
      important: undefined
    },
    assetFilter: {
      offset: undefined,
      limit: undefined,
      search: undefined,
      sort: undefined
    },
    reportFilter: {
      offset: undefined,
      limit: undefined,
      search: undefined,
      sort: undefined,
      range: undefined,
      completed: undefined,
      incompleted: undefined
    },
    productFilter: {
      offset: undefined,
      limit: undefined,
      search: undefined,
      sort: undefined,
      range: undefined
    },
    chartFilter: {
      threshold: 20,
      y2max: undefined
    }
  }),
  getters: {
    getFilterTags() {
      if (typeof this.newsItemsFilter.tags === 'string') {
        return [this.newsItemsFilter.tags]
      }
      return this.newsItemsFilter.tags
    }
  },
  actions: {
    setFilter(filter) {
      this.newsItemsFilter = filter
    },
    appendTag(tag) {
      if (this.newsItemsFilter.tags) {
        if (typeof this.newsItemsFilter.tags === 'string') {
          this.newsItemsFilter.tags = [this.newsItemsFilter.tags]
        }
        if (!this.newsItemsFilter.tags.includes(tag)) {
          this.newsItemsFilter.tags.push(tag)
        }
      } else {
        this.newsItemsFilter.tags = [tag]
      }
    },
    displayMore() {
      const limit = this.newsItemsFilter.limit
        ? parseInt(this.newsItemsFilter.limit)
        : 20
      this.newsItemsFilter.limit = limit + 20
    },
    nextPage() {
      const offset = this.newsItemsFilter.offset
        ? parseInt(this.newsItemsFilter.offset)
        : 0
      const limit = this.newsItemsFilter.limit
        ? parseInt(this.newsItemsFilter.limit)
        : 20

      this.newsItemsFilter.offset = offset + limit
    },
    updateFilter(filter) {
      Object.keys(filter).forEach((element) => {
        this.newsItemsFilter[element] = filter[element]
      })
    },
    updateAssetFilter(filter) {
      Object.keys(filter).forEach((element) => {
        this.assetFilter[element] = filter[element]
      })
    },
    updateReportFilter(filter) {
      Object.keys(filter).forEach((element) => {
        this.reportFilter[element] = filter[element]
      })
    },
    setReportFilter(filter) {
      this.reportFilter = filter
    },
    updateProductFilter(filter) {
      Object.keys(filter).forEach((element) => {
        this.productFilter[element] = filter[element]
      })
    },
    setProductFilter(filter) {
      this.productFilter = filter
    }
  }
})
