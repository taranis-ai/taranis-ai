<template>
  <div>
    <v-switch
      v-model="localValue"
      :label="label ? label : ''"
      :color="color ? color : 'success'"
      @change="setValue"
      inset
      dense
      hide-details
    ></v-switch>
  </div>
</template>

<script>
export default {
  name: 'switchField',
  props: {
    label: String,
    color: String,
    value: Boolean
  },
  data: () => ({
    localValue: false
  }),
  methods: {
    setValue () {
      this.$emit('input', this.localValue)
    }
  },
  mounted () {
    this.localValue = this.value
  }
}
</script>
