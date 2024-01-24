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
          v-model="story.title"
          :label="$t('enter.title')"
          name="title"
          type="text"
          :rules="[rules.required]"
        />

        <edit-tags v-model="story.tags" />

        <code-editor
          v-model:content="story.comment"
          placeholder="Story comment"
        />
      </v-card-text>
    </v-card>
    <v-spacer class="pt-2"></v-spacer>
    <v-btn block class="mt-5" type="submit" color="success">
      {{ submitText }}
    </v-btn>
  </v-form>
</template>

<script>
import { computed, ref } from 'vue'
import { addNewsItem, patchNewsItem } from '@/api/assess'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useMainStore } from '@/stores/MainStore'
import CodeEditor from '@/components/common/CodeEditor.vue'
import EditTags from '@/components/assess/EditTags.vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

export default {
  name: 'StoryEdit',
  components: {
    CodeEditor,
    EditTags
  },
  props: {
    storyProp: {
      type: Object,
      default: () => {},
      required: true
    }
  },
  setup(props) {
    const mainStore = useMainStore()
    const form = ref(null)
    const user = computed(() => mainStore.user)
    const edit = ref(props.newsItemProp ? true : false)
    const router = useRouter()
    const { t } = useI18n()
    const submitText = computed(() => {
      return edit.value ? t('button.update') : t('button.create')
    })

    const story = ref(props.storyProp)

    const rules = {
      required: (v) => !!v || 'Required'
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

      news_item.value.author = user.value.name
      const d = new Date()
      news_item.value.collected = d.toISOString()

      try {
        const result = await addNewsItem(news_item.value)

        notifySuccess(result)
        console.debug(result.data)
        router.push('/newsitem/' + result.data.ids[0])
      } catch (e) {
        notifyFailure(e)
      }
    }

    return {
      story,
      form,
      rules,
      submitText,
      submit
    }
  }
}
</script>
