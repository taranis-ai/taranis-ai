<template>
  <VueDatePicker
    v-model="selected"
    :name="'dateFilter-' + placeholder"
    :placeholder="placeholder"
    :max-date="maxDatePlus"
    format="yyyy-MM-dd HH:mm:ss"
    time-picker-inline
    auto-apply
    clearable
    space-confirm
    @open="openMenu()"
  />
</template>

<script>
import { ref, computed, watch } from 'vue'
import { useUserStore } from '@/stores/UserStore'

export default {
  name: 'DateFilter',
  props: {
    modelValue: {
      type: String,
      default: null
    },
    placeholder: {
      type: String,
      default: 'Enter date'
    },
    maxDate: {
      type: Date,
      default: new Date()
    },
    defaultDate: {
      type: Date,
      required: false,
      default: null
    }
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const selected = ref(props.modelValue)
    const userStore = useUserStore()

    const locale = computed(() => {
      return userStore.language
    })

    const maxDatePlus = computed(() => {
      const newDate = new Date(props.maxDate.getTime())
      newDate.setHours(23)
      newDate.setMinutes(59)
      return newDate
    })

    function updateSelected(val) {
      if (val === null) {
        selected.value = null
      } else {
        selected.value = val.toISOString()
      }
      emit('update:modelValue', selected.value)
    }

    function openMenu() {
      console.debug(props.defaultDate)
      if (selected.value === null && props.defaultDate !== null) {
        selected.value = props.defaultDate
      }
    }

    watch(
      () => props.modelValue,
      (val) => {
        selected.value = val
      }
    )

    return {
      openMenu,
      locale,
      maxDatePlus,
      selected: computed({
        get: () => Date.parse(selected.value),
        set: updateSelected
      })
    }
  }
}
</script>
