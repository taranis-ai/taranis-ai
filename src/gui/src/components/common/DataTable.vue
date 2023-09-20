<template>
  <v-data-table
    :headers="headers"
    :items="items"
    :search="search"
    class="elevation-1"
    show-select
    @click:row="rowClick"
    @update:model-value="emitFilterChange"
  >
    <template #top>
      <v-card>
        <v-card-title>
          <v-row no-gutters>
            <v-text-field
              v-if="searchBar"
              v-model="search"
              append-inner-icon="mdi-magnify"
              density="compact"
              label="Search"
              single-line
              class="mr-4"
              hide-details
            />
            <v-btn
              v-if="selected.length > 0"
              color="error"
              dark
              class="ml-4"
              @click="deleteItems(selected)"
            >
              Delete {{ selected.length }}
            </v-btn>
            <v-btn
              v-if="addButton"
              color="primary"
              dark
              class="ml-4"
              @click="addItem"
            >
              New Item
            </v-btn>
            <slot name="titlebar"></slot>
          </v-row>
        </v-card-title>
      </v-card>
    </template>
    <template #item.default="{ item }">
      <v-chip :color="getDefaultColor(item.raw.default)" variant="outlined">
        {{ item.raw.default }}
      </v-chip>
    </template>
    <template #item.state="{ item }">
      <v-chip :color="item.raw.state > 0 ? 'red' : 'green'" variant="outlined">
        {{ item.raw.state > 0 ? 'error' : 'ok' }}
      </v-chip>
    </template>

    <template #item.completed="{ item }">
      <v-chip
        :color="item.raw.completed ? 'green' : 'blue'"
        variant="outlined"
        :text="item.raw.completed ? 'true' : 'false'"
      />
    </template>

    <template #item.tag="{ item }">
      <v-icon small class="mr-1" :icon="tagIcon || item.raw.tag" />
    </template>
    <template #item.icon="{ item }">
      <v-img
        :src="'data:image/png;base64,' + item.raw.icon"
        width="32"
        height="32"
      />
    </template>

    <template #item.actions="{ item }">
      <div class="d-inline-flex">
        <slot name="actionColumn" :item="item.raw"></slot>
        <v-tooltip left>
          <template #activator="{ props }">
            <v-icon
              v-bind="props"
              color="red"
              icon="mdi-delete"
              @click.stop="deleteItem(item.raw)"
            />
          </template>
          <span>Delete</span>
        </v-tooltip>
      </div>
    </template>
    <template v-if="items.length < 10" #bottom />
    <template #no-data>
      <v-btn color="primary" @click.stop="updateItems()">
        <v-icon class="mr-1" icon="mdi-refresh" />
        Refresh
      </v-btn>
    </template>
  </v-data-table>
</template>

<script>
import { ref, defineComponent, toRaw } from 'vue'
import { useMainStore } from '@/stores/MainStore'

export default defineComponent({
  name: 'DataTable',
  props: {
    items: {
      type: Array,
      required: true
    },
    addButton: {
      type: Boolean,
      default: false
    },
    sortByItem: {
      type: String,
      default: null
    },
    headerFilter: {
      type: Array,
      default: () => []
    },
    searchBar: {
      type: Boolean,
      default: true
    },
    tagIcon: {
      type: String,
      default: ''
    }
  },
  emits: [
    'delete-item',
    'edit-item',
    'add-item',
    'selection-change',
    'update-items'
  ],
  setup(props, { emit }) {
    const search = ref('')
    const selected = ref([])

    const store = useMainStore()

    let headers = []

    function headerTransform(key) {
      if (key === 'tag') {
        return {
          title: 'Tag',
          key: 'tag',
          sortable: false,
          width: '15px'
        }
      } else if (key === 'actions') {
        return {
          title: 'Actions',
          key: 'actions',
          sortable: false,
          width: '30px'
        }
      }

      return { title: key, key: key }
    }

    if (props.headerFilter.length > 0) {
      headers = props.headerFilter.map((key) => headerTransform(key))
    } else if (props.items.length > 0) {
      headers = Object.keys(props.items[0]).map((key) => headerTransform(key))
    }

    function emitFilterChange(selectedItems) {
      selected.value = selectedItems
      emit('selection-change', selectedItems)
      store.itemCountFiltered = selectedItems.length
    }

    function customFilter(value, query) {
      return (
        value != null &&
        query != null &&
        typeof value === 'string' &&
        value.toString().indexOf(query) !== -1
      )
    }

    function rowClick(event, value) {
      const item = toRaw(value.item.raw)
      emit('edit-item', item)
    }

    function addItem() {
      emit('add-item')
    }

    function getDefaultColor(defaultgroup) {
      return defaultgroup ? 'green' : ''
    }

    function deleteItem(item) {
      emit('delete-item', item)
    }

    function deleteItems(itemsToDelete) {
      itemsToDelete.forEach((item) => deleteItem({ id: item }))
      selected.value = []
    }

    function updateItems() {
      emit('update-items')
    }

    return {
      search,
      selected,
      headers,
      emitFilterChange,
      customFilter,
      rowClick,
      addItem,
      getDefaultColor,
      deleteItem,
      deleteItems,
      updateItems
    }
  }
})
</script>
