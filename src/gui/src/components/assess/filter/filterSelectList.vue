<template>
  <v-btn-toggle
    v-model="filterAttribute"
    class="vertical-button-group"
    selected-class="text-primary"
    multiple
  >
    <v-btn
      v-for="button in filterAttributeOptions"
      :key="button.value"
      class="vertical-button toggle-button py-2 px-4 mb-1"
      :value="button.value"
      :prepend-icon="button.icon"
      :append-icon="
        filterAttribute.includes(button.value) ? 'mdi-check-bold' : undefined
      "
    >
      {{ button.label }}
    </v-btn>
  </v-btn-toggle>
</template>

<script>
import { computed } from 'vue'

export default {
  name: 'FilterSelectList',
  props: {
    modelValue: {
      type: Array,
      default: () => []
    },
    filterAttributeOptions: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const filterAttribute = computed({
      get() {
        return props.modelValue
      },
      set(value) {
        const filterUpdate = props.filterAttributeOptions.reduce(
          (obj, item) => {
            obj[item.value] = value.includes(item.value) ? 'true' : undefined
            return obj
          },
          {}
        )

        console.debug('filterAttributeSelections', filterUpdate)
        emit('update:modelValue', filterUpdate)
      }
    })

    return {
      filterAttribute
    }
  }
}
</script>

<style lang="scss">
.toggle-button {
  border-radius: 4px !important;
}
</style>
