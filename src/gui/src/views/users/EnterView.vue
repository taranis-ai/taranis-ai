<template>
  <v-form
    id="form"
    ref="form"
    validate-on="submit"
    style="width: 100%; padding: 8px"
    @submit.prevent="add"
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
          :rules="[rules.url]"
          type="text"
        />
        <code-editor
          v-model:content="editorContent"
          :placeholder="placeholder"
        />
      </v-card-text>
    </v-card>
    <v-spacer class="pt-2"></v-spacer>
    <v-btn block type="submit" color="success">
      {{ $t('enter.create') }}
    </v-btn>
  </v-form>
</template>

<script>
import { computed, ref } from 'vue'
import { addNewsItem } from '@/api/assess'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useMainStore } from '@/stores/MainStore'
import CodeEditor from '@/components/common/CodeEditor.vue'

export default {
  name: 'EnterView',
  components: {
    CodeEditor
  },
  setup() {
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
      published: '',
      collected: '',
      attributes: []
    })

    const editorContent = ref('')

    const rules = {
      required: (v) => !!v || 'Required',
      url: (v) =>
        /^(https?:\/\/)?[\w-]+(\.[\w-]+)+.*$/.test(v) || 'Must be a valid URL'
    }

    async function add() {
      const { valid } = await form.value.validate()

      if (!valid) {
        return
      }

      news_item.value.content = editorContent.value
      news_item.value.author = user.value.name
      const d = new Date()
      news_item.value.collected = d.toISOString()
      news_item.value.published = news_item.value.collected

      try {
        await addNewsItem(news_item.value)

        notifySuccess('enter.successful')
      } catch (e) {
        notifyFailure('enter.failed')
      }
    }

    const placeholder = `Article content here...



    `

    return {
      news_item,
      form,
      rules,
      editorContent,
      placeholder,
      add
    }
  }
}
</script>
