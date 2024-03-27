<template>
  <v-radio-group v-model="input" :disabled="readOnly" :label="title">
    <v-radio
      :label="$t('attribute.tlp_clear')"
      color="blue-grey"
      value="CLEAR"
    />
    <v-radio :label="$t('attribute.tlp_green')" color="green" value="GREEN" />
    <v-radio :label="$t('attribute.tlp_amber')" color="orange" value="AMBER" />
    <v-radio :label="$t('attribute.tlp_red')" color="red" value="RED" />
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
