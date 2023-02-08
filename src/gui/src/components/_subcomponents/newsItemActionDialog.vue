<template>
  <v-dialog v-model="dialog" width="600">
    <template v-slot:activator="{ on: dialog }">
      <v-tooltip open-delay="1000" bottom :disabled="!tooltip">
        <template v-slot:activator="{ on: tooltip }">
          <v-btn
            v-on="{ ...tooltip, ...dialog }"
            icon
            tile
            class="news-item-action"
            :class="[{ active: active ? active : false }, extraClass]"
          >
            <v-icon color="black">{{ icon }}</v-icon>
            <span v-if="buttonText">{{ buttonText }}</span>
          </v-btn>
        </template>
        <span>{{ tooltip }}</span>
      </v-tooltip>
    </template>
    <slot />
  </v-dialog>
</template>

<script>
export default {
  name: 'newsItemActionDialog',
  emits: ['open', 'close'],
  data: () => ({
  }),
  props: {
    showDialog: { type: Boolean, default: false },
    active: Boolean,
    icon: String,
    extraClass: String,
    tooltip: String,
    buttonText: { type: String, default: '' }
  },
  computed: {
    dialog: {
      get() {
        return this.showDialog
      },
      set(value) {
        if (!value) {
          this.$emit('close')
        } else {
          this.$emit('open')
        }
      }
    }
  },
  methods: {}
}
</script>
