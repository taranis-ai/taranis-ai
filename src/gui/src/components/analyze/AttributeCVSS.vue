<template>
  <div>
    <v-text-field
      v-model="vector"
      name="cvss"
      prepend-icon="mdi-chevron-down"
      @click:prepend="open = !open"
    />
    <div v-show="open" id="cvssboard" ref="cvssboard"></div>
  </div>
</template>

<script>
import { CVSS } from '@/plugins/cvss.js'

export default {
  name: 'AttributeCVSS',
  props: {
    value: {
      type: String,
      default: 'CVSS:3.1/AV:L/AC:L/PR:N/UI:N/S:C/C:N/I:N/A:L',
      required: true
    }
  },
  emits: ['input'],
  data: () => ({
    cvss: null,
    open: true
  }),
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
  mounted() {
    this.cvss = new CVSS('cvssboard', {
      onchange: this.onChange
    })
    this.cvss.set(this.value)
  },
  methods: {
    onChange() {
      const vector = this.cvss.get().vector
      if (vector !== 'CVSS:3.1/AV:_/AC:_/PR:_/UI:_/S:_/C:_/I:_/A:_') {
        this.$emit('input', this.cvss.get().vector)
      }
    }
  }
}
</script>

<style src="@/assets/cvss.css"></style>
