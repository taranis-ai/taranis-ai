<template>
  <v-row>
    <v-dialog v-model="dialog">
      <v-card>
        <v-toolbar>
          <v-btn icon="mdi-close" @click="close"> </v-btn>
          <v-toolbar-title>{{ $t('report_item.select') }}</v-toolbar-title>
          <v-spacer></v-spacer>
          <v-btn text dark @click="add">
            <v-icon left>mdi-plus-box</v-icon>
            <span>{{ $t('report_item.add') }}</span>
          </v-btn>
        </v-toolbar>
        <v-container fluid class="pa-0 ma-0">
          <div :style="UI.STYLE.sticky_filter_toolbar">
            <ToolbarFilterAnalyze
              ref="toolbarFilter"
              publish_selector
              total_count_title="analyze.total_count"
              @update-report-items-filter="updateFilter"
            />
          </div>

          <ContentDataAnalyze
            ref="contentData"
            publish_selector
            :selection="selector_values"
            class="item-selector"
            card-item="CardAnalyze"
            @show-report-item-detail="showReportItemDetail"
            @new-data-loaded="newDataLoaded"
          />
        </v-container>
      </v-card>
    </v-dialog>

    <v-spacer style="height: 8px"></v-spacer>

    <component
      :is="cardLayout()"
      v-for="sel_value in selector_values"
      :key="sel_value.id"
      publish_selector
      class="item-selector"
      :card="sel_value"
      @show-report-item-detail="showReportItemDetail"
      @remove-report-item-from-selector="removeReportItemFromSelector"
    />
  </v-row>
</template>

<script>
import CardAnalyze from '../analyze/CardAnalyze'
import ToolbarFilterAnalyze from '@/components/analyze/ToolbarFilterAnalyze.vue'
import AuthMixin from '@/services/auth/auth_mixin'
import { mapActions } from 'pinia'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'

export default {
  name: 'ReportItemSelector',
  components: {
    ToolbarFilterAnalyze,
    CardAnalyze
  },
  mixins: [AuthMixin],
  props: {
    values: {
      type: Array,
      required: true
    },
    modify: {
      type: Boolean
    },
    edit: {
      type: Boolean
    }
  },
  data: () => ({
    dialog: false,
    value: '',
    selector_values: this.values
  }),
  computed: {
    ...mapActions(useAnalyzeStore, ['selection_report'])
  },
  methods: {
    ...mapActions(useAnalyzeStore, ['setMultiSelectReport']),
    newDataLoaded(count) {
      this.$refs.toolbarFilter.updateDataCount(count)
    },

    updateFilter(filter) {
      this.$refs.contentData.updateFilter(filter)
    },

    showReportItemDetail(report_item) {
      this.$refs.reportItemDialog.showDetail(report_item)
    },

    removeReportItemFromSelector(report_item) {
      const i = this.selector_values.indexOf(report_item)
      this.selector_values.splice(i, 1)
    },

    cardLayout: function () {
      return 'CardAnalyze'
    },

    openSelector() {
      this.setMultiSelectReport(true)
      this.dialog = true
    },

    add() {
      const selection = this.selection_report
      for (let i = 0; i < selection.length; i++) {
        let found = false
        for (let j = 0; j < this.selector_values.length; j++) {
          if (this.selector_values[j].id === selection[i].item.id) {
            found = true
            break
          }
        }

        if (found === false) {
          selection[i].item.tag = 'mdi-file-table-outline'
        }
        this.selector_values.push(selection[i].item)
      }

      this.close()
    },

    close() {
      this.setMultiSelectReport(false)
      this.dialog = false
    }
  }
}
</script>
