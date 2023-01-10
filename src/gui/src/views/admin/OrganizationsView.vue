<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items.sync="organizations"
      :headerFilter="['tag', 'id', 'name', 'description']"
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
import { deleteOrganization, createOrganization, updateOrganization } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess } from '@/utils/helpers'

export default {
  name: 'Organizations',
  components: {
    ConfigTable
  },
  data: () => ({
    organizations: []
  }),
  methods: {
    ...mapActions('config', ['loadOrganizations']),
    ...mapGetters('config', ['getOrganizations']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadOrganizations().then(() => {
        const sources = this.getOrganizations()
        this.organizations = sources.items
        this.updateItemCount({ total: sources.total_count, filtered: sources.length })
      })
    },
    deleteItem(item) {
      if (!item.default) {
        deleteOrganization(item).then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        })
      }
    },
    addItem(item) {
      createOrganization(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      })
    },
    editItem(item) {
      updateOrganization(item).then(() => {
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
