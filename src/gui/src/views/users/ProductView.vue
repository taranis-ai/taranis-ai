<template>
  <v-container fluid>
    <product-item
      v-if="readyToRender"
      :product-prop="product"
      :edit="edit"
      @productcreated="productCreated"
    />
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
      if (route.params.id) {
        const response = await getProduct(route.params.id)
        return response.data
      }
      edit.value = false
      return defaultProduct.value
    }

    const productCreated = () => {
      edit.value = true
    }

    onBeforeMount(async () => {
      product.value = await loadProducts()
      readyToRender.value = true
    })

    return { product, edit, readyToRender, productCreated }
  }
}
</script>
