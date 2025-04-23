<template>
  <div class="d-flex">
    <v-btn-group class="flex-grow-1" density="compact" divided>
      <v-btn
        class="flex-grow-1"
        variant="outlined"
        @click="selected = 'shift'"
        data-testid="from-end-last-shift-button"
      >
        <v-tooltip
          activator="parent"
          location="top"
          text="from end of last shift"
        />
        <v-icon icon="mdi-clock-end" />
      </v-btn>
      <v-btn
        class="flex-grow-1"
        variant="outlined"
        @click="selected = 'week'"
        data-testid="from-last-monday-button"
      >
        <v-tooltip activator="parent" location="top" text="from last monday" />
        <v-icon icon="mdi-calendar-week" />
      </v-btn>
      <v-btn
        class="flex-grow-1"
        variant="outlined"
        @click="selected = '24h'"
        data-testid="last-24h-button"
      >
        <v-tooltip activator="parent" location="top" text="last 24 hours" />
        <v-icon icon="mdi-calendar-today-outline" />
      </v-btn>
    </v-btn-group>
  </div>
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

    function updateSelected(val) {
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
