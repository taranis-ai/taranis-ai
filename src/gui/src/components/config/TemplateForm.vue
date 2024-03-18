<template>
  <v-container fluid class="mt-3">
    <v-form
      id="form"
      ref="form"
      validate-on="submit"
      @submit.prevent="submitTemplate"
    >
      <v-row no-gutters>
        <v-col cols="12">
          <v-text-field v-model="name" class="mt-5" label="Template Name" />
        </v-col>
        <v-col cols="12">
          <code-editor
            v-model:content="data"
            class="mt-5"
            header="Template Content"
          />
        </v-col>
        <v-col cols="12">
          <v-btn type="submit" block color="success" class="mt-5">
            Submit
          </v-btn>
        </v-col>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
import CodeEditor from '@/components/common/CodeEditor.vue'
import { ref, watch } from 'vue'

export default {
  name: 'TemplateForm',
  components: {
    CodeEditor
  },
  props: {
    templateData: {
      type: String,
      required: true
    },
    templateName: {
      type: String,
      required: true
    }
  },
  emits: ['updated'],
  setup(props, { emit }) {
    const data = ref(props.templateData)
    const name = ref(props.templateName)
    const edit = ref(false)

    const submitTemplate = () => {
      emit('updated', { templateData: data.value, templateName: name.value })
    }

    watch(
      () => props.templateData,
      (val) => {
        data.value = val
      }
    )

    watch(
      () => props.templateName,
      (val) => {
        name.value = val
      }
    )

    return {
      data,
      name,
      edit,
      submitTemplate
    }
  }
}
</script>
