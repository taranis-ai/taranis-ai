<template>
    <v-container fluid class="view">
        <v-row class="view-panel" no-gutters>
            <slot name="panel"></slot>
        </v-row>
        <v-row class="view-content" no-gutters>
            <slot name="content"></slot>
        </v-row>
    </v-container>
</template>

<script>
export default {
  name: 'ViewLayout',
  data: () => ({

  }),
  methods: {
  }
}
</script>
