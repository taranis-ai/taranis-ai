<template>
  <v-card class="h-100">
    <v-toolbar density="compact">
      <v-toolbar-title :text="container_title" />
      <v-spacer />
      <v-switch
        v-model="verticalView"
        style="max-width: 250px"
        class="mr-4"
        label="Side-by-side"
        hide-details
        color="success"
        density="compact"
      />
      <v-switch
        v-if="edit"
        v-model="report_item.completed"
        style="max-width: 250px"
        hide-details
        label="Completed"
        color="success"
        density="compact"
      />
      <v-btn
        prepend-icon="mdi-content-save"
        color="success"
        variant="flat"
        class="ml-4"
        @click="saveReportItem"
      >
        {{ $t('button.save') }}
      </v-btn>
      <v-btn
        v-if="report_item.stories.length"
        prepend-icon="mdi-delete-outline"
        color="error"
        variant="flat"
        class="ml-4"
        @click="removeAllFromReport"
      >
        remove all stories
      </v-btn>
    </v-toolbar>
    <v-card-text>
      <v-form ref="form" @submit.prevent="saveReportItem">
        <v-row no-gutters>
          <v-col :cols="verticalView ? 6 : 12">
            <v-row no-gutters>
              <v-col v-if="edit" cols="12">
                <span class="caption">ID: {{ report_item.id }}</span>
              </v-col>
              <v-col cols="4" class="pr-3">
                <v-select
                  id="report_item_selector"
                  v-model="report_item.report_item_type_id"
                  :disabled="edit"
                  item-title="title"
                  item-value="id"
                  :rules="required"
                  no-data-text="No Report Types available - please create one under Admin > Report Types"
                  :items="report_item_types.items"
                  :label="$t('report_item.report_type')"
                />
              </v-col>
              <v-col cols="8" class="pr-3">
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
              <v-col v-if="edit" cols="12" class="pa-0 ma-0">
                <v-expansion-panels
                  v-for="(
                    attributes, attribute_group
                  ) in report_item.attributes"
                  :key="attribute_group"
                  v-model="expand_panel_groups"
                  class="mb-1"
                  multiple
                >
                  <v-expansion-panel
                    :title="attribute_group"
                    :value="attribute_group"
                  >
                    <v-expansion-panel-text>
                      <div
                        v-for="(attribute, attribute_id) in attributes"
                        :key="attribute_id"
                      >
                        <attribute-item
                          v-model:value="attribute.value"
                          :read-only="!edit"
                          :attribute-item="attribute"
                        />
                      </div>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-col>
            </v-row>
          </v-col>
          <v-col :cols="verticalView ? 6 : 12" class="pa-5">
            <v-alert
              v-if="edit && report_item.stories.length == 0"
              dense
              outlined
              type="info"
              :text="$t('report_item.no_stories')"
            />
            <card-story
              v-for="story in report_item.stories"
              :key="story.id"
              :story="story"
              :report-view="true"
              @remove-from-report="removeFromReport(story.id)"
            />
          </v-col>
        </v-row>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, computed, onMounted, provide } from 'vue'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { useUserStore } from '@/stores/UserStore'
import { createReportItem, updateReportItem } from '@/api/analyze'
import AttributeItem from '@/components/analyze/AttributeItem.vue'
import CardStory from '@/components/assess/CardStory.vue'
import { notifyFailure, notifySuccess } from '@/utils/helpers'
import { setStoriesToReportItem } from '@/api/analyze'
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
    const form = ref(null)

    const verticalView = ref(useUserStore().split_view)
    const report_item = ref(props.reportItemProp)
    const expand_panel_groups = ref(
      report_item.value.attributes
        ? Object.keys(report_item.value.attributes)
        : []
    )
    const required = ref([(v) => !!v || 'Required'])
    provide(
      'report_stories',
      report_item.value.stories.map((story) => ({
        value: story.id,
        title: story.title
      }))
    )
    const { report_item_types } = storeToRefs(store)

    const container_title = computed(() =>
      props.edit
        ? `${t('button.edit')} report item - ${report_item.value.title}`
        : `${t('button.add_new')} report item`
    )

    onMounted(() => {
      store.loadReportTypes()
    })

    const saveReportItem = async () => {
      const { valid } = await form.value.validate()
      if (!valid) {
        notifyFailure('Please correct the errors before saving.')
        return
      }
      if (props.edit) {
        updateReportItem(report_item.value.id, report_item.value)
          .then((response) => {
            notifySuccess(`Report with ID ${response.data.id} updated`)
          })
          .catch(() => {
            notifyFailure('Failed to update report item')
          })
      } else {
        createReportItem(report_item.value)
          .then((response) => {
            router.push('/report/' + response.data.id)
            emit('reportcreated', response.data.id)
            notifySuccess(`Report with ID ${response.data.id} created`)
            report_item.value = response.data
          })
          .catch(() => {
            notifyFailure('Failed to create report item')
          })
      }
    }

    const removeAllFromReport = () => {
      setStoriesToReportItem(report_item.value.id, [])
        .then(() => {
          report_item.value.stories = []
          notifySuccess('Removed all from report')
        })
        .catch(() => {
          notifyFailure('Failed to remove from report')
        })
    }

    const removeFromReport = (story_id) => {
      report_item.value.stories = report_item.value.stories.filter(
        (story) => story.id !== story_id
      )

      const story_ids = report_item.value.stories.map((story) => story.id)

      setStoriesToReportItem(report_item.value.id, story_ids)
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
      report_item,
      form,
      required,
      report_item_types,
      container_title,
      saveReportItem,
      removeAllFromReport,
      removeFromReport
    }
  }
}
</script>
