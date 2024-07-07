<template>
  <DataTable
    :items="products_data"
    :header-filter="['title', 'created', 'type', 'reports', 'actions']"
    :add-button="false"
    :search-bar="false"
    @delete-item="deleteItem"
    @edit-item="editItem"
    @update-items="updateData"
    @selection-change="selectionChange"
  >
    <template #titlebar>
      <h2>Products</h2>
    </template>
  </DataTable>
</template>

<script>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import { usePublishStore } from '@/stores/PublishStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'

export default {
  name: 'ProductView',
  components: {
    DataTable
  },
  setup() {
    const mainStore = useMainStore()
    const publishStore = usePublishStore()
    const selected = ref([])
    const router = useRouter()
    const { d } = useI18n()

    const { products, product_types } = storeToRefs(publishStore)

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

    const editItem = (item) => {
      router.push('/product/' + item.id)
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection
    }

    onMounted(() => {
      publishStore.loadProductTypes()
    })

    onUnmounted(() => {
      mainStore.resetItemCount()
    })

    return {
      selected,
      products,
      products_data,
      updateData,
      editItem,
      deleteItem: publishStore.removeProduct,
      selectionChange
    }
  }
}
</script>
