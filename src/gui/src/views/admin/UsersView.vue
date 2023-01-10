<template>
  <ConfigTable
    :addButton="true"
    :items.sync="users"
    :headerFilter="['tag', 'id', 'name', 'username']"
    sortByItem="id"
    :actionColumn=true
    @delete-item="deleteItem"
    @edit-item="editItem"
    @add-item="addItem"
  />
</template>

<script>
import ConfigTable from '../../components/config/ConfigTable'
import { deleteUser, createUser, updateUser } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'UsersView',
  components: {
    ConfigTable
  },
  data: () => ({
    users: []
  }),
  methods: {
    ...mapActions('config', ['loadUsers']),
    ...mapGetters('config', ['getUsers']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadUsers().then(() => {
        const sources = this.getUsers()
        this.users = sources.items
        this.updateItemCount({ total: sources.total_count, filtered: sources.length })
      })
    },
    deleteItem(item) {
      if (!item.default) {
        deleteUser(item).then(() => {
          this.message = `Successfully deleted ${item.name}`
          this.dialog = true
          this.$root.$emit('notification',
            {
              type: 'success',
              loc: `Successfully deleted ${item.name}`
            })
          this.updateData()
        })
      }
    },
    addItem(item) {
      createUser(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: `Successfully added ${item.name}`
          })
        this.updateData()
      })
    },
    editItem(item) {
      updateUser(item).then(() => {
        this.$root.$emit('notification',
          {
            type: 'success',
            loc: `Successfully updated ${item.name}`
          })
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
