<template>
  <v-container fluid style="min-height: 100vh">
    <card-product :product-prop="product" />
  </v-container>
</template>

<script>
import { ref, onMounted } from 'vue'
import { getProduct } from '@/api/publish'
import CardProduct from '@/components/publish/CardProduct.vue'

export default {
  name: 'ProductView',
  components: {
    CardProduct
  },
  setup() {
    const defaultProduct = {
      id: null,
      uuid: null,
      title: ''
    }

    const product = ref({})
    const edit = ref(true)

    const loadProducts = async () => {
      if (this.$route.params.id && this.$route.params.id !== '0') {
        const response = await getProduct(this.$route.params.id)
        product.value = response.data
      } else {
        edit.value = false
        product.value = defaultProduct
      }
    }

    onMounted(() => {
      loadProducts()
    })

    return {
      product,
      edit
    }
  }
}
</script>
