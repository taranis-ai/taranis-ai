<template>
  <v-btn-toggle
    v-model="selected"
    density="compact"
    divided
    selected-class="text-primary"
    class="d-flex flex-row"
  >
    <v-btn class="flex-grow-1" variant="outlined" value="week">
      <v-tooltip activator="parent" location="top" text="from last monday" />
      week
    </v-btn>
    <v-btn class="flex-grow-1" variant="outlined" value="month">
      <v-tooltip activator="parent" location="top" text="from first of month" />
      month
    </v-btn>
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
