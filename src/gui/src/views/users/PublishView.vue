<template>
  <v-container fluid>
    <v-card v-for="product in products" :key="product.id" class="mt-3">
      <v-card-title>
        {{ product }}
      </v-card-title>
    </v-card>
    <h2 v-if="!products">No Products found</h2>
  </v-container>
</template>

<script>
import { deleteProduct } from '@/api/publish'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

export default {
  name: 'PruoductView',
  components: {},
  data: function () {
    return {
      selected: [],
      products: []
    }
  },
  computed: {},
  methods: {
    ...mapActions('publish', ['loadProducts']),
    ...mapGetters('publish', ['getProducts']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadProducts().then(() => {
        const sources = this.getProducts()
        this.products = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
    },
    editProduct(item) {
      this.$router.push('/product/' + item.id)
    },
    deleteItem(item) {
      deleteProduct(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    },
    selectionChange(selected) {
      this.selected = selected.map((item) => item.id)
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
