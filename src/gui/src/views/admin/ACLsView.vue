<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items.sync="acls"
      :headerFilter="['tag', 'id', 'name', 'username']"
      sortByItem="id"
      :actionColumn="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <NewACL
      v-if="showForm"
      :user_id.sync="userID"
    ></NewACL>
  </div>
</template>

<script>
import ConfigTable from '../../components/config/ConfigTable'
import NewACL from '../../components/config/user/NewACL'
import { deleteACLEntry, createACLEntry, updateACLEntry } from '@/api/config'
import { notifySuccess } from '@/utils/helpers'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'ACLsView',
  components: {
    ConfigTable,
    NewACL
  },
  data: () => ({
    acls: [],
    showForm: false,
    edit: false
  }),
  methods: {
    ...mapActions('config', ['loadACLEntries']),
    ...mapGetters('config', ['getACLEntries']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadACLEntries().then(() => {
        const sources = this.getACLEntries()
        this.acls = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
    },
    addItem() {
      this.userID = null
      this.showForm = true
    },
    editItem(item) {
      this.userID = item.id
      this.showForm = true
    },
    handleSubmit(submittedData) {
      if (this.showForm) {
        this.updateItem(submittedData)
      } else {
        this.createItem(submittedData)
      }
    },
    deleteItem(item) {
      deleteACLEntry(item).then(() => {
        notifySuccess(`Successfully deleted ${item.name}`)
        this.updateData()
      })
    },
    createItem(item) {
      createACLEntry(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        this.updateData()
      })
    },
    updateItem(item) {
      updateACLEntry(item).then(() => {
        notifySuccess(`Successfully updated ${item.name}`)
        this.updateData()
      })
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}

</script>
