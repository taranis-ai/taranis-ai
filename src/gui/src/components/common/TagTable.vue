<template>
  <v-data-table-server
    :headers="headers"
    :items-length="totalItems"
    :items="clusters"
    :loading="loading"
    :sort-by="[{ key: 'size', order: 'desc' }]"
    :search="search"
    class="elevation-1"
    item-value="name"
    @update:options="loadItems"
  >
    <template #top>
      <v-card elevation="0">
        <v-card-title>
          <v-row no-gutters>
            <v-text-field
              v-model="search"
              append-inner-icon="mdi-magnify"
              density="compact"
              label="Search"
              variant="outlined"
              single-line
              class="mr-4"
              hide-details
            />
          </v-row>
        </v-card-title>
      </v-card>
    </template>

    <template #item.name="{ item }">
      <router-link :to="'/assess?tags=' + item.name">
        {{ item.name }}
      </router-link>
    </template>
    <template #item.action="{ item }">
      <div class="d-inline-flex">
        <v-tooltip left>
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              color="error"
              icon="mdi-delete-outline"
              @click.stop="deleteItem(item)"
            />
          </template>
          <span>{{ $t('button.delete') }}</span>
        </v-tooltip>
      </div>
    </template>
  </v-data-table-server>
</template>

<script>
import { ref } from 'vue'
import { useDashboardStore } from '@/stores/DashboardStore'
import { deleteTag } from '@/api/dashboard'

export default {
  name: 'TagTable',
  props: {
    tagType: { type: String, required: true }
  },
  setup(props) {
    const headers = [
      { title: 'Tag', key: 'name' },
      { title: 'Size', key: 'size' },
      { title: 'Action', key: 'action', sortable: false, width: '30px' }
    ]
    const loading = ref(false)
    const totalItems = ref(0)
    const clusters = ref([])
    const store = useDashboardStore()
    const search = ref('')

    async function loadItems({ page, itemsPerPage, sortBy }) {
      loading.value = true
      const params = {
        page: page,
        per_page: itemsPerPage,
        sort_by:
          sortBy.length > 0 ? `${sortBy[0].key}_${sortBy[0].order}` : null,
        search: search.value
      }
      console.debug('loadItems', params)

      const cluster = await store.getCluster(props.tagType, params)
      clusters.value = cluster.items
      totalItems.value = cluster.total_count
      loading.value = false
    }

    async function deleteItem(item) {
      console.debug('deleteItem', item)
      deleteTag(item.name)
      clusters.value = clusters.value.filter((i) => i.name !== item.name)
      totalItems.value -= 1
    }

    return {
      search,
      loading,
      totalItems,
      headers,
      clusters,
      loadItems,
      deleteItem
    }
  }
}
</script>
