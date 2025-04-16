<template>
  <v-autocomplete
    v-model="selected"
    :readonly="readOnly"
    :label="title"
    :items="report_item_stories[reportItemId]"
    :multiple="multiple"
    :rules="rules"
    closable-chips
    chips
    center-affix
    clearable
    variant="outlined"
    no-data-text="No Stories found"
    menu-icon="mdi-chevron-down"
  >
    <template #item="{ props, item }">
      <v-list-item v-bind="props" :base-color="item.raw.used ? 'grey' : ''">
        <template #title>
          {{ item.raw.title }}
          <v-icon
            :icon="
              item.raw.used ? 'mdi-checkbox-outline' : 'mdi-close-box-outline'
            "
          />
        </template>
      </v-list-item>
    </template>
  </v-autocomplete>
</template>

<script>
import { computed, ref } from 'vue'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'AttributeStory',
  props: {
    modelValue: {
      type: String,
      required: true
    },
    title: {
      type: String,
      default: 'Stories'
    },
    reportItemId: {
      type: String,
      required: true
    },
    readOnly: { type: Boolean, default: false },
    multiple: { type: Boolean, default: true },
    required: { type: Boolean, default: false }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const rules = [(v) => v.length > 0 || 'Required']
    const store = useAnalyzeStore()

    const { report_item_stories } = storeToRefs(store)

    const selected = ref(
      props.modelValue
        .split(',')
        .filter((v) => v)
        .map((val) => val)
    )

    function updateSelected(val) {
      selected.value = val
      emit('update:modelValue', val.filter((v) => v).join(','))
    }

    return {
      selected: computed({
        get: () => selected.value,
        set: updateSelected
      }),
      report_item_stories,
      rules
    }
  }
}
</script>
