<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <slot name="header"></slot>
    <v-data-table
      :headers="headers"
      :items="items"
      :search="search"
      :sort-by="[{ key: sortByItem }]"
      class="elevation-1"
      show-select
      :custom-filter="customFilter"
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
        <v-chip
          :color="item.raw.state > 0 ? 'red' : 'green'"
          variant="outlined"
        >
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
        <v-icon small class="mr-1" :icon="item.raw.tag" />
      </template>

      <template #item.actions="{ item }">
        <div class="d-inline-flex">
          <slot name="actionColumn"></slot>
          <v-tooltip left>
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                color="red"
                @click.stop="deleteItem(item.raw)"
              >
                mdi-delete
              </v-icon>
            </template>
            <span>Delete</span>
          </v-tooltip>
        </div>
      </template>
      <template v-if="items.length < 10" #bottom />
      <template #no-data>
        <v-btn color="primary" @click.stop="updateItems()">
          <v-icon class="mr-1">mdi-refresh</v-icon>
          Refresh
        </v-btn>
      </template>
    </v-data-table>
  </v-container>
</template>

<script>
import { useMainStore } from '@/stores/MainStore'
import { mapWritableState } from 'pinia'
import { defineComponent, toRaw } from 'vue'

export default defineComponent({
  name: 'DataTable',
  components: {},
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
    actionColumn: {
      type: Boolean,
      default: false
    },
    searchBar: {
      type: Boolean,
      default: true
    }
  },
  emits: [
    'delete-item',
    'edit-item',
    'add-item',
    'selection-change',
    'update-items'
  ],
  data: () => ({
    search: '',
    selected: []
  }),
  computed: {
    ...mapWritableState(useMainStore, ['itemCountFiltered']),
    headers() {
      const actionHeader = {
        title: 'Actions',
        key: 'actions',
        sortable: false,
        width: '30px'
      }
      let headers = []
      if (this.headerFilter.length > 0) {
        if (typeof this.headerFilter[0] !== 'object') {
          headers = this.headerFilter.map((key) => this.headerTransform(key))
        } else {
          headers = this.headerFilter
        }
      } else if (this.items.length > 0) {
        headers = Object.keys(this.items[0]).map((key) =>
          this.headerTransform(key)
        )
      }
      if (this.actionColumn) {
        headers.push(actionHeader)
      }
      return headers
    }
  },
  methods: {
    headerTransform(key) {
      if (key === 'tag') {
        return {
          title: key,
          key: key,
          sortable: false,
          width: '15px'
        }
      }
      return { title: key, key: key }
    },
    emitFilterChange(selected) {
      this.selected = selected
      this.$emit('selection-change', selected)
      this.itemCountFiltered = selected.length
    },
    customFilter(value, query) {
      return (
        value != null &&
        query != null &&
        typeof value === 'string' &&
        value.toString().indexOf(query) !== -1
      )
    },

    rowClick(event, value) {
      const item = toRaw(value.item.raw)
      this.$emit('edit-item', item)
    },
    addItem() {
      this.$emit('add-item')
    },
    getDefaultColor(defaultgroup) {
      return defaultgroup ? 'green' : ''
    },
    deleteItem(item) {
      this.$emit('delete-item', item)
    },
    deleteItems(items) {
      items.forEach((item) => this.deleteItem({ id: item }))
      this.selected = []
    },
    updateItems() {
      this.$emit('update-items')
    }
  }
})
</script>
