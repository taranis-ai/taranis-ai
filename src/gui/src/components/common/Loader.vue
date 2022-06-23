<template>
<v-container style="height: 400px;">
      <v-row
        align-content="center"
        justify="center"
      >
      <v-col cols="12" class="text-center">
          <v-progress-circular
            :size="20"
            :width="3"
            indeterminate
            color="primary"
            ></v-progress-circular>
            <!-- color="dark-grey lighten-4" -->
        </v-col>
        <v-col
          class="text-subtitle-1 text-center dark-grey--text text--lighten-2"
          cols="12"
        >
          {{ label }}
        </v-col>
        
      </v-row>
    </v-container>
</template>

<script>
export default {
  name: 'loader',
  props: {
    label: String
  },
  methods: {}
}
</script>
