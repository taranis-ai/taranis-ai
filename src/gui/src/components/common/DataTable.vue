<template>
  <v-data-table
    :sort-by="sortBy"
    :headers="headers"
    :items="items"
    :search="search"
    class="data-table-base"
    show-select
    :model-value="selected"
    :items-per-page="itemsPerPage"
    :hide-default-footer="items.length < itemsPerPage"
    @update:model-value="emitFilterChange"
    @click:row="rowClick"
  >
    <template #top>
      <v-card v-if="showTop" elevation="0">
        <v-card-title>
          <v-row no-gutters>
            <v-text-field
              v-if="searchBar"
              v-model="search"
              append-inner-icon="mdi-magnify"
              density="compact"
              label="Search"
              variant="outlined"
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
              {{ $t('button.new_item') }}
            </v-btn>
            <slot name="titlebar"></slot>
          </v-row>
        </v-card-title>
      </v-card>
    </template>
    <template #item.default="{ item }">
      <v-chip :color="getDefaultColor(item.default)" variant="outlined">
        {{ item.default }}
      </v-chip>
    </template>
    <template #item.state="{ item }">
      <v-chip :color="sourceStateMap[item.state].color" variant="outlined">
        {{ sourceStateMap[item.state].text }}
      </v-chip>
    </template>

    <template #item.completed="{ item }">
      <v-chip
        :color="item.completed ? 'green' : 'blue'"
        variant="outlined"
        :text="item.completed ? 'true' : 'false'"
      />
    </template>

    <template #item.tag="{ item }">
      <v-icon small class="mr-1" :icon="item.tag" />
    </template>
    <template #item.icon="{ item }">
      <v-img
        :src="'data:image/png;base64,' + item.icon"
        width="32"
        height="32"
      />
    </template>

    <template #item.actions="{ item }">
      <div class="d-inline-flex">
        <slot name="actionColumn" :item="item"></slot>
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
    <template #no-data>
      <slot name="nodata">
        <v-empty-state
          icon="mdi-magnify"
          title="No Data Found"
          class="my-5"
          action-text="Reload Data"
          @click:action="updateItems()"
        />
      </slot>
    </template>
  </v-data-table>
</template>

<script>
import { ref, defineComponent, toRaw } from 'vue'
import { sourceStateMap } from '@/utils/helpers'

export default defineComponent({
  name: 'DataTable',
  props: {
    items: {
      type: Array,
      required: true,
      default: () => []
    },
    addButton: {
      type: Boolean,
      default: false
    },
    headerFilter: {
      type: Array,
      default: () => []
    },
    searchBar: {
      type: Boolean,
      default: true
    },
    showTop: {
      type: Boolean,
      default: true
    },
    itemsPerPage: {
      type: Number,
      default: 20
    },
    sortBy: {
      type: Array,
      default: () => []
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
      } else if (key === 'created') {
        return {
          title: 'Created',
          key: 'created',
          sortable: true,
          sort: (a, b) => new Date(a) - new Date(b)
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
      const item = toRaw(value.item)
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
      sourceStateMap,
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

<style lang="scss">
.data-table-base {
  border: 2px solid white;
  transition: 180ms;
  box-shadow: 1px 2px 9px 0px rgba(0, 0, 0, 0.15);
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  margin: 4px;
  padding: 12px;
}
</style>
