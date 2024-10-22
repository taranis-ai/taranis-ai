<template>
    <v-dialog v-bind:model-value="dialog" width="auto" min-width="500px" @update:model-value="updateDialog">
      <v-card>
        <v-card-title class="headline">{{ $t('unsavedChanges.title') }}</v-card-title>
        <v-card-text>{{ $t('unsavedChanges.message') }}</v-card-text>
        <v-card-actions>
          <v-btn color="secondary" @click="closeDialog">{{ $t('button.cancel') }}</v-btn>
          <v-btn color="primary" @click="saveAndContinue">{{ $t('button.saveAndContinue') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </template>
  
  <script>
  export default {
    props: {
      modelValue: {
        type: Boolean,
        required: true
      }
    },
    emits: ['update:modelValue', 'saveAndContinue'],
    methods: {
      closeDialog() {
        this.$emit('update:modelValue', false); // Emit to close the dialog
      },
      saveAndContinue() {
        this.$emit('saveAndContinue'); // Emit save and continue action
        this.$emit('update:modelValue', false); // Close the dialog after saving
      },
      updateDialog(newValue) {
        this.$emit('update:modelValue', newValue); // Emit the update to the parent component
      }
    }
  }
  </script>
  