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
  </div>
</template>

<script>
import ConfigTable from '../../components/config/ConfigTable'
import {
  deleteOSINTSource,
  createNewOSINTSource,
  updateOSINTSource,
  exportOSINTSources,
  importOSINTSources
} from '@/api/config'
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'OSINTSources',
  components: {
    ConfigTable
  },
  data: () => ({
    osint_sources: [],
    selected: []
  }),
  methods: {
    ...mapActions('config', ['loadOSINTSources']),
    ...mapGetters('config', ['getOSINTSources']),
    // ...mapGetters('assess', ['getOSINTSources']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadOSINTSources().then(() => {
        const sources = this.getOSINTSources()
        this.osint_sources = sources.items
        this.updateItemCount({
          total: sources.total_count,
          filtered: sources.length
        })
      })
    },
    importSources() {
      importOSINTSources(this.selected).then(() => {
        this.message = `Successfully imported ${this.selected.length} sources`
        this.dialog = true
        this.updateData()
      })
    },
    exportSources() {
      exportOSINTSources(this.selected)
    },
    deleteItem(item) {
      if (!item.default) {
        deleteOSINTSource(item).then(() => {
          this.message = `Successfully deleted ${item.name}`
          this.dialog = true
          this.$root.$emit('notification', {
            type: 'success',
            loc: `Successfully deleted ${item.name}`
          })
          this.updateData()
        })
      }
    },
    addItem(item) {
      createNewOSINTSource(item).then(() => {
        this.$root.$emit('notification', {
          type: 'success',
          loc: `Successfully created ${item.name}`
        })
        this.updateData()
      })
    },
    editItem(item) {
      updateOSINTSource(item).then(() => {
        this.$root.$emit('notification', {
          type: 'success',
          loc: `Successfully updated ${item.name}`
        })
        this.updateData()
      })
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {
  }
}
</script>
