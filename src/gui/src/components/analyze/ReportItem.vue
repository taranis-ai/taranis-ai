<template>
  <v-card>
    <v-toolbar density="compact">
      <v-toolbar-title>{{ container_title }}</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-switch v-model="verticalView" label="Side-by-side"></v-switch>
      <v-switch
        v-if="edit"
        v-model="report_item.completed"
        label="Completed"
      ></v-switch>
      <v-btn
        prepend-icon="mdi-content-save"
        color="success"
        variant="flat"
        @click="saveReportItem"
      >
        {{ $t('button.save') }}
      </v-btn>
    </v-toolbar>
    <v-card-text>
      <v-row>
        <v-col
          :cols="verticalView ? 6 : 12"
          :class="verticalView ? 'taranis-ng-vertical-view' : ''"
        >
          <v-row no-gutters>
            <v-col v-if="edit" cols="12">
              <span class="caption">ID: {{ report_item.uuid }}</span>
            </v-col>
            <v-col cols="4" class="pr-3">
              <v-select
                v-model="report_type"
                :disabled="edit"
                item-title="title"
                item-value="id"
                :rules="required"
                :items="report_types"
                :label="$t('report_item.report_type')"
              />
            </v-col>
            <v-col cols="4" class="pr-3">
              <v-text-field
                v-model="report_item.title_prefix"
                :label="$t('report_item.title_prefix')"
                name="title_prefix"
              ></v-text-field>
            </v-col>
            <v-col cols="4" class="pr-3">
              <v-text-field
                v-model="report_item.title"
                :label="$t('report_item.title')"
                name="title"
                type="text"
                :rules="required"
              ></v-text-field>
            </v-col>
          </v-row>
          <v-row>
            <v-col v-if="report_type && edit" cols="12" class="pa-0 ma-0">
              <v-expansion-panels
                v-for="attribute_group in report_type.attribute_groups"
                :key="attribute_group.id"
                class="mb-1"
                multiple
              >
                <v-expansion-panel>
                  <v-expansion-panel-title
                    color="primary--text"
                    class="body-1 text-uppercase pa-3"
                  >
                    {{ attribute_group.title }}
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <attribute-item
                      v-for="attribute_item in attributes[attribute_group.id]"
                      :key="attribute_item.id"
                      :read-only="!edit"
                      :attribute-item="attribute_item"
                      :value="attribute_values[attribute_item.id]"
                      @input="updateAttributeValues(attribute_item.id, $event)"
                    />
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-col>
          </v-row>
        </v-col>
        <v-col
          :cols="verticalView ? 6 : 12"
          class="pa-5 taranis-ng-vertical-view"
        >
          <card-story
            v-for="newsItem in report_item.news_item_aggregates"
            :key="newsItem.id"
            :story="newsItem"
          ></card-story>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script>
import { createReportItem, updateReportItem } from '@/api/analyze'
import AttributeItem from '@/components/analyze/AttributeItem.vue'
import CardStory from '@/components/assess/CardStory.vue'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { notifyFailure } from '@/utils/helpers'
import { mapActions, mapState } from 'pinia'
import { notifySuccess } from '@/utils/helpers'

export default {
  name: 'ReportItem',
  components: {
    AttributeItem,
    CardStory
  },
  props: {
    reportItemProp: { type: Object, required: true },
    edit: { type: Boolean, default: false }
  },
  emits: ['reportcreated'],
  data: function () {
    return {
      verticalView: this.edit,
      expand_panel_groups: [],
      selected_report_type: null,
      report_types: [],
      report_types_selection: [],
      attributes: {},
      report_item: this.reportItemProp,
      required: [(v) => !!v || 'Required']
    }
  },
  computed: {
    ...mapState(useAnalyzeStore, ['report_item_types']),
    attribute_values() {
      return this.report_item.attributes.reduce((acc, attr) => {
        acc[attr.attribute_group_item_id] = attr.value
        return acc
      }, {})
    },
    report_type: {
      get() {
        return this.selected_report_type
      },
      set(value) {
        this.updateSelectedReportType(value)
      }
    },
    container_title() {
      return this.edit
        ? `${this.$t('button.edit')} report item - ${this.report_item.title}`
        : `${this.$t('button.add_new')} report item`
    }
  },
  mounted() {
    console.debug(`Loaded REPORT ITEM ${this.report_item.id}`)

    this.loadReportTypes().then(() => {
      this.report_types = this.report_item_types.items
      if (this.report_item.report_item_type_id) {
        this.updateSelectedReportType(this.report_item.report_item_type_id)
      }
    })
  },
  methods: {
    ...mapActions(useAnalyzeStore, ['loadReportTypes']),

    updateSelectedReportType(value) {
      this.selected_report_type = this.report_types.find(
        (report_type) => report_type.id === value
      )
      console.debug('Selected report type', this.selected_report_type)
      this.report_item.report_item_type_id = value
      if (!this.selected_report_type) {
        return
      }
      this.attributes = this.extractAttributes(
        this.selected_report_type.attribute_groups
      )

      if (this.report_item.attributes.length > 0) {
        return
      }
      this.report_item.attributes =
        this.selected_report_type.attribute_groups.flatMap((group) =>
          group.attribute_group_items.map((item) => ({
            attribute_group_item_id: item.id,
            value: ''
          }))
        )
    },

    extractAttributes(attribute_groups) {
      const result = {}
      for (const group of attribute_groups) {
        const items = group.attribute_group_items.map((item) => ({
          ...item.attribute,
          title: item.title,
          id: item.id
        }))
        result[group.id] = items.reduce((acc, item) => {
          acc[item.id] = item
          return acc
        }, {})
      }
      return result
    },

    updateAttributeValues(key, values) {
      const attribute = this.report_item.attributes.find(
        (attr) => attr.attribute_group_item_id === parseInt(key)
      )
      if (attribute) {
        attribute.value = values
      }
    },

    saveReportItem() {
      if (this.edit) {
        updateReportItem(this.report_item.id, this.report_item)
          .then((response) => {
            notifySuccess(`Report with ID ${response.data} updated`)
          })
          .catch(() => {
            notifyFailure('Failed to update report item')
          })
      } else {
        createReportItem(this.report_item)
          .then((response) => {
            this.$router.push('/report/' + response.data)
            this.$emit('reportcreated', response.data)
            notifySuccess(`Report with ID ${response.data} created`)
            this.report_item.id = response.data
          })
          .catch(() => {
            notifyFailure('Failed to create report item')
          })
      }
    }
  }
}
</script>
