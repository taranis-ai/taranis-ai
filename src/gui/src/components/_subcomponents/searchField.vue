<template>
  <v-text-field
    :value="value"
    @input="setValue"
    :label="label ? label : 'search'"
    outlined
    dense
    hide-details
    append-icon="$awakeSearch"
  ></v-text-field>
</template>

<script>
export default {
  name: 'searchField',
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
