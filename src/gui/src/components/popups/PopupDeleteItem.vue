<template>
  <v-card>
    <v-btn outlined color="#d18e8e" @click="$emit('close')">
      <v-icon>mdi-close</v-icon>
    </v-btn>

    <v-container>
      <v-row>
        <v-col cols="12">
          <h2 class="font-weight-regular dark-grey--text text-capitalize pt-0">
            "{{ title }}"
          </h2>
        </v-col>
      </v-row>

      <v-row class="pb-4">
        <v-row class="mt-4 mb-0">
          <v-col cols="12" sm="12" class="pl-5 d-flex flex-column align-start">
            <p>{{ message }}</p>

            <p class="awake-red-color--text">
              <v-icon color="awake-red-color" class="mb-1">
                mdi-alert-octagon-outline
              </v-icon>
              This action cannot be undone.
            </p>

            <v-btn outlined color="#d18e8e" @click="emitDeleteAction()">
              <v-icon>mdi-delete</v-icon>
              delete item
            </v-btn>
          </v-col>
        </v-row>
      </v-row>
    </v-container>
  </v-card>
</template>

<script>
export default {
  name: 'PopupDeleteItem',
  props: {
    title: {
      type: String,
      required: true
    },
    message: {
      type: String,
      default: 'This action deletes the item permanently.'
    }
  },
  emits: ['close', 'deleteItem'],
  setup(props, { emit }) {
    function emitDeleteAction() {
      emit('deleteItem')
      emit('close')
    }

    return {
      emitDeleteAction
    }
  }
}
</script>
