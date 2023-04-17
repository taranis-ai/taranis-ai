<template>
  <DataTable
    :addButton="true"
    :items.sync="report_items"
    :headerFilter="['tag', 'title', 'created']"
    sortByItem="id"
    :actionColumn="true"
    @delete-item="deleteItem"
    @edit-item="editItem"
    @add-item="addItem"
    @update-items="updateData"
    @selection-change="selectionChange"
  >
    <template v-slot:actionColumn>
      <v-tooltip left>
        <template v-slot:activator="{ on }">
          <v-icon v-on="on" color="secondary" @click.stop="createProduct(item)">
            mdi-file
          </v-icon>
        </template>
        <span>Create Product</span>
      </v-tooltip>
    </template>
  </DataTable>
</template>

<script>
import DataTable from '@/components/common/DataTable'
import {
  deleteReportItem,
  createReportItem,
  updateReportItem
} from '@/api/analyze'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

export default {
  name: 'Analyze',
  components: {
    DataTable
  },
  data: () => ({
    report_items: [],
    report_types: {},
    selected: [],
    report_item: {
      report_item_type_id: null,
      title_prefix: '',
      title: ''
    }
  }),
  methods: {
    ...mapActions('analyze', ['loadReportItems', 'loadReportTypes']),
    ...mapGetters('analyze', ['getReportItems', 'getReportTypes']),
    ...mapActions(['updateItemCount']),
    updateData() {
      this.loadReportItems().then(() => {
        const sources = this.getReportItems()
        this.report_items = sources
        this.updateItemCount({
          total: sources.length,
          filtered: sources.length
        })
      })
      this.loadReportTypes().then(() => {
        this.report_types = this.getReportTypes().items
      })
    },
    addItem() {
      this.$router.push('/report/0')
    },
    editItem(item) {
      this.$router.push('/report/' + item.id)
    },
    handleSubmit(submittedData) {
      console.log(submittedData)
    },
    deleteItem(item) {
      deleteReportItem(item)
        .then(() => {
          notifySuccess(`Successfully deleted ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to delete ${item.name}`)
        })
    },
    createItem(item) {
      createReportItem(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    },
    updateItem(item) {
      updateReportItem(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          this.updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    },
    createProduct() {
      this.$router.push({ name: 'product', params: { id: null } })
    },
    selectionChange(selected) {
      this.selected = selected.map((item) => item.id)
    }
  },
  mounted() {
    this.updateData()
  },
  beforeDestroy() {}
}
</script>
