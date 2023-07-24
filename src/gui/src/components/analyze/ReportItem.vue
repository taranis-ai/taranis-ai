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
                v-model="report_item.report_item_type_id"
                :disabled="edit"
                item-title="title"
                item-value="id"
                :rules="required"
                :items="report_item_types.items"
                :label="$t('report_item.report_type')"
              />
            </v-col>
            <v-col cols="4" class="pr-3">
              <v-text-field
                v-model="report_item.title_prefix"
                :label="$t('report_item.title_prefix')"
                name="title_prefix"
              />
            </v-col>
            <v-col cols="4" class="pr-3">
              <v-text-field
                v-model="report_item.title"
                :label="$t('report_item.title')"
                name="title"
                type="text"
                :rules="required"
              />
            </v-col>
          </v-row>
          <v-row>
            <v-col v-if="edit && report_type" cols="12" class="pa-0 ma-0">
              <v-expansion-panels
                v-for="attribute_group in report_type.attribute_groups"
                :key="attribute_group.id"
                class="mb-1"
                multiple
              >
                <v-expansion-panel :title="attribute_group.title">
                  <v-expansion-panel-text>
                    <attribute-item
                      v-for="attribute_item in attribute_group.attribute_group_items"
                      :key="attribute_item.id"
                      :read-only="!edit"
                      :attribute-item="attribute_item"
                      :value="attribute_values[attribute_item.id]"
                      @update:value="
                        updateAttributeValues(attribute_item.id, $event)
                      "
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
            v-for="story in report_item.news_item_aggregates"
            :key="story.id"
            :story="story"
            :report-view="true"
            @remove-from-report="removeFromReport(story.id)"
          ></card-story>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { createReportItem, updateReportItem } from '@/api/analyze'
import AttributeItem from '@/components/analyze/AttributeItem.vue'
import CardStory from '@/components/assess/CardStory.vue'
import { notifyFailure, notifySuccess } from '@/utils/helpers'
import { setAggregatesToReportItem } from '@/api/analyze'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'

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
  setup(props, { emit }) {
    const { t } = useI18n()
    const router = useRouter()
    const store = useAnalyzeStore()

    const verticalView = ref(props.edit)
    const expand_panel_groups = ref([])
    const attributes = ref({})
    const report_item = ref(props.reportItemProp)
    const required = ref([(v) => !!v || 'Required'])

    const { report_item_types } = storeToRefs(store)
    const attribute_values = computed(() =>
      report_item.value.attributes.reduce((acc, attr) => {
        acc[attr.attribute_group_item_id] = attr.value
        return acc
      }, {})
    )

    const report_type = computed(() =>
      report_item_types.value.items.find(
        (item) => item.id === report_item.value.report_item_type_id
      )
    )

    const container_title = computed(() =>
      props.edit
        ? `${t('button.edit')} report item - ${report_item.value.title}`
        : `${t('button.add_new')} report item`
    )

    onMounted(() => {
      console.debug(`Loaded REPORT ITEM ${report_item.value.id}`)
      store.loadReportTypes()
    })

    const updateAttributeValues = (key, values) => {
      const attribute = report_item.value.attributes.find(
        (attr) => attr.attribute_group_item_id === parseInt(key)
      )
      if (attribute) {
        attribute.value = values
      }
    }

    const saveReportItem = () => {
      if (props.edit) {
        updateReportItem(report_item.value.id, report_item.value)
          .then((response) => {
            notifySuccess(`Report with ID ${response.data} updated`)
          })
          .catch(() => {
            notifyFailure('Failed to update report item')
          })
      } else {
        createReportItem(report_item.value)
          .then((response) => {
            router.push('/report/' + response.data)
            emit('reportcreated', response.data)
            notifySuccess(`Report with ID ${response.data} created`)
            report_item.value.id = response.data
          })
          .catch(() => {
            notifyFailure('Failed to create report item')
          })
      }
    }

    const removeFromReport = (story_id) => {
      console.debug(`Removing story ${story_id} from report`)
      report_item.value.news_item_aggregates =
        report_item.value.news_item_aggregates.filter(
          (story) => story.id !== story_id
        )
      const aggregate_ids = report_item.value.news_item_aggregates.map(
        (story) => story.id
      )
      setAggregatesToReportItem(report_item.value.id, aggregate_ids)
        .then(() => {
          notifySuccess('Removed from report')
        })
        .catch(() => {
          notifyFailure('Failed to remove from report')
        })
    }

    return {
      verticalView,
      expand_panel_groups,
      attributes,
      report_item,
      required,
      report_item_types,
      attribute_values,
      report_type,
      container_title,
      updateAttributeValues,
      saveReportItem,
      removeFromReport
    }
  }
}
</script>
