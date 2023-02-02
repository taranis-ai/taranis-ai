<template>
  <v-container>
    <v-app-bar :elevation="2" app class="mt-12">
      <v-app-bar-title>{{ container_title }}</v-app-bar-title>
      <v-spacer></v-spacer>
      <v-switch v-model="verticalView" label="Side-by-side view"></v-switch>
      <div v-if="edit">
        <v-switch
          v-if="edit"
          v-model="report_item.completed"
          label="Completed"
        ></v-switch>
      </div>
      <v-btn color="success" class="mr-2" @click="saveReportItem">
        <v-icon left>mdi-content-save</v-icon>
        <span>{{ $t('report_item.save') }}</span>
      </v-btn>
    </v-app-bar>

    <v-card>
      <v-row>
        <v-col
          :cols="verticalView ? 6 : 12"
          :class="verticalView ? 'taranis-ng-vertical-view' : ''"
        >
          <v-row no-gutters>
            <v-col cols="12" v-if="edit">
              <span class="caption">ID: {{ report_item.uuid }}</span>
            </v-col>
            <v-col cols="4" class="pr-3">
              <v-select
                :disabled="edit"
                v-model="report_type"
                item-text="title"
                item-value="id"
                :items="report_types"
                :label="$t('report_item.report_type')"
              />
            </v-col>
            <v-col cols="4" class="pr-3">
              <v-text-field
                :label="$t('report_item.title_prefix')"
                name="title_prefix"
                v-model="report_item.title_prefix"
              ></v-text-field>
            </v-col>
            <v-col cols="4" class="pr-3">
              <v-text-field
                :label="$t('report_item.title')"
                name="title"
                type="text"
                v-model="report_item.title"
                v-validate="'required'"
                :error-messages="errors.collect('title')"
              ></v-text-field>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" class="pa-0 ma-0" v-if="report_type">
              <v-expansion-panels
                class="mb-1"
                v-for="attribute_group in report_type.attribute_groups"
                :key="attribute_group.id"
                multiple
              >
                <v-expansion-panel>
                  <v-expansion-panel-header
                    color="primary--text"
                    class="body-1 text-uppercase pa-3"
                  >
                    {{ attribute_group.title }}
                  </v-expansion-panel-header>
                  <v-expansion-panel-content>
                    <attribute-item
                      :read_only="!edit"
                      v-for="attribute_item in attributes[attribute_group.id]"
                      :attribute_item="attribute_item"
                      :key="attribute_item.id"
                      v-model="values[attribute_item.id]"
                    />
                    <!-- v-model="report_item.attributes.find(attr => attr.attribute_group_item_id === attribute_item.id).value" -->
                  </v-expansion-panel-content>
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
    </v-card>
  </v-container>
</template>

<script>
import {
  createReportItem,
  updateReportItem
  //   lockReportItem,
  //   unlockReportItem,
  //   holdLockReportItem,
  //   getReportItem,
  //   getReportItemData,
  //   getReportItemLocks
} from '@/api/analyze'

import AttributeItem from '@/components/analyze/AttributeItem'
import CardStory from '@/components/assess/CardStory'

import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'ReportItem',
  props: {
    report_item_prop: Object,
    edit: { type: Boolean, default: false }
  },
  emits: ['reportcreated'],
  components: {
    AttributeItem,
    CardStory
  },
  data: () => ({
    verticalView: true,
    expand_panel_groups: [],
    modify: true,
    selected_report_type: null,
    report_types: [],
    report_types_selection: [],
    attributes: {},
    values: {}
  }),
  computed: {
    report_item() {
      return this.report_item_prop
    },
    report_type: {
      get() {
        return this.selected_report_type
      },
      set(value) {
        this.selected_report_type = this.report_types.find(
          (report_type) => report_type.id === value
        )
        this.report_item.report_item_type_id = value
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
      }
    },
    container_title() {
      return this.edit
        ? this.$t('report_item.edit')
        : this.$t('report_item.add_new')
    }
  },
  methods: {
    ...mapGetters(['getUserId']),
    ...mapGetters('analyze', ['getReportTypes']),
    ...mapActions('analyze', ['loadReportTypes']),

    extractAttributes(attribute_groups) {
      const result = {}
      for (const group of attribute_groups) {
        const items = group.attribute_group_items.map((item) => ({
          ...item.attribute,
          title: item.title
        }))
        result[group.id] = items.reduce((acc, item) => {
          acc[item.id] = item
          return acc
        }, {})
      }
      return result
    },

    saveReportItem() {
      if (this.edit) {
        updateReportItem(this.report_item.id, this.report_item)
      } else {
        createReportItem(this.report_item).then((response) => {
          this.$router.push('/report/' + response.data)
          this.$emit('reportcreated', response.data)
        })
      }
    }
  },
  mounted() {
    this.loadReportTypes().then(() => {
      this.report_types = this.getReportTypes().items
      this.report_type = this.report_item.report_item_type_id
      console.debug('REPORT ITEM')
      console.debug(this.report_item)
      console.debug('Report Types')
      console.debug(this.report_types)
      console.debug('Report Type')
      console.debug(this.report_type)
    })
  },
  beforeDestroy() {}
}
</script>
