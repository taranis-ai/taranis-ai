<template>
    <v-container fluid>
        <v-list single-line subheader elevation="2">
            <CardCompact v-for="item in items" :item="item" :key="item.id"
                         :deletePermission="deletePermission"></CardCompact>
        </v-list>
    </v-container>
</template>

<script>
import CardCompact from '../card/CardCompact'

export default {
  name: 'ContentDataCompact',
  components: {
    CardCompact
  },
  props: {
    name: String,
    action: String,
    getter: String,
    deletePermission: String
  },
  data: () => ({
    items: [],
    filter: {
      search: ''
    }
  }),
  methods: {
    updateItems () {
      this.$store.dispatch(this.action, this.filter)
        .then(() => {
          this.items = this.$store.getters[this.getter].items
        })
    }
  },
  mounted () {
    this.updateItems()
    this.$root.$on('notification', () => {
      this.updateItems()
    })
    this.$root.$on('update-items-filter', (filter) => {
      this.filter = filter
      this.updateData()
    })
  }
}
</script>
