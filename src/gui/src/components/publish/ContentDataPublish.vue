<template>
  <v-container id="selector_publish">
    <CardProduct
      v-for="collection in collections"
      :card="collection"
      :key="collection.id"
    ></CardProduct>
    <v-card v-intersect.quiet="infiniteScrolling"></v-card>
  </v-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'
import CardProduct from './CardProduct'

export default {
  name: 'ContentDataPublish',
  components: {
    CardProduct
  },
  data: () => ({
    collections: [],
    data_loaded: false,
    filter: {
      search: undefined,
      range: 'ALL',
      sort: 'DATE_DESC'
    }
  }),
  methods: {
    ...mapGetters('publish', ['getProducts']),
    ...mapActions('publish', ['loadProducts']),
    infiniteScrolling(entries, observer, isIntersecting) {
      if (this.data_loaded && isIntersecting) {
        this.updateData(true, false)
      }
    },

    updateData(append, reload_all) {
      this.data_loaded = false

      if (append === false) {
        this.collections = []
      }

      let offset = this.collections.length
      let limit = 20
      if (reload_all) {
        offset = 0
        if (this.collections.length > limit) {
          limit = this.collections.length
        }
        this.collections = []
      }
      this.loadProducts({
        filter: this.filter,
        offset: offset,
        limit: limit
      }).then(() => {
        this.collections = this.collections.concat(this.getProducts())
        console.log(this.collections)
        this.data_loaded = true
      })
    }
  },
  watch: {
    $route() {
      this.updateData(false, false)
    }
  },
  mounted() {
    this.updateData()
    this.$root.$on('notification', () => {
      this.updateData(true, true)
    })
    this.$root.$on('update-products-filter', (filter) => {
      this.filter = filter
      this.updateData(false, false)
    })
  },
  created() {},
  beforeDestroy() {}
}
</script>
