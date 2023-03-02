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
    loading: false,
    available_tags: [],
    search: ''
  }),
  props: {
    tags: {
      type: Array,
      default: () => []
    }
  },
  computed: {
    selected: {
      get() {
        return this.tags
      },
      set(val) {
        this.$emit('input', val)
      }
    }
  },
  watch: {
    search(val) {
      val && this.querySelections({ search: val })
    }
  },
  methods: {
    shortText(item) {
      return item.length > 20 ? item.substring(0, 20) + '...' : item
    },
    async querySelections(filter) {
      this.loading = true
      await getTags(filter).then((res) => {
        this.available_tags = res.data
        this.loading = false
      })
    }
  },
  async mounted() {
    await this.querySelections()
  }
}
</script>
