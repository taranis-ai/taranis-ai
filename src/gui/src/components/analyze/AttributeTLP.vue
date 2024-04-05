<template>
  <v-radio-group v-model="input" :disabled="readOnly" :label="title">
    <v-radio label="TLP:CLEAR" color="blue-grey" value="clear" />
    <v-radio label="TLP:GREEN" color="green" value="green" />
    <v-radio label="TLP:AMBER" color="orange" value="amber" />
    <v-radio label="TLP:AMBER+STRICT" color="orange" value="amber+strict" />
    <v-radio label="TLP:RED" color="red" value="red" />
  </v-radio-group>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'AttributeTLP',
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
    readOnly: { type: Boolean, default: false }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const input = computed({
      get: () => props.modelValue,
      set: (newValue) => emit('update:modelValue', newValue || '')
    })

    return {
      input
    }
  }
}
</script>
