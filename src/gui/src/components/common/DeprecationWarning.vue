<template>
  <v-card title="Deprecation Warning" class="blink">
    <v-card-text>
      This item component is deprecated and will be removed in the future.
    </v-card-text>
  </v-card>
</template>

<style scoped>
@keyframes colorchange {
  0% {
    background-color: #ffff00;
  }
  50% {
    background-color: #ffee00;
  }
  100% {
    background-color: #ffff00;
  }
}

.blink {
  animation: colorchange 2s infinite;
}
</style>
