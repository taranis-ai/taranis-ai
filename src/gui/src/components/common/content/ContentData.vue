<template>
  <v-container id="selector">
    <component
      v-bind:is="cardLayout()"
      v-for="collection in collections"
      :card="collection"
      :key="collection.id"
      :deletePermission="deletePermission"
    ></component>
  </v-container>
</template>

<script>
import CardAssess from '@/components/assess/legacy/CardAssess'
import CardAnalyze from '@/components/analyze/CardAnalyze'
import CardProduct from '@/components/publish/CardProduct'
import CardPreset from '@/components/common/card/CardPreset'

export default {
  name: 'ContentData',
  components: {
    CardAssess,
    CardAnalyze,
    CardProduct,
    CardPreset
  },
  props: {
    name: String,
    action: String,
    getter: String,
    cardItem: String,
    deletePermission: String
  },
  data: () => ({
    collections: [],
    filter: {
      search: ''
    }
  }),
  methods: {
    updateData() {
      this.$store.dispatch(this.action, this.filter).then(() => {
        this.collections = this.$store.getters[this.getter].items
      })
    },
    cardLayout: function () {
      return this.cardItem
    }
  },
  mounted() {
    this.updateData()
    this.$root.$on('notification', () => {
      this.updateData()
    })
    this.$root.$on('update-data', () => {
      this.updateData()
    })
    this.$root.$on('update-items-filter', (filter) => {
      this.filter = filter
      this.updateData()
    })
  },
  beforeDestroy() {
    this.$root.$off('notification')
    this.$root.$off('update-data')
    this.$root.$off('update-items-filter')
  }
}
</script>
