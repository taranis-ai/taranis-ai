<template>
  <div>
    <h3 v-if="header">{{ header }}</h3>
    <codemirror
      v-model="data"
      class="editor"
      :placeholder="placeholder"
      :extensions="extensions"
      :style="{ 'min-height': '8em' }"
      :disabled="disabled"
    />
  </div>
</template>

<script>
import { computed } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { basicSetup } from 'codemirror'

import { html } from '@codemirror/lang-html'
import { json } from '@codemirror/lang-json'

export default {
  name: 'CodeEditor',
  components: {
    Codemirror
  },
  props: {
    header: {
      type: String,
      required: false,
      default: ''
    },
    placeholder: {
      type: String,
      default: 'Enter content here...'
    },
    content: {
      type: String,
      default: ''
    },
    disabled: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:content'],
  setup(props, { emit }) {
    const extensions = [html(), json(), basicSetup]

    const data = computed({
      get() {
        return props.content
      },
      set(value) {
        emit('update:content', value)
      }
    })

    return {
      data,
      extensions
    }
  }
}
</script>

<style>
.editor {
  height: 242px;
  max-height: 242px;
}
</style>
