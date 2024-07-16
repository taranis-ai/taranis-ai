<template>
  <div>
    <h3 v-if="header">{{ header }}</h3>
    <code-mirror
      v-model="data"
      basic
      wrap
      :placeholder="placeholder"
      :disabled="disabled"
    />
  </div>
</template>

<script>
import { computed } from 'vue'
import CodeMirror from 'vue-codemirror6'

export default {
  name: 'CodeEditor',
  components: {
    CodeMirror
  },
  props: {
    header: {
      type: String,
      required: false,
      default: ''
    },
    placeholder: {
      type: String,
      default: 'Enter content here...\n\n\n\n\n'
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
    const data = computed({
      get() {
        return props.content
      },
      set(value) {
        emit('update:content', value)
      }
    })

    return {
      data
    }
  }
}
</script>

<style scoped>
.editor {
  height: 242px;
  max-height: 242px;
}
</style>
