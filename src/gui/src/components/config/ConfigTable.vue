<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
      <v-data-table
        ref="configTable"
        v-model="selection"
        @update:search="emitSearchChange"
        @current-items="emitFilterChange"
        :headers="headers"
        :items="items"
        :search="search"
        :group-by="groupByItem"
        :sort-by="sortByItem"
        class="elevation-1"
        :hide-default-footer="items.length < 10"
        show-select
        @click:row="rowClick"
      >
      <template v-slot:[`top`]>
        <v-card>
          <v-card-title>
            <v-text-field
              v-model="search"
              append-icon="mdi-magnify"
              label="Search"
              single-line
              class="mr-8"
              hide-details
            ></v-text-field>
            <v-btn
              color="error"
              dark
              class="ml-8"
              @click="deleteItems(selected)"
              v-if="selected.length > 0"
            >
              Delete {{ selected.length }}
            </v-btn>
            <v-btn
              color="primary"
              dark
              class="ml-8"
              @click="addItem"
              v-if="addButton"
            >
              New Item
            </v-btn>
            <slot name="titlebar"></slot>
          </v-card-title>
         </v-card>
      </template>
        <template v-slot:[`group.header`]="{ items }">
          <th :colspan="headers.length" class="text-left">
            {{ items[0].collector_type }}
          </th>
        </template>

        <template v-slot:[`header.tag`]="{}"></template>
        <template v-slot:[`header.actions`]="{}"></template>

        <template v-slot:[`item.default`]="{ item }">
          <v-chip :color="getDefaultColor(item.default)" dark>
            {{ item.default }}
          </v-chip>
        </template>

        <template v-slot:[`item.tag`]="{ item }">
          <v-icon small class="mr-1">
            {{ item.tag }}
          </v-icon>
        </template>
        <template v-slot:[`item.actions`]="{ item }">
          <div class="d-inline-flex">
            <slot name="actionColumn"></slot>
            <v-icon color="red darken-4" @click.stop="deleteItem(item)"> mdi-delete </v-icon>
          </div>
        </template>
        <template v-slot:no-data>
          <v-btn color="primary" @click.stop="updateItems()">
            <v-icon class="mr-1">mdi-refresh</v-icon>
            Refresh
          </v-btn>
        </template>
      </v-data-table>
  </v-container>
</template>

<script>
import { mapActions } from 'vuex'
export default {
  name: 'ConfigTable',
  components: {},
  emits: ['delete-item', 'edit-item', 'add-item', 'selection-change', 'search-change'],
  props: {
    items: {
      type: Array,
      required: true
    },
    addButton: {
      type: Boolean,
      default: false
    },
    groupByItem: {
      type: String,
      default: null
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
    }
  },
  data: () => ({
    search: '',
    selected: []
  }),
  computed: {
    selection: {
      get() {
        return this.selected
      },
      set(value) {
        this.selected = value
        this.$emit('selection-change', this.selected)
      }
    },
    headers() {
      var actionHeader = {
        text: 'Actions',
        value: 'actions',
        sortable: false,
        width: '30px'
      }
      var headers = []
      if (this.headerFilter.length > 0) {
        headers = this.headerFilter.map((key) => this.headerTransform(key))
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
    ...mapActions(['updateItemCountFiltered']),

    headerTransform(key) {
      if (key === 'tag') {
        return {
          text: key,
          value: key,
          sortable: false,
          width: '15px'
        }
      }
      return { text: key, value: key }
    },
    emitFilterChange(e) {
      this.updateItemCountFiltered(e.length)
    },
    emitSearchChange() {
      this.$emit('search-change', this.search)
    },
    rowClick(item) {
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
      items.forEach((item) => this.deleteItem(item))
    },
    updateItems() {
      this.$emit('update-items')
    }
  }
}
</script>
