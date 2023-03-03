<template>
  <v-col :cols="cols" class="pa-2 mb-8">
      <v-card class="mt-4 mx-auto" max-width="100%">
        <v-card-text class="pt-0">
          <router-link :to="linkTo" class="title">{{ linkText }}</router-link>
          <v-divider class="my-2"></v-divider>
          <slot name="content"></slot>
        </v-card-text>
      </v-card>
  </v-col>
</template>

<script>
export default {
  name: 'DashBoardCard',
  props: {
    linkTo: { type: String },
    linkText: { type: String },
    cols: { type: String, default: '4' }
  }
}
</script>
