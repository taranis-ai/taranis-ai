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

        Published:
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

        <attributes-table v-model="news_item.attributes" />

        <code-editor
          v-model:content="news_item.content"
          :placeholder="placeholder"
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
import { computed, ref, onMounted } from 'vue'
import { addNewsItem, patchNewsItem } from '@/api/assess'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useUserStore } from '@/stores/UserStore'
import CodeEditor from '@/components/common/CodeEditor.vue'
import AttributesTable from '@/components/assess/AttributesTable.vue'
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
    }
  },
  setup(props) {
    const userStore = useUserStore()
    const form = ref(null)
    const edit = ref(props.newsItemProp ? true : false)
    const router = useRouter()
    const { t } = useI18n()
    const submitText = computed(() => {
      return edit.value ? t('button.update') : t('button.create')
    })

    const news_item = ref({
      title: '',
      review: '',
      content: '',
      link: '',
      source: 'manual',
      author: '',
      published: new Date(),
      collected: '',
      attributes: []
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

      news_item.value.author = userStore.name
      const d = new Date()
      news_item.value.collected = d.toISOString()

      try {
        const result = await addNewsItem(news_item.value)

        notifySuccess(result)
        router.push('/newsitem/' + result.data.ids[0])
      } catch (e) {
        notifyFailure(e)
      }
    }

    const placeholder = `Article content here...



    `

    onMounted(() => {
      if (props.newsItemProp) {
        news_item.value = props.newsItemProp
      }
    })

    return {
      news_item,
      form,
      rules,
      placeholder,
      submitText,
      submit
    }
  }
}
</script>
