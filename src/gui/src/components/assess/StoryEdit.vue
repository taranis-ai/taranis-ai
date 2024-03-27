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

        <attributes-table v-model="story.attributes" />

        <code-editor
          v-model:content="story.comment"
          placeholder="Story comment"
        />
      </v-card-text>
    </v-card>
    <v-spacer class="pt-2"></v-spacer>
    <v-btn block class="mt-5" type="submit" color="success">
      {{ $t('button.update') }}
    </v-btn>
  </v-form>
</template>

<script>
import { ref } from 'vue'
import { patchStory } from '@/api/assess'
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
          attributes: story.value.attributes
        })
        notifySuccess(result)
      } catch (e) {
        notifyFailure(e)
      }
      router.push('/story/' + props.storyProp.id)
    }

    return {
      story,
      form,
      rules,
      submit
    }
  }
}
</script>
