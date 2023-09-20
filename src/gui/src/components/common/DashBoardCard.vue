<template>
  <v-col :cols="cols" class="pa-2 mb-8">
    <v-card class="mt-4 mx-auto">
      <slot name="title">
        <v-card-title>
          <router-link v-if="linkTo != '#'" :to="linkTo">
            {{ linkText }}
          </router-link>
          <span v-else class="title">{{ linkText }}</span>
          <v-divider class="my-2"></v-divider>
        </v-card-title>
      </slot>
      <slot name="card">
        <v-card-text class="pt-0">
          <slot name="content"></slot>
        </v-card-text>
      </slot>
    </v-card>
  </v-col>
</template>

<script>
export default {
  name: 'DashBoardCard',
  props: {
    linkTo: { type: String, default: '#' },
    linkText: { type: String, default: '/' },
    cols: { type: String, default: '4' }
  }
}
</script>
