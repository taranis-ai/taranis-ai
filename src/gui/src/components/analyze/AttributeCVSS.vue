<template>
  <div>
  <v-text-field
    name="cvss"
    v-model="vector"
    prepend-icon="mdi-chevron-down"
    @click:prepend="open = !open"
  />
  <div v-show="open" id="cvssboard" ref="cvssboard"></div>
  </div>
</template>

<style src="@/assets/cvss.css">
</style>

<script>
import { CVSS } from '@/plugins/cvss.js'

export default {
  name: 'AttributeCVSS',
  emits: ['input'],
  data: () => ({
    cvss: null,
    open: true
  }),
  props: {
    value: {
      type: String,
      default: 'CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:C/C:N/I:N/A:L',
      required: true
    }
  },
  computed: {
    vector: {
      get() {
        if (!this.cvss) {
          return this.value
        }
        return this.cvss.get().vector
      },
      set(value) {
        this.cvss.set(value)
      }
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
