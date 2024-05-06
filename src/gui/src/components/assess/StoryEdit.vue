<template>
  <v-container fluid>
    <v-card>
      <v-card-text>
        <v-form
          id="form"
          ref="form"
          validate-on="submit"
          style="width: 100%; padding: 8px"
          @submit.prevent="submit"
        >
          <v-text-field
            v-model="story.title"
            :label="$t('enter.title')"
            name="title"
            type="text"
            :rules="[rules.required]"
          />

          <edit-tags v-model="story.tags" />

          <attributes-table v-model="story.attributes" />

          <code-editor
            v-model:content="story.comment"
            :header="$t('enter.comment')"
            :placeholder="$t('enter.comment_placeholder')"
          />
          <code-editor
            v-model:content="story.summary"
            :header="$t('enter.summary')"
            :placeholder="$t('enter.summary_placeholder')"
          />
          <v-btn
            prepend-icon="mdi-auto-fix"
            text="AI based summary"
            @click="triggerSummaryBot"
          />
          <v-spacer class="pt-1"></v-spacer>
          <v-btn block class="mt-5" type="submit" color="success">
            {{ $t('button.update') }}
          </v-btn>
        </v-form>
      </v-card-text>
    </v-card>
    <v-expansion-panels v-model="panels" multiple>
      <v-expansion-panel
        v-for="news_item in story.news_items"
        :key="news_item.id"
        :title="news_item.title"
        :text="news_item.content"
        :value="news_item.id"
      >
      </v-expansion-panel>
    </v-expansion-panels>
  </v-container>
</template>

<script>
import { ref } from 'vue'
import { patchStory, triggerBot } from '@/api/assess'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import CodeEditor from '@/components/common/CodeEditor.vue'
import EditTags from '@/components/assess/EditTags.vue'
import AttributesTable from '@/components/assess/AttributesTable.vue'
import { useRouter } from 'vue-router'

export default {
  name: 'StoryEdit',
  components: {
    CodeEditor,
    EditTags,
    AttributesTable
  },
  props: {
    storyProp: {
      type: Object,
      default: () => {},
      required: true
    }
  },
  setup(props) {
    const form = ref(null)
    const router = useRouter()
    const story = ref(props.storyProp)
    const panels = ref(story.value.news_items.map((item) => item.id))

    const rules = {
      required: (v) => !!v || 'Required'
    }

    async function submit() {
      const { valid } = await form.value.validate()

      if (!valid) {
        return
      }

      try {
        const result = await patchStory(props.storyProp.id, {
          title: story.value.title,
          tags: story.value.tags,
          comment: story.value.comment,
          summary: story.value.summary,
          attributes: story.value.attributes
        })
        notifySuccess(result)
      } catch (e) {
        notifyFailure(e)
      }
      router.push('/story/' + props.storyProp.id)
    }

    async function triggerSummaryBot() {
      try {
        const result = await triggerBot('summary_bot', props.storyProp.id)
        notifySuccess(result.data.message)
      } catch (e) {
        notifyFailure(e)
      }
    }

    return {
      panels,
      story,
      form,
      rules,
      submit,
      triggerSummaryBot
    }
  }
}
</script>
