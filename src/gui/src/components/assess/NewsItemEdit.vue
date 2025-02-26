<template>
  <v-form
    id="form"
    ref="form"
    validate-on="submit"
    style="width: 100%; padding: 8px"
    @submit.prevent="submit"
  >
    <v-card>
      <v-card-title v-if="readOnly" style="background-color: #ffee00">
        <h3>
          Editing is prohibited for news items that are not manually created.
        </h3>
      </v-card-title>
      <v-card-text>
        <v-text-field
          v-model="news_item.title"
          :label="$t('form.title')"
          name="title"
          type="text"
          :rules="[rules.required]"
        />

        Published:
        <VueDatePicker
          v-model="news_item.published"
          name="published"
          position="left"
          :placeholder="$t('enter.published')"
          :max-date="new Date()"
          time-picker-inline
          clearable
          auto-apply
          class="mb-5"
        />

        <code-editor
          v-model:content="news_item.content"
          class="mb-3"
          :placeholder="$t('enter.content_placeholder')"
        />

        <v-text-field
          v-model="news_item.link"
          :label="$t('enter.link')"
          name="link"
          type="text"
        />

        <v-textarea
          v-model="news_item.review"
          :label="$t('enter.comment')"
          name="review"
        />

        <attributes-table v-model="news_item.attributes" />
      </v-card-text>
    </v-card>
    <v-spacer class="pt-2"></v-spacer>
    <v-btn
      block
      class="mt-5"
      type="submit"
      color="success"
      :disabled="readOnly"
    >
      {{ submitText }}
      <v-tooltip
        v-if="storyId"
        activator="parent"
        location="bottom"
        :text="submitText + ' ' + storyId"
      />
    </v-btn>
  </v-form>
</template>

<script>
import { computed, ref, onMounted } from 'vue'
import { addNewsItem, patchNewsItem, groupAction } from '@/api/assess'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useUserStore } from '@/stores/UserStore'
import CodeEditor from '@/components/common/CodeEditor.vue'
import AttributesTable from '@/components/common/AttributesTable.vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

export default {
  name: 'NewsItemEdit',
  components: {
    CodeEditor,
    AttributesTable
  },
  props: {
    newsItemProp: {
      type: Object,
      default: () => {},
      required: false
    },
    storyId: {
      type: String,
      default: '',
      required: false
    }
  },
  setup(props) {
    const userStore = useUserStore()
    const form = ref(null)
    const edit = ref(props.newsItemProp ? true : false)
    const router = useRouter()
    const { t } = useI18n()
    const submitText = computed(() => {
      if (props.storyId) {
        return t('enter.add_to_story')
      }
      return edit.value ? t('button.update') : t('button.create')
    })

    const news_item = ref({
      title: '',
      review: '',
      content: '',
      link: '',
      source: 'manual',
      osint_source_id: 'manual',
      author: userStore.name,
      published: new Date(),
      collected: '',
      attributes: []
    })

    const readOnly = computed(() => {
      return news_item.value.source !== 'manual'
    })

    const rules = {
      required: (v) => !!v || 'Required',
      url: (v) =>
        /^(https?:\/\/)?[\w-]+(\.[\w-]+)+.*$/.test(v) || 'Must be a valid URL'
    }

    async function submit() {
      const { valid } = await form.value.validate()
      if (!valid) {
        return
      }

      if (edit.value) {
        try {
          const result = await patchNewsItem(
            props.newsItemProp.id,
            news_item.value
          )
          notifySuccess(result)
        } catch (e) {
          notifyFailure(e)
        }
        router.push('/newsitem/' + props.newsItemProp.id)
        return
      }

      const d = new Date()
      news_item.value.collected = d.toISOString()

      try {
        const result = await addNewsItem(news_item.value)
        let new_story = result.data.story_id
        if (props.storyId) {
          await groupAction([props.storyId, new_story])
          new_story = props.storyId
        }
        notifySuccess(result)
        router.push('/story/' + new_story)
      } catch (e) {
        notifyFailure(e)
      }
    }

    onMounted(() => {
      if (props.newsItemProp) {
        news_item.value = props.newsItemProp
      }
    })

    return {
      news_item,
      form,
      rules,
      readOnly,
      submitText,
      submit
    }
  }
}
</script>
