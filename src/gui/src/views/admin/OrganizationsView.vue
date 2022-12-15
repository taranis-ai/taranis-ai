<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items="organizations"
      :headerFilter="['tag', 'id', 'name', 'description']"
      sortByItem="id"
      :actionColumn=true
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
import { deleteOrganization, createNewOrganization, updateOrganization } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'Organizations',
  components: {
    ConfigTable
  },
  data: () => ({
    organizations: [],
    dialog: false,
    message: ''
  }),
  methods: {
    ...mapActions('config', ['loadOrganizations']),
    ...mapGetters('config', ['getOrganizations']),
    ...mapActions(['updateItemCount']),
    deleteItem(item) {
      if (!item.default) {
        deleteOrganization(item)
      }
    },
    addItem(item) {
      createNewOrganization(item)
      this.dialog = true
    },
    editItem(item) {
      updateOrganization(item)
      this.message = `Successfully updated ${item.name} - ${item.id}`
    }
  },
  mounted () {
    this.loadOrganizations().then(() => {
      const sources = this.getOrganizations()
      this.organizations = sources.items
      this.updateItemCount({ total: sources.total_count, filtered: sources.length })
    })
  },
  beforeDestroy () {
    this.$root.$off('delete-item')
  }
}
</script>
