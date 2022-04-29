<template>
  <v-card>
    <v-container>
      <v-row>
        <v-col cols="12">
          <h2 class="font-weight-bold dark-grey--text text-capitalize pt-3">
            <v-icon color="awake-red-color" class="mb-1">
              mdi-alert-octagon-outline
            </v-icon>
            <span class="awake-red-color--text">
              Delete News Item: <br />
            </span>
            "{{ newsItem.title }}"
          </h2>
          This action deletes the news item completely and it will no longer
          appear in other topics. Would you like to continue and delete the item
          permanently?
        </v-col>
      </v-row>
    </v-container>

    <v-divider></v-divider>

    <v-card-actions class="mt-3">
      <v-spacer></v-spacer>
      <v-btn
        color="awake-red-color darken-1"
        outlined
        @click="$emit('input', false)"
        class="text-lowercase pr-4"
      >
        <v-icon left class="red-icon">$awakeClose</v-icon>
        abort
      </v-btn>
      <v-btn
        color="primary"
        dark
        depressed
        @click="emitDeleteAction()"
        class="text-lowercase selection-toolbar-btn pr-4"
      >
        <v-icon left>mdi-check</v-icon>
        delete
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'PopupDeleteItem',
  props: {
    value: Boolean,
    newsItem: {}
  },
  methods: {
    ...mapActions('assess', ['deleteNewsItem']),

    emitDeleteAction () {
      this.$emit('deleteItem')
      // Close Popup
      this.$emit('input', false)
    }
  }
}
</script>
