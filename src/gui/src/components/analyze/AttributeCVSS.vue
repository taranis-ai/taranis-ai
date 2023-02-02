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
      default: '',
      required: true
    }
  },
  methods: {
    onChange() {
      console.debug(this.cvss.get().vector)
      this.$emit('input', this.cvss.get().vector)
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
