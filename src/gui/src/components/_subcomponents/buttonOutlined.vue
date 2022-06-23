<template>
  <v-tooltip open-delay="1000" bottom :disabled="!tooltip">
    <template v-slot:activator="{ on, attrs }">
      <!-- BUTTON -->
      <v-btn
        v-bind="attrs"
        v-on="on"
        outlined
        class="buttonOutlined"
        @click.native.capture="execute($event)"
        :color="color ? color : '#575757'"
        :class="[extraClass]"
        :style="{ borderColor: colorValue }"
      >
        <!-- ICON -->
        <v-icon
          v-if="icon"
          :style="color ? { fill: colorValue } : { fill: '#575757' }"
          >
          {{ icon }}
          </v-icon>
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
  },
  computed: {
    colorValue () {
      switch (this.color) {
        case 'primary':
          return '#7468e8'
        case 'secondary':
          return '#34a5e8'
        case 'accent':
          return '#6daed9'
        case 'info':
          return '#2196f3'
        case 'error':
          return '#ff5252'
        case 'success':
          return '#4caf50'
        case 'warning':
          return '#ffc107'
        case 'light-grey-1':
          return '#c9c9c9'
        case 'light-grey-2':
          return '#c8c8c8'
        case 'dark-grey':
          return '#575757'
        case 'topic-selected-bg':
          return '#f4f3fb'
        case 'topic-hot':
          return '#dbe868'
        case 'topic-header-bg':
          return '#edeac2'
        case 'awake-green-color':
          return '#77bb70'
        case 'awake-yellow-color':
          return '#e9c645'
        case 'awake-red-color':
          return '#d18e8e'
        case 'status-important':
          return '#dbe868'
        case 'status-unread':
          return '#7468e8'
        case 'status-error':
          return '#d18e8e'
        default:
          return '#c8c8c8'
      }
    }
  }
}
</script>
