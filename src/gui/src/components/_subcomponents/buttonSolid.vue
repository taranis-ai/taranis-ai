<template>
  <v-tooltip open-delay="1000" bottom :disabled="!tooltip">
    <template v-slot:activator="{ on, attrs }">
      <!-- BUTTON -->
      <v-btn
        v-bind="attrs"
        v-on="on"
        dark
        depressed
        :color="color ? color : 'primary'"
        class="buttonSolid"
        :class="[extraClass]"
        @click.native.capture="execute($event)"
      >
        <!-- ICON -->
        <v-icon v-if="icon"
        :left="label"
        >{{ icon }}</v-icon>
        <!-- LABEL -->
        {{ label }}
      </v-btn>
    </template>

    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>

<script>
export default {
  name: 'buttonOutlined',
  props: {
    color: String,
    label: String,
    icon: String,
    extraClass: String,
    tooltip: String
  },
  methods: {
    execute (event) {
      event.stopPropagation()
      this.$emit('click', event)
    }
  }
}
</script>
