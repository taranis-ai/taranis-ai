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
        v-if="isSaved"
        prepend-icon="mdi-content-copy"
        color="primary"
        variant="flat"
        class="ml-4"
        @click="cloneReportItem"
      >
        Clone
      </v-btn>
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
        v-if="report_item.news_item_aggregates.length"
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
                <span class="caption">ID: {{ report_item.uuid }}</span>
              </v-col>
              <v-col cols="4" class="pr-3">
                <v-select
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
              <v-col v-if="edit && report_type" cols="12" class="pa-0 ma-0">
                <v-expansion-panels
                  v-for="attribute_group in report_type.attribute_groups"
                  :key="attribute_group.id"
                  class="mb-1"
                  multiple
                >
                  <v-expansion-panel :title="attribute_group.title">
                    <v-expansion-panel-text>
                      <div
                        v-for="(
                          attribute, attribute_id
                        ) in report_item.attributes"
                        :key="attribute_id"
                      >
                        <attribute-item
                          v-if="
                            attribute_group.attribute_group_items.find(
                              (item) =>
                                item.id === attribute.attribute_group_item_id
                            )
                          "
                          v-model:value="attribute.value"
                          :read-only="!edit"
                          :attribute-item="
                            attribute_group.attribute_group_items.find(
                              (item) =>
                                item.id === attribute.attribute_group_item_id
                            )
                          "
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
              v-if="edit && report_item.news_item_aggregates.length == 0"
              dense
              outlined
              type="info"
              :text="$t('report_item.no_stories')"
            />
            <card-story
              v-for="story in report_item.news_item_aggregates"
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
    const form = ref(null)
    const isSaved = ref(false)
    const verticalView = ref(useUserStore().split_view)
    const expand_panel_groups = ref([])
    const report_item = ref(props.reportItemProp)
    const required = ref([(v) => !!v || 'Required'])
    provide(
      'report_stories',
      report_item.value.news_item_aggregates.map((story) => ({
        value: story.id,
        title: story.title
      }))
    )

    const { report_item_types } = storeToRefs(store)

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
            if (response && response.data && response.data.id) {
              isSaved.value = true
            }
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
      setAggregatesToReportItem(report_item.value.id, [])
        .then(() => {
          report_item.value.news_item_aggregates = []
          notifySuccess('Removed all from report')
        })
        .catch(() => {
          notifyFailure('Failed to remove from report')
        })
    }

    const removeFromReport = (story_id) => {
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

    const cloneReportItem = async () => {
      if (!report_item.value.title || report_item.value.title.trim() === '') {
        notifyFailure('Cannot clone the item: Title is required.')
        return // Exit the function if the title is not provided
      }
      try {
        console.log(
          'Attempting to clone report item with state:',
          report_item.value
        )
        // Prepare the data for cloning excluding fields we don't want duplicated
        const cloneData = { ...report_item.value }
        delete cloneData.id
        delete cloneData.attributes
        delete cloneData.created
        delete cloneData.last_updated
        delete cloneData.user_id
        cloneData.uuid = null

        console.log('Clone data before sending to backend:', cloneData)

        const response = await createReportItem(cloneData)
        notifySuccess(t('Clone created with ID:') + ` ${response.data.id}`)

        const clonedItemId = response.data.id // Retrieve ID of the newly created item

        // Prepare the update data with attributes
        const updateData = {
          attributes: report_item.value.attributes
        }

        // Update the newly created report item to include attributes
        await updateReportItem(clonedItemId, updateData)
        notifySuccess(`Attributes added to the clone with ID: ${clonedItemId}`)

        router.push('/report/' + response.data.id)
      } catch (error) {
        console.error('Clone creation error:', error)
        notifyFailure(t('Failed to clone report item'))
      }
    }

    return {
      verticalView,
      expand_panel_groups,
      report_item,
      form,
      required,
      report_item_types,
      report_type,
      container_title,
      isSaved,
      saveReportItem,
      removeAllFromReport,
      removeFromReport,
      cloneReportItem
    }
  }
}
</script>
