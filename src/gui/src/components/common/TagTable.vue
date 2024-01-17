<template>
  <v-data-table-server
    :headers="headers"
    :items-length="totalItems"
    :items="clusters"
    :loading="loading"
    class="elevation-1"
    item-value="name"
    @update:options="loadItems"
  >
    <template #item.name="{ item }">
      <router-link :to="'/assess?tags=' + item.name">
        {{ item.name }}
      </router-link>
    </template>
  </v-data-table-server>
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
    const totalItems = ref(0)
    const clusters = ref([])
    const store = useDashboardStore()

    function loadItems({ page, itemsPerPage, sortBy }) {
      loading.value = true
      const params = {
        page: page,
        per_page: itemsPerPage,
        sort_by: sortBy.length > 0 ? `${sortBy[0].key}_${sortBy[0].order}` : null
      }
      console.debug('loadItems', params)

      store
        .getCluster(props.tagType, params)
        .then((cluster) => {
          clusters.value = cluster.items
          totalItems.value = cluster.total_count
        })
        .finally(() => {
          loading.value = false
        })
    }

    return {
      loading,
      totalItems,
      headers,
      clusters,
      loadItems
    }
  }
}
</script>
