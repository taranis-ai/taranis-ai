<template>
  <v-row>
    <v-btn
      text
      small
      :title="$t('report_item.tooltip.enum_selector')"
      @click="show"
    >
      <v-icon>mdi-feature-search-outline</v-icon>
    </v-btn>
    <v-dialog v-model="visible">
      <v-card>
        <v-toolbar>
          <v-btn icon="mdi-close" @click="cancel"> </v-btn>
          <v-toolbar-title>{{ $t('attribute.select_enum') }}</v-toolbar-title>
        </v-toolbar>

        <v-card>
          <v-card-text>
            <v-data-table
              v-model:page="current_page"
              :headers="headers"
              :items="attribute_enums"
              :server-items-length="attribute_enums_total_count"
              :items-per-page="25"
              @update:options="updateOptions"
              @click:row="clickRow"
            >
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-card>
    </v-dialog>
  </v-row>
</template>

<script>
import { getAttributeEnums } from '@/api/analyze'
import { getCPEAttributeEnums } from '@/api/assets'

export default {
  name: 'EnumSelector',
  props: {
    attributeId: {
      type: Number,
      required: true
    },
    cpeOnly: {
      type: Boolean,
      default: true
    }
  },
  emits: ['enum-selected'],
  data: () => ({
    visible: false,
    search: '',
    headers: [
      {
        text: 'Value',
        align: 'left',
        sortable: false,
        value: 'value'
      },
      { text: 'Description', value: 'description', sortable: false }
    ],
    current_page: 1,
    current_page_size: 25,
    attribute_enums: [],
    attribute_enums_total_count: 0
  }),
  methods: {
    show() {
      this.updateAttributeEnums()
      this.visible = true
    },

    cancel() {
      this.visible = false
    },

    clickRow(event, row) {
      this.$emit('enum-selected', {
        value: row.item.value
      })
      this.visible = false
    },

    updateAttributeEnums() {
      if (this.cpeOnly === true) {
        getCPEAttributeEnums({
          search: this.search,
          offset: (this.current_page - 1) * this.current_page_size,
          limit: this.current_page_size
        }).then((response) => {
          this.processResponse(response)
        })
      } else {
        getAttributeEnums({
          attribute_id: this.attributeId,
          search: this.search,
          offset: (this.current_page - 1) * this.current_page_size,
          limit: this.current_page_size
        }).then((response) => {
          this.processResponse(response)
        })
      }
    },

    processResponse(response) {
      this.attribute_enums = []
      this.attribute_enums_total_count = response.data.total_count
      for (let i = 0; i < response.data.items.length; i++) {
        this.attribute_enums.push(response.data.items[i])
      }
    },

    updateOptions(options) {
      this.current_page = options.page
      this.current_page_size = options.itemsPerPage
      this.updateAttributeEnums()
    }
  }
}
</script>
