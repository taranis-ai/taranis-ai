<template>
  <v-row v-bind="UI.DIALOG.ROW.WINDOW">
    <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="dialog">
      <v-card v-bind="UI.DIALOG.BASEMENT">
        <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
          <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="close">
            <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
          </v-btn>
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
              publish_selector
              total_count_title="analyze.total_count"
              @update-report-items-filter="updateFilter"
              ref="toolbarFilter"
            />
          </div>

          <ContentDataAnalyze
            publish_selector
            :selection="selector_values"
            class="item-selector"
            card-item="CardAnalyze"
            ref="contentData"
            @show-report-item-detail="showReportItemDetail"
            @new-data-loaded="newDataLoaded"
          />
        </v-container>
      </v-card>
    </v-dialog>

    <v-spacer style="height: 8px"></v-spacer>

    <NewReportItem ref="reportItemDialog" />

    <component
      publish_selector
      class="item-selector"
      v-bind:is="cardLayout()"
      v-for="value in selector_values"
      :card="value"
      :key="value.id"
      @show-report-item-detail="showReportItemDetail"
      @remove-report-item-from-selector="removeReportItemFromSelector"
    />
  </v-row>
</template>

<script>
import ContentDataAnalyze from '@/components/analyze/ContentDataAnalyze'
import ToolbarFilter from '@/components/common/ToolbarFilter'
import CardAnalyze from '../analyze/CardAnalyze'
import ToolbarFilterAnalyze from '@/components/analyze/ToolbarFilterAnalyze'
import NewReportItem from '@/components/analyze/NewReportItem'
import AuthMixin from '@/services/auth/auth_mixin'
import { mapGetters, mapActions } from 'vuex'

export default {
  name: 'ReportItemSelector',
  components: {
    ToolbarFilterAnalyze,
    ContentDataAnalyze,
    ToolbarFilter,
    CardAnalyze,
    NewReportItem
  },
  mixins: [AuthMixin],
  props: {
    values: Array,
    modify: Boolean,
    edit: Boolean
  },
  data: () => ({
    dialog: false,
    value: '',
    selector_values: this.values
  }),
  computed: {},
  methods: {
    ...mapGetters('analyze', [
      'getCurrentReportItemGroup',
      'getReportItems',
      'getSelectionReport'
    ]),
    ...mapActions('analyze', ['selectReport', 'multiSelectReport']),
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
      this.$store.dispatch('multiSelectReport', true)
      this.dialog = true
    },

    add() {
      const selection = this.getSelectionReport()
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
      this.$store.dispatch('multiSelectReport', false)
      this.dialog = false
    }
  }
}
</script>
