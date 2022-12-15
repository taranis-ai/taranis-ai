<template>
  <div>
  <ConfigTable
    :addButton="true"
    :items="node_items"
    :headerFilter="['tag', 'name', 'title', 'description', 'id']"
    @delete-item="deleteItem"
    @edit-item="editItem"
    @add-item="addItem"
  />
  <v-snackbar v-model="message" rounded="pill" color="success" centered>
    {{ message }}
  </v-snackbar>
</div>
</template>

<script>
import ConfigTable from '../../components/config/ConfigTable'
import { deleteNode, createNode, updateNode } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'Nodes',
  components: {
    ConfigTable
  },
  methods: {
    ...mapActions('config', [
      'loadNodes'
    ]),
    ...mapActions(['updateItemCount']),
    ...mapGetters('config', [
      'getNodes'
    ]),
    deleteItem(item) {
      deleteNode(item)
    },
    addItem(item) {
      createNode(item)
      this.message = `Successfully added ${item.name}`
    },
    editItem(item) {
      updateNode(item)
      this.message = `Successfully updated ${item.name} - ${item.id}`
    }
  },
  data: () => ({
    node_items: [],
    message: ''
  }),
  mounted () {
    var filter = { search: '' }
    this.loadNodes(filter).then(() => {
      var nodes = this.getNodes()
      this.node_items = nodes.items
      this.updateItemCount({ total: nodes.total_count, filtered: nodes.length })
    })
  },
  beforeDestroy () {
    this.$root.$off('delete-item')
  }
}
</script>
