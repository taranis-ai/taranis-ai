<template>
  <v-combobox
    :value="value"
    :items="items"
    :label="label"
    :placeholder="placeholder"
    @input="setValue"
    return-object
    :item-text="getAttributeName()"
    multiple
    outlined
    dense
    hide-selected
    append-icon="mdi-chevron-down"
    class="pl-0"
    hide-details
    search-input
  >
    <template v-slot:item="{ item }">
      <span class="dropdown-list-item">
        {{ item[getAttributeName()] }}
      </span>
    </template>
    <template v-slot:selection="{ parent, item, index }">
      <v-chip
        small
        v-if="index < 1 && !parent.isMenuActive"
        label
        color="grey--lighten-4"
        close
        close-icon="$newsItemActionRemove"
        class="pa-2 ml-0 mt-1"
        @click:close="parent.selectItem(item)"
      >
        <span class="text-truncate text-capitalize topics-chip">{{
          item[getAttributeName()]
        }}</span>
      </v-chip>

      <v-chip
        small
        v-else-if="parent.isMenuActive"
        label
        color="grey--lighten-4"
        close
        close-icon="$newsItemActionRemove"
        class="pa-2 ml-0 mt-1"
        @click:close="parent.selectItem(item)"
      >
        <span class="text-truncate text-capitalize topics-chip">
          {{ item[getAttributeName()] }}
        </span>
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
  name: 'dropdownSelection',
  props: {
    label: String,
    placeholder: String,
    attribute: String,
    value: [],
    items: []
  },
  methods: {
    setValue (newValue) {
      this.$emit('input', newValue)
    },
    getAttributeName () {
      return this.attribute ? this.attribute : 'title'
    }
  }
}
</script>
