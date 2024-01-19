<template>
  <v-form
    id="form"
    ref="form"
    validate-on="submit"
    style="width: 100%; padding: 8px"
    @submit.prevent="submit"
  >
    <v-card>
      <v-card-text>
        <v-text-field
          v-model="news_item.title"
          :label="$t('enter.title')"
          name="title"
          type="text"
          :rules="[rules.required]"
        />

        <VueDatePicker
          v-model="news_item.published"
          name="published"
          :placeholder="$t('enter.published')"
          :max-date="new Date()"
          time-picker-inline
          clearable
          auto-apply
          class="mb-5"
        />

        <v-textarea
          v-model="news_item.review"
          :label="$t('enter.review')"
          name="review"
          :rules="[rules.required]"
        />

        <v-text-field
          v-model="news_item.link"
          :label="$t('enter.link')"
          name="link"
          type="text"
        />

        <code-editor
          v-model:content="editorContent"
          :placeholder="placeholder"
        />
      </v-card-text>
    </v-card>
    <v-spacer class="pt-2"></v-spacer>
    <v-btn block class="mt-5" type="submit" color="success">
      {{ $t('enter.create') }}
    </v-btn>
  </v-form>
</template>

<script>
import { computed, ref, onMounted } from 'vue'
import { addNewsItem } from '@/api/assess'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useMainStore } from '@/stores/MainStore'
import CodeEditor from '@/components/common/CodeEditor.vue'

export default {
  name: 'NewsItemEdit',
  components: {
    CodeEditor
  },
  props: {
    newsItemProp: {
      type: Object,
      default: () => {},
      required: false
    }
  },
  setup(props) {
    const mainStore = useMainStore()
    const form = ref(null)
    const user = computed(() => mainStore.user)

    const news_item = ref({
      id: '',
      title: '',
      review: '',
      content: '',
      link: '',
      source: 'manual',
      author: '',
      hash: '',
      osint_source_id: '',
      published: new Date(),
      collected: '',
      attributes: []
    })

    const editorContent = ref('')

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

      news_item.value.content = editorContent.value
      news_item.value.author = user.value.name
      const d = new Date()
      news_item.value.collected = d.toISOString()

      try {
        await addNewsItem(news_item.value)

        notifySuccess('enter.successful')
      } catch (e) {
        notifyFailure('enter.failed')
      }
    }

    const placeholder = `Article content here...



    `

    onMounted(() => {
      if (props.newsItemProp) {
        news_item.value = props.newsItemProp
        editorContent.value = props.newsItemProp.content
      }
    })

    return {
      news_item,
      form,
      rules,
      editorContent,
      placeholder,
      submit
    }
  }
}
</script>
