<template>
  <v-container fluid style="min-height: 100vh">
    <card-product :card="product" />
  </v-container>
</template>

<script>
import { getProduct } from '@/api/publish'
import CardProduct from '@/components/publish/CardProduct'

export default {
  name: 'ProductView',
  data: () => ({
    product: {}
  }),
  components: {
    CardProduct
  },
  async created() {
    this.products = await this.loadProducts()
  },
  methods: {
    async loadProducts() {
      if (this.$route.params.id) {
        return await getProduct(this.$route.params.id).then((response) => {
          return response.data
        })
      }
    }
  }
}
</script>
