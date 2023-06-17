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
      class="vertical-button mb-5"
      :value="button.value"
      :prepend-icon="button.icon"
      :append-icon="
        filterAttribute.includes(button.value) ? 'mdi-check-bold' : undefined
      "
      size="large"
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

<style scoped>
.vertical-button-group {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.vertical-button {
  justify-content: flex-start;
  text-transform: unset !important;
}
</style>
