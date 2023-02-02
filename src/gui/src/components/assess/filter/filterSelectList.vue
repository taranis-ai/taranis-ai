<template>
  <v-list dense class="py-0">
    <v-list-item-group
      active-class="selected"
      :value="value"
      @change="setValue"
      multiple
      class="filter-list"
    >
      <template>
        <v-list-item
          v-for="item in items"
          :key="item.type"
          class="extra-dense"
          :ripple="false"
          :value="item.type"
        >
          <template v-slot:default="{ active }">
            <!-- Item -->
            <v-list-item-icon class="mr-2">
              <v-icon small color="grey" class="filter-icon mt-auto mb-auto">
                {{ item.icon }}
              </v-icon>
            </v-list-item-icon>

            <!-- Label -->
            <v-list-item-content class="py-1 mt-auto mb-auto">
              {{ item.label }}
            </v-list-item-content>

            <!-- Checkmark -->
            <v-list-item-action>
              <v-icon
                v-if="active"
                small
                class="mt-auto mb-auto dark-grey--text text--lighten-3"
              >
                mdi-check-bold
              </v-icon>
            </v-list-item-action>
          </template>
        </v-list-item>
      </template>
    </v-list-item-group>
  </v-list>
</template>

<script>
export default {
  name: 'filterSelectList',
  props: {
    value: {
      type: Array,
      default: () => []
    },
    items: {
      type: Array,
      default: () => []
    }
  },
  methods: {
    setValue (newValue) {
      this.$emit('input', newValue)
    }
  }
}
</script>
