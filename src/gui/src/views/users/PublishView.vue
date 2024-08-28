<template>
  <DataTable
    :items="products_data"
    :header-filter="['title', 'created', 'type', 'reports', 'actions']"
    :add-button="false"
    :search-bar="false"
    :items-per-page="productFilter.limit"
    @delete-item="deleteItem"
    @edit-item="editItem"
    @update-items="updateData"
    @selection-change="selectionChange"
  >
    <template #titlebar>
      <h2>Products</h2>
    </template>
    <template #nodata>
      <v-alert title="No Products Found" type="warning">
        <v-row no-gutters class="mt-5">
          <v-btn
            class="mr-2"
            min-width="48%"
            color="primary"
            text="Reset Filter"
            prepend-icon="mdi-refresh"
            @click="resetFilter()"
          />
          <v-btn
            color="primary"
            min-width="48%"
            class="ml-2"
            text="Create new Product"
            prepend-icon="mdi-chart-box-plus-outline"
            @click="createProduct()"
          />
        </v-row>
      </v-alert>
    </template>
  </DataTable>
</template>

<script>
import { ref, computed, onBeforeMount } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import { usePublishStore } from '@/stores/PublishStore'
import { storeToRefs } from 'pinia'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useFilterStore } from '@/stores/FilterStore'
import { updateFilterFromQuery } from '@/utils/helpers'

export default {
  name: 'ProductView',
  components: {
    DataTable
  },
  setup() {
    const publishStore = usePublishStore()
    const selected = ref([])
    const router = useRouter()
    const filterStore = useFilterStore()
    const { d } = useI18n()

    const { products, product_types } = storeToRefs(publishStore)
    const { productFilter } = storeToRefs(filterStore)

    const products_data = computed(() => {
      return products.value.items.map((item) => {
        return {
          id: item.id,
          title: item.title,
          created: d(item.created, 'long'),
          reports: item.report_items.length,
          type: product_types.value.items.find(
            (type) => type.id === item.product_type_id
          )?.title
        }
      })
    })

    async function updateData() {
      await publishStore.loadProductTypes()
      await publishStore.updateProducts()
    }

    function editItem(item) {
      router.push('/product/' + item.id)
    }

    function selectionChange(new_selection) {
      selected.value = new_selection
    }

    function createProduct() {
      router.push('/product/')
    }

    function resetFilter() {
      publishStore.reset()
      filterStore.resetFilter()
      updateData()
    }

    onBeforeMount(() => {
      updateData()
      updateFilterFromQuery(useRoute().query, 'publish')
    })

    return {
      selected,
      products,
      products_data,
      productFilter,
      updateData,
      editItem,
      createProduct,
      resetFilter,
      deleteItem: publishStore.removeProduct,
      selectionChange
    }
  }
}
</script>
