<template>
  <v-combobox
    :value="value"
    :items="items"
    @change="setValue"
    :label="label ? label : 'tags'"
    multiple
    outlined
    dense
    append-icon="mdi-chevron-down"
    class="pl-0"
    hide-details
    hide-selected
    deletable-chips
  >
    <!-- @change="defaultTag" -->
    <template v-slot:selection="{ parent, item, index }">
      <v-chip
        small
        v-if="index < 1 && !parent.isMenuActive"
        @click:close="removeTag(item)"
        label
        color="grey--lighten-4"
        close
        close-icon="mdi-delete"
        class="pa-2 ml-0 mt-1"
      >
        <span>{{ item }}</span>
      </v-chip>

      <v-chip
        small
        v-else-if="parent.isMenuActive"
        @click:close="removeTag(item)"
        label
        color="grey--lighten-4"
        close
        close-icon="mdi-delete"
        class="pa-2 ml-0 mt-1"
      >
        <span>{{ item }}</span>
      </v-chip>
      <span
        v-if="index === 1 && !parent.isMenuActive"
        class="grey--text text-caption"
      >
        (+{{ value.length - 1 }})
      </span>
    </template>
  </v-combobox>
</template>

<script>
export default {
  name: 'tagFilter',
  props: {
    label: String,
    value: [],
    items: []
  },
  methods: {
    removeTag (chip) {
      this.$emit(
        'input',
        this.value.filter((c) => c !== chip)
      )
    },
    setValue (newValue) {
      this.$emit('input', newValue)
    }
  }
}
</script>
