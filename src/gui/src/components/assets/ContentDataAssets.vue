<template>

    <v-container id="selector">
        <component v-bind:is="cardLayout()" v-for="collection in collections" :card="collection" :key="collection.id"></component>
    </v-container>

</template>

<script>
import CardAsset from '@/components/assets/CardAsset'
import CardCompact from '@/components/common/card/CardCompact'

export default {
  name: 'ContentData',
  components: {
    CardAsset,
    CardCompact
  },
  props: {
    name: String,
    action: String,
    getter: String,
    cardItem: String
  },
  data: () => ({
    collections: [],
    filter: {
      search: '',
      vulnerable: false,
      sort: 'ALPHABETICAL'
    }
  }),
  methods: {
    updateData () {
      if (window.location.pathname.includes('/group/')) {
        const i = window.location.pathname.indexOf('/group/')
        const len = window.location.pathname.length
        const group = window.location.pathname.substring(i + 7, len)

        this.$store.dispatch('getAllAssets', { group_id: group, filter: this.filter })
          .then(() => {
            this.collections = this.$store.getters.getAssets.items
          })
      }
    },
    cardLayout: function () {
      return this.cardItem
    }
  },
  watch: {
    $route () {
      this.updateData()
    }
  },
  mounted () {
    this.updateData()
    this.$root.$on('notification', () => {
      this.updateData()
    })
    this.$root.$on('update-data', () => {
      this.updateData()
    })
    this.$root.$on('update-assets-filter', (filter) => {
      this.filter = filter
      this.updateData()
    })
  }
}
</script>
