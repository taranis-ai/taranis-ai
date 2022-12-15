<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <v-col cols="12">
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
            color="primary"
            dark
            class="ml-8"
            @click="addItem"
            v-if="addButton"
          >
            New Item
          </v-btn>
        </v-card-title>
      <v-data-table
        ref="configTable"
        :headers="headers"
        :items="items"
        :search="search"
        :group-by="groupByItem"
        :sort-by="sortByItem"
        class="elevation-1"
        hide-default-footer
        @click:row="rowClick"
      >
        <template v-slot:[`group.header`]="{ items }">
          <th :colspan="headers.length" class="text-left">
            {{ items[0].collector_type }}
          </th>
        </template>

        <template v-slot:[`item.default`]="{ item }">
          <v-chip :color="getDefaultColor(item.default)" dark>
            {{ item.default }}
          </v-chip>
        </template>

        <template v-slot:[`item.tag`]="{ item }">
          <v-icon small class="mr-2">
            {{ item.tag }}
          </v-icon>
        </template>
        <template v-slot:[`item.actions`]="{ item }">
          <v-icon small class="mr-2" @click.stop="rowClick(item)">
            mdi-pencil
          </v-icon>
          <v-icon small @click.stop="deleteItem(item)"> mdi-delete </v-icon>
        </template>
        <template v-slot:no-data>
          <v-btn color="primary">Reset</v-btn>
        </template>
      </v-data-table>
      </v-card>
    </v-col>
    <v-row>
      <v-col cols="12">
        <EditConfig
          v-if="formData && Object.keys(formData).length > 0"
          :configData="formData"
          @submit="handleSubmit"
        ></EditConfig>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { emptyValues } from '@/utils/helpers'
import EditConfig from '../../components/config/EditConfig'

export default {
  name: 'ConfigTable',
  components: {
    EditConfig
  },
  emits: ['delete-item', 'edit-item', 'add-item'],
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
    edit: false,
    formData: {},
    search: ''
  }),
  computed: {
    headers() {
      var actionHeader = {
        text: 'Actions',
        value: 'actions',
        sortable: false
      }
      var headers = []
      if (this.headerFilter.length > 0) {
        headers = this.headerFilter.map((item) => ({ text: item, value: item }))
      } else if (this.items.length > 0) {
        headers = Object.keys(this.items[0]).map((key) => {
          return {
            text: key,
            value: key
          }
        })
      }
      if (this.actionColumn) {
        headers.push(actionHeader)
      }
      return headers
    }
  },
  methods: {
    handleSubmit(submittedData) {
      console.log(submittedData)
      if (this.edit) {
        this.$emit('edit-item', submittedData)
      } else {
        this.$emit('add-item', submittedData)
      }
    },
    getDefaultColor(defaultgroup) {
      return defaultgroup ? 'green' : ''
    },
    deleteItem(item) {
      this.$emit('delete-item', item)
    },
    addItem() {
      this.edit = false
      var onlyKeys = emptyValues(this.items[0])
      this.formData = onlyKeys
    },
    rowClick(item, event) {
      this.formData = item
      this.edit = true
    }
  }
}
</script>
