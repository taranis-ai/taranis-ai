<template>
  <v-dialog v-model="modelValue" width="400">
    <v-card>
      <v-btn outlined color="#d18e8e" class="close-btn" @click="onCancel">
        <v-icon>mdi-close</v-icon>
      </v-btn>

      <v-container>
        <v-row>
          <v-col cols="12">
            <h2
              class="font-weight-regular dark-grey--text text-capitalize pt-0"
            >
              Unsaved Changes
            </h2>
          </v-col>
        </v-row>

        <v-row class="pb-4">
          <v-col cols="12" class="pl-5 d-flex flex-column align-start">
            <p>
              You have unsaved changes. Do you want to save before continuing?
            </p>
            <v-row class="mt-4">
              <v-btn outlined color="gray" class="mr-4" @click="onCancel">
                <v-icon left>mdi-close</v-icon>
                Cancel
              </v-btn>
              <v-spacer></v-spacer>
              <v-btn color="primary" @click="onSaveAndContinue">
                <v-icon left>mdi-content-save</v-icon>
                Save and Continue
              </v-btn>
            </v-row>
          </v-col>
        </v-row>
      </v-container>
    </v-card>
  </v-dialog>
</template>

<script>
import { defineComponent } from 'vue'
export default defineComponent({
  name: 'PopupDirty',
  props: {
    modelValue: {
      type: Boolean,
      required: true
    }
  },
  emits: ['update:modelValue', 'saveAndContinue', 'cancel'],
  setup(props, { emit }) {
    function onCancel() {
      emit('cancel')
      emit('update:modelValue', false)
    }

    function onSaveAndContinue() {
      emit('saveAndContinue')
      emit('update:modelValue', false)
    }

    return {
      onCancel,
      onSaveAndContinue
    }
  }
})
</script>

<style scoped>
.close-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  min-width: 32px;
  min-height: 32px;
}
.font-weight-regular {
  font-weight: 400;
}
.dark-grey--text {
  color: #333333;
}
.awake-red-color--text {
  color: #d18e8e;
}
</style>
