<template>
<v-container fluid>
  <!-- Product form with Save Button and Dirty State Warning -->
  <v-row>
    <v-col>
      <v-text-field
        v-model="product.title"
        label="Product Title"
      />
    </v-col>
  </v-row>

  <!-- Display ProductItem if ready to render -->
  <product-item
    v-if="readyToRender"
    :product-prop="product"
    :edit="edit"
    @productcreated="productCreated"
  />

  <!-- Save Button with warning icon if there are unsaved changes -->
  <v-btn :color="dirty ? 'warning' : 'primary'" @click="saveProduct">
    <v-icon v-if="dirty">mdi-alert</v-icon> Save
    {{ dirty ? 'Unsaved changes detected!' : 'Save' }}
  </v-btn>
</v-container>
</template>
<script>
import { ref, reactive, onMounted, watch } from 'vue';
import { getProduct } from '@/api/publish';
import ProductItem from '@/components/publish/ProductItem.vue';

export default {
  name: 'ProductView',
  components: {
    ProductItem
  },
  props: {
    productId: {
      type: String, // Ensuring the prop type is a String (or change to Number if needed)
      required: true
    }
  },
  setup(props) {
    const product = reactive({
      id: null,
      title: '',
      product_type_id: null,
      report_items: []
    });

    const originalProduct = ref({});
    const dirty = ref(false);
    const readyToRender = ref(false);
    const edit = ref(true);

    // Watch for changes in product to detect unsaved changes
    watch(
      () => product,
      (newVal) => {
        dirty.value = (
          newVal.title !== originalProduct.value.title ||
          JSON.stringify(newVal.report_items) !== JSON.stringify(originalProduct.value.report_items)
        );
        console.log('Dirty state updated via watcher:', dirty.value);
      },
      { deep: true }
    );

    // Function to load product data
    const loadProduct = async () => {
      console.debug('Loading product', props.productId);
      if (props.productId && props.productId !== 'null') { // Check if productId is valid
        try {
          const response = await getProduct(props.productId);
          if (response && response.data) {
            product.id = response.data.id;
            product.title = response.data.title || '';
            product.product_type_id = response.data.product_type_id || null;
            product.report_items = response.data.report_items || [];

            originalProduct.value = JSON.parse(JSON.stringify(response.data));
            console.log('Product loaded:', product);
          } else {
            console.error('Product data is invalid or empty');
          }
        } catch (error) {
          console.error('Error loading product:', error);
        }
      } else {
        console.error('productId is missing or invalid');
      }
      readyToRender.value = true;
    };

    // Save product and reset dirty state
    const saveProduct = () => {
      console.log('Saving product...');
      originalProduct.value = JSON.parse(JSON.stringify(product));
      dirty.value = false;
      console.log('Dirty state after save:', dirty.value);
    };

    const productCreated = () => {
      edit.value = true;
    };

    onMounted(async () => {
      await loadProduct();
    });

    return {
      product,
      originalProduct,
      edit,
      readyToRender,
      dirty,
      saveProduct,
      productCreated
    };
  }
};
</script>
