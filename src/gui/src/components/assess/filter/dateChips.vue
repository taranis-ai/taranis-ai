<template>
  <v-btn-toggle
    v-model="selected"
    density="compact"
    divided
    selected-class="text-primary"
  >
    <v-btn variant="outlined" value="all">all</v-btn>
    <v-btn variant="outlined" value="today">today</v-btn>
    <v-btn variant="outlined" value="week">week</v-btn>
  </v-btn-toggle>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'DateChips',
  props: {
    modelValue: {
      type: String,
      default: 'all'
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const selected = ref(props.modelValue)

    const updateSelected = (val) => {
      selected.value = val
      emit('update:modelValue', val)
    }

    return {
      selected: computed({
        get: () => selected.value,
        set: updateSelected
      })
    }
  }
}
</script>
