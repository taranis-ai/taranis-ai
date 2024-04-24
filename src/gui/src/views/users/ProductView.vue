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

export default {
  name: 'ProductView',
  components: {
    ProductItem
  },
  props: {
    productId: {
      type: String,
      required: true
    }
  },
  setup(props) {
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
      console.debug('Loading product', props.productId)
      if (props.productId) {
        const response = await getProduct(props.productId)
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
