<template>
  <v-data-table-server
    :headers="headers"
    :items-length="totalItems"
    :items="clusters"
    :loading="loading"
    :search="search"
    class="elevation-1"
    item-value="name"
    @update:options="loadItems"
  />
</template>

<script>
import { ref } from 'vue'
import { useDashboardStore } from '@/stores/DashboardStore'

export default {
  name: 'TagTable',
  props: {
    tagType: { type: String, required: true }
  },
  setup(props) {
    const headers = [
      { title: 'Tag', key: 'name' },
      { title: 'Size', key: 'size' }
    ]
    const loading = ref(false)
    const search = ref('')
    const totalItems = ref(100)
    const clusters = ref([])
    const store = useDashboardStore()

    function loadItems({ page, itemsPerPage }) {
      loading.value = true
      const params = {
        page: page,
        per_page: itemsPerPage
      }
      store
        .getCluster(props.tagType, params)
        .then((cluster) => {
          console.debug(cluster)
          clusters.value = cluster.items
          totalItems.value = cluster.total_count
        })
        .finally(() => {
          loading.value = false
        })
    }

    return {
      loading,
      search,
      totalItems,
      headers,
      clusters,
      loadItems
    }
  }
}
</script>
