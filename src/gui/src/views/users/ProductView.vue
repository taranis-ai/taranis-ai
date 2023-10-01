<template>
  <v-container fluid style="min-height: 100vh">
    <product-item v-if="readyToRender" :product-prop="product" :edit="edit" />
  </v-container>
</template>

<script>
import { ref, onBeforeMount } from 'vue'
import { getProduct } from '@/api/publish'
import ProductItem from '@/components/publish/ProductItem.vue'
import { useRoute } from 'vue-router'

export default {
  name: 'ProductView',
  components: {
    ProductItem
  },
  setup() {
    const route = useRoute()
    const defaultProduct = ref({
      id: null,
      title: '',
      product_type_id: null,
      report_items: []
    })
    const product = ref(defaultProduct.value)

    const edit = ref(true)
    const readyToRender = ref(false)

    const loadProducts = async () => {
      console.debug('Loading product', route.params.id)
      if (route.params.id && route.params.id !== '0') {
        const response = await getProduct(route.params.id)
        return response.data
      }
      edit.value = false
      return defaultProduct.value
    }

    const reportCreated = () => {
      edit.value = true
    }

    onBeforeMount(async () => {
      product.value = await loadProducts()
      readyToRender.value = true
    })

    return { product, edit, readyToRender, reportCreated }
  }
}
</script>
