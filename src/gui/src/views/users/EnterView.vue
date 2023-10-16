<template>
  <v-form
    id="form"
    ref="form"
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
        />

        <v-textarea
          v-model="news_item.review"
          :label="$t('enter.review')"
          name="review"
        />
        <v-text-field
          v-model="news_item.source"
          :label="$t('enter.source')"
          name="source"
          type="text"
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
    <v-btn color="primary" @click="add()">{{ $t('enter.create') }}</v-btn>
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
    const user = computed(() => mainStore.user)

    const news_item = ref({
      id: '',
      title: '',
      review: '',
      content: '',
      link: '',
      source: '',
      author: '',
      hash: '',
      osint_source_id: '',
      published: '',
      collected: '',
      attributes: []
    })

    const editorContent = ref('')

    const add = async () => {
      news_item.value.content = editorContent.value
      news_item.value.author = user.value.name
      const d = new Date()
      news_item.value.collected = d.toISOString()
      news_item.value.published = news_item.value.collected

      try {
        await addNewsItem(news_item.value)

        // Reset fields
        Object.keys(news_item.value).forEach((key) => {
          news_item.value[key] = ''
        })

        notifySuccess('enter.successful')
      } catch (e) {
        notifyFailure('enter.failed')
      }
    }

    const placeholder = `Article content here...



    `

    return {
      news_item,
      editorContent,
      placeholder,
      add
    }
  }
}
</script>
