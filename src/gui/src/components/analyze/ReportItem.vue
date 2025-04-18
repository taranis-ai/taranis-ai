<template>
  <v-card class="h-100">
    <v-toolbar density="compact">
      <v-toolbar-title :text="container_title" />
      <v-spacer />
      <v-switch
        v-model="verticalView"
        style="max-width: 250px"
        class="mr-4"
        :label="$t('analyze.vertical_view')"
        hide-details
        color="success"
        density="compact"
      />
      <v-switch
        v-if="edit"
        v-model="report_item.completed"
        style="max-width: 250px"
        hide-details
        :label="$t('analyze.completed')"
        color="success"
        density="compact"
      />
      <v-btn
        v-if="edit"
        prepend-icon="mdi-chart-box-plus-outline"
        color="primary"
        class="ml-4"
        variant="flat"
        text="New Product from Report"
        :to="newProductProps"
      />
      <v-btn
        prepend-icon="mdi-delete-outline"
        color="error"
        variant="flat"
        class="ml-4"
        @click="removeAllFromReport"
      >
        {{ $t('analyze.remove_all_stories') }}
      </v-btn>
      <v-btn
        prepend-icon="mdi-content-save"
        color="success"
        variant="flat"
        class="ml-4"
        @click="saveReportItem"
      >
        <v-tooltip activator="parent" text="[ctrl+shift+s]" location="bottom" />
        {{ $t('button.save') }}
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
                  menu-icon="mdi-chevron-down"
                />
              </v-col>
              <v-col cols="8" class="pr-3">
                <v-text-field
                  v-model="report_item.title"
                  :label="$t('generic.title')"
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
                  eager
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
                          :report-item-id="report_item.id"
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
import { ref, computed, onMounted, watch } from 'vue'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { useUserStore } from '@/stores/UserStore'
import { createReportItem } from '@/api/analyze'
import AttributeItem from '@/components/analyze/AttributeItem.vue'
import CardStory from '@/components/assess/CardStory.vue'
import { notifyFailure, notifySuccess } from '@/utils/helpers'
import { setStoriesToReportItem } from '@/api/analyze'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useHotkeys } from 'vue-use-hotkeys'

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
    const { report_item_types, report_item_stories } = storeToRefs(store)
    const newProductProps = ref({
      name: 'product',
      query: { report: report_item.value.id }
    })

    const used_story_ids = computed(() => {
      if (!report_item.value || !report_item.value.attributes) {
        return []
      }
      const report_item_attributes =
        'Data' in report_item.value.attributes
          ? Object.values(report_item.value.attributes.Data)
          : []
      return report_item_attributes
        .filter((item) => item.type === 'STORY')
        .map((item) => item.value.split(','))
        .flat()
    })

    watch(
      () => used_story_ids.value,
      () => {
        setReportItemStories()
      }
    )

    function setReportItemStories() {
      report_item_stories.value[report_item.value.id] =
        report_item.value.stories.map((story) => ({
          value: story.id,
          title: story.title,
          used: used_story_ids.value.includes(story.id)
        }))
    }

    const container_title = computed(() =>
      props.edit
        ? `${t('button.edit')} report item - ${report_item.value.title}`
        : `${t('button.add_new')} report item`
    )

    onMounted(() => {
      store.loadReportTypes()
      setReportItemStories()
    })

    useHotkeys('ctrl+shift+s', (event, handler) => {
      console.debug(`You pressed ${handler.key}`)
      event.preventDefault()
      saveReportItem()
    })

    async function saveReportItem() {
      const { valid } = await form.value.validate()
      if (!valid) {
        notifyFailure('Please correct the errors before saving.')
        return
      }
      if (props.edit) {
        const flattened_attributes = {}

        for (const group of Object.values(report_item.value.attributes)) {
          for (const [key, obj] of Object.entries(group)) {
            flattened_attributes[key] = { value: obj.value }
          }
        }

        const update_report_item = {
          title: report_item.value.title,
          completed: report_item.value.completed,
          attributes: flattened_attributes
        }
        try {
          store.patchReportItem(report_item.value.id, update_report_item)
        } catch (error) {
          notifyFailure('Failed to update report item')
        }
        return
      }

      try {
        const new_report_item = {
          ...report_item.value,
          stories: report_item.value.stories.map((story) => story.id)
        }
        const response = await createReportItem(new_report_item)
        console.debug('Report item created:', response.data)
        router.push('/report/' + response.data.id)
        emit('reportcreated', response.data.id)
        notifySuccess(`Report with ID ${response.data.id} created`)
        report_item.value = response.data
        store.updateReportItems()
      } catch (error) {
        console.error(error)
        notifyFailure('Failed to create report item')
      }
    }

    function removeAllFromReport() {
      setStoriesToReportItem(report_item.value.id, [])
        .then(() => {
          report_item.value.stories = []
          notifySuccess('Removed all from report')
        })
        .catch(() => {
          notifyFailure('Failed to remove from report')
        })
    }

    function removeFromReport(story_id) {
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
      newProductProps,
      container_title,
      saveReportItem,
      removeAllFromReport,
      removeFromReport
    }
  }
}
</script>
