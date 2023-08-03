<template>
  <DataTable
    :items="products.items"
    :add-button="false"
    :search-bar="false"
    sort-by-item="id"
    :action-column="true"
    @delete-item="deleteItem"
    @edit-item="editItem"
    @add-item="addItem"
    @update-items="updateData"
    @selection-change="selectionChange"
  >
  </DataTable>
</template>

<script>
import { ref } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import { deleteProduct } from '@/api/publish'
import { usePublishStore } from '@/stores/PublishStore'
import { useMainStore } from '@/stores/MainStore'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { storeToRefs } from 'pinia'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

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
    const { products } = storeToRefs(publishStore)

    const updateData = async () => {
      await publishStore.loadProducts()
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
          notifySuccess(`Successfully deleted ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
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
      updateData,
      addItem,
      editItem,
      deleteItem,
      selectionChange
    }
  }
}
</script>
