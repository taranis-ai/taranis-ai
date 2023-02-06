<template>
  <v-autocomplete
    v-model="selected"
    :loading="loading"
    :items="tags"
    chips
    dense
    deletable-chips
    :search-input.sync="search"
    clearable
    flat
    no-data-text="No tags found"
    hide-details
    cache-items
    label="Tags"
    multiple
  >
  <template v-slot:item="{ item }">
   {{ shortText(item) }}
  </template>
  </v-autocomplete>
</template>

<script>
import { getTags } from '@/api/assess'

export default {
  name: 'tagFilter',
  emits: ['input'],
  data: () => ({
    selected: [],
    loading: false,
    tags: [],
    search: ''
  }),
  props: {},
  watch: {
    search(val) {
      val && val !== this.select && this.querySelections(val)
    }
  },
  methods: {
    shortText(item) {
      return item.length > 20 ? item.substring(0, 20) + '...' : item
    },
    querySelections(v) {
      this.loading = true
      getTags().then((res) => {
        this.tags = res.data
        this.loading = false
      })
    }
  },
  mounted() {
    this.querySelections()
  }
}
</script>
