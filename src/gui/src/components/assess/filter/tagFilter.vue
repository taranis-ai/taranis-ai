<template>
  <v-autocomplete
    v-model="selected"
    :loading="loading"
    :items="available_tags"
    chips
    dense
    deletable-chips
    :search-input.sync="search"
    clearable
    flat
    no-data-text="No tags found"
    item-value="name"
    item-text="name"
    hide-details
    cache-items
    label="Tags"
    multiple
  >
    <template v-slot:item="{ item }">
      <v-icon left>{{ tagIcon(item.tag_type) }}</v-icon>{{ shortText(item.name) }}
    </template>
    <template v-slot:selection="{ item }">
      <v-chip>
      <v-icon left>{{ tagIcon(item.tag_type) }}</v-icon>{{ shortText(item.name) }}
      </v-chip>
    </template>
  </v-autocomplete>
</template>

<script>
import { getTags } from '@/api/assess'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'tagFilter',
  data: () => ({
    loading: false,
    available_tags: [],
    selected_tags: [],
    search: ''
  }),
  props: {},
  computed: {
    selected: {
      get() {
        return this.selected_tags
      },
      set(val) {
        this.setTags(val)
        this.updateNewsItems()
      }
    }
  },
  watch: {
    search(val) {
      val && this.querySelections({ search: val })
    }
  },
  methods: {
    ...mapGetters('filter', ['getFilterTags']),
    ...mapActions('filter', ['setTags']),
    ...mapActions('assess', ['updateNewsItems']),
    shortText(item) {
      return item.length > 20 ? item.substring(0, 20) + '...' : item
    },
    tagIcon(tag_type) {
      if (tag_type === 'ORG') {
        return 'mdi-domain'
      }
      if (tag_type === 'LOC') {
        return 'mdi-map-marker'
      }
      if (tag_type === 'PER') {
        return 'mdi-account'
      }
      return 'mdi-tag'
    },
    async querySelections(filter) {
      this.loading = true
      await getTags(filter).then((res) => {
        this.available_tags = res.data
        this.selected_tags.forEach(tag => {
          if (!this.available_tags.includes(tag)) {
            this.available_tags.unshift(tag)
          }
        })
        this.loading = false
      })
    },
    loadFilterTags() {
      const tags = this.getFilterTags()
      if (!tags) {
        return []
      }
      return tags.map((tag) => {
        return { name: tag }
      })
    }
  },
  async mounted() {
    this.selected_tags = this.loadFilterTags()
    await this.querySelections()

    console.debug('mounted tagFilter')
  }
}
</script>
