<template>
  <div>
    <ConfigTable
      :addButton="true"
      :items="osint_sources"
      :headerFilter="['name', 'description', 'id']"
      groupByItem="collector_type"
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
import { deleteOSINTSource, createNewOSINTSource, updateOSINTSource } from '@/api/config'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'OSINTSources',
  components: {
    ConfigTable
  },
  data: () => ({
    osint_sources: [],
    dialog: false,
    message: ''
  }),
  methods: {
    ...mapActions('config', ['loadOSINTSources']),
    ...mapGetters('config', ['getOSINTSources']),
    // ...mapGetters('assess', ['getOSINTSources']),
    ...mapActions(['updateItemCount']),
    deleteItem(item) {
      if (!item.default) {
        deleteOSINTSource(item)
      }
    },
    addItem(item) {
      createNewOSINTSource(item)
      this.dialog = true
    },
    editItem(item) {
      updateOSINTSource(item)
      this.message = `Successfully updated ${item.name} - ${item.id}`
    }
  },
  mounted () {
    this.loadOSINTSources().then(() => {
      const sources = this.getOSINTSources()
      this.osint_sources = sources.items
      this.updateItemCount({ total: sources.total_count, filtered: sources.length })
    })
  },
  beforeDestroy () {
    this.$root.$off('delete-item')
  }
}
</script>
