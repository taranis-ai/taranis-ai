<template>
  <div id="cvssboard" ref="cvssboard"></div>
</template>

<style src="@/assets/cvss.css">
</style>

<script>
import { CVSS } from '@/plugins/cvss.js'

export default {
  name: 'AttributeCVSS',
  components: {},
  emits: ['input'],
  data: () => ({
    cvss: null
  }),
  props: {
    value: {
      type: String,
      default: 'CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:C/C:N/I:N/A:L',
      required: true
    }
  },
  methods: {
    onChange() {
      const vector = this.cvss.get().vector
      if (vector !== 'CVSS:3.0/AV:_/AC:_/PR:_/UI:_/S:_/C:_/I:_/A:_') {
        this.$emit('input', this.cvss.get().vector)
      }
    }
  },
  mounted() {
    this.cvss = new CVSS('cvssboard', {
      onchange: this.onChange
    })
    this.cvss.set(this.value)
  }
}
</script>
