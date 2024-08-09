<template>
  <v-file-input
    v-model="input"
    :disabled="readOnly"
    :label="title"
    :rules="rules"
    outlined
  />
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'AttributeAttachment',
  props: {
    modelValue: {
      type: String,
      default: '',
      required: true
    },
    title: {
      type: String,
      default: 'TLP'
    },
    readOnly: { type: Boolean, default: false },
    required: { type: Boolean, default: false }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const rules = [(v) => v.length > 0 || 'Required']

    const input = computed({
      get: () => {
        if (props.modelValue) {
          const parts = props.modelValue.split(';base64,')
          if (parts.length === 2) {
            return {
              name: atob(parts[0].split(':')[1]),
              content: parts[1]
            }
          }
        }
        return null
      },
      set: (newValue) => {
        if (newValue) {
          const reader = new FileReader()
          reader.onload = (event) => {
            const base64String = event.target.result.split(',')[1]
            const fileInfo = `filename:${btoa(newValue.name)};base64,${base64String}`
            emit('update:modelValue', fileInfo)
          }
          reader.readAsDataURL(newValue)
        } else {
          emit('update:modelValue', '')
        }
      }
    })

    return {
      input,
      rules
    }
  }
}
</script>
