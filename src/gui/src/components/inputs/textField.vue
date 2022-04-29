<template>
  <v-text-field
    :value="value"
    @input="setValue"
    :label="label ? label : 'search'"
    outlined
    dense
    hide-details
  ></v-text-field>
</template>

<script>
export default {
  name: 'textField',
  props: {
    label: String,
    value: String
  },
  methods: {
    setValue (newValue) {
      this.$emit('input', newValue)
    }
  }
}
</script>
