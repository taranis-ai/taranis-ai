<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items.sync="Nodes"
      :headerFilter="['tag', 'id', 'name', 'title', 'description']"
      sortByItem="id"
      :actionColumn=true
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
    />
  </div>
</template>

<script>
import ConfigTable from '../../components/config/ConfigTable'
import { deleteNode, createNode, updateNode } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess } from '@/utils/helpers'

export default {
  name: 'Nodes',
  components: {
    ConfigTable
  },
  data: () => ({
    nodes: []
  }),
  methods: {
    ...mapActions('config', ['loadNodes']),
    ...mapActions(['updateItemCount']),
    ...mapGetters('config', ['getNodes']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadNodes().then(() => {
        const sources = this.getNodes()
        this.nodes = sources.items
        this.updateItemCount({ total: sources.total_count, filtered: sources.length })
      })
    },
    deleteItem(item) {
      if (!item.default) {
        deleteNode(item).then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        })
      }
    },
    addItem(item) {
      createNode(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      })
    },
    editItem(item) {
      updateNode(item).then(() => {
        notifySuccess(`Successfully updated ${item.name}`)

        this.updateData()
      })
    }
  },
  mounted () {
    this.updateData()
  },
  beforeDestroy () {}
}
</script>
