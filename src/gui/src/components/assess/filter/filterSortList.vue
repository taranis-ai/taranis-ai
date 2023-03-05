<template>
  <v-list dense class="py-0">
    <v-list-item-group
      v-model="selected"
      active-class="selected"
      class="filter-list"
      mandatory
    >
        <v-list-item
          v-for="item in orderOptions"
          :key="item.title"
          class="extra-dense"
          :ripple="false"
          :value="item.type + '_' + item.direction"
          @click.native.capture="changeDirection($event, item)"
        >
          <template v-slot:default="{ active }">
            <v-list-item-icon class="mr-2">
              <v-icon small color="grey" class="filter-icon mt-auto mb-auto">
                {{ item.icon }}
              </v-icon>
            </v-list-item-icon>

            <v-list-item-content class="py-1 mt-auto mb-auto">
              {{ item.label }}
            </v-list-item-content>

            <v-list-item-action>
              <v-icon
                v-if="active"
                :class="[
                  'mt-auto',
                  'mb-auto',
                  'dark-grey--text',
                  'text--lighten-3',
                  {
                    asc: item.direction === 'ASC',
                    desc: item.direction === 'DESC'
                  }
                ]"
              >
                mdi-chevron-up
              </v-icon>
            </v-list-item-action>
          </template>
        </v-list-item>
    </v-list-item-group>
  </v-list>
</template>

<script>
export default {
  name: 'filterSortList',
  props: {
    value: {},
    items: []
  },
  data: function() {
    return {
      orderOptions: this.items
    }
  },
  computed: {
    selected: {
      get () {
        return this.value
      },
      set (newValue) {
        this.$emit('input', newValue)
      }
    }
  },
  methods: {
    changeDirection (event, item) {
      event.preventDefault()
      this.orderOptions.forEach((option) => {
        if (option.type === item.type) {
          option.direction = option.direction === 'ASC' ? 'DESC' : 'ASC'
        }
      })
    }
  }
}
</script>
