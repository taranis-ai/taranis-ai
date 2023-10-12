<template>
  <DataTable
    :items="products_data"
    :header-filter="['title', 'created', 'type', 'reports', 'actions']"
    :add-button="false"
    :search-bar="false"
    @delete-item="deleteItem"
    @edit-item="editItem"
    @add-item="addItem"
    @update-items="updateData"
    @selection-change="selectionChange"
  />
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import { deleteProduct } from '@/api/publish'
import { usePublishStore } from '@/stores/PublishStore'
import { useMainStore } from '@/stores/MainStore'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
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

    const updateData = async () => {
      await publishStore.loadProducts()
      await publishStore.loadProductTypes()
      mainStore.itemCountTotal = products.value.total_count
      mainStore.itemCountFiltered = products.value.items.length
    }

    const addItem = () => {
      router.push('/report/0')
    }

    const editItem = (item) => {
      router.push('/product/' + item.id)
    }

    const deleteItem = (item) => {
      deleteProduct(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.title}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.title}`)
        })
    }

    const selectionChange = (new_selection) => {
      selected.value = new_selection
    }

    onMounted(() => {
      updateData()
    })

    return {
      selected,
      products,
      products_data,
      updateData,
      addItem,
      editItem,
      deleteItem,
      selectionChange
    }
  }
}
</script>
