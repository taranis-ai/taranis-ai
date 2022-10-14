<template>
  <v-data-table
    :headers="headers"
    :items="items"
    class="elevation-1"
    hide-default-footer
  >
  <template v-slot:[`item.default`]="{ item }">
    <v-chip :color="getDefaultColor(item.default)" dark>
      {{ item.default }}
    </v-chip>
  </template>
  <template v-slot:[`item.actions`]="{ item }">
  <v-icon
    small
    class="mr-2"
    @click="editItem(item)"
  >
    mdi-pencil
  </v-icon>
  <v-icon
    small
    @click="deleteItem(item)"
  >
    mdi-delete
  </v-icon>
  </template>
  <template v-slot:no-data>
    <v-btn
      color="primary"
      @click="initialize"
    >
      Reset
    </v-btn>
  </template>
  </v-data-table>
</template>

<script>
export default {
  name: 'ConfigTable',
  props: {
    items: Array
  },
  computed: {
    headers () {
      var headers = (this.items.length > 0 ? Object.keys(this.items[0]).map(key => {
        return {
          text: key,
          value: key
        }
      }) : [])
      headers.push({
        text: 'Actions',
        value: 'actions',
        sortable: false
      })
      return headers
    }
  },
  methods: {
    getDefaultColor (defaultgroup) {
      return (defaultgroup ? 'green' : '')
    },
    deleteItem(item) {
      this.$emit('delete-item', item)
    },
    editItem(item) {
      this.$emit('edit-item', item)
    }
  }
}
</script>
