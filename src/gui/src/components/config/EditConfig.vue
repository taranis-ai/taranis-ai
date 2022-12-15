<template>
  <v-container fluid class="mt-15">
    <v-form
      @submit.prevent="handleSubmit"
      id="edit_config_form"
      ref="config_form"
      class="px-4"
    >
      <v-row no-gutters v-for="(item, i) in formData" :key="i">
        <v-text-field
          v-model="formData[i]"
          :label="i"
          required
          v-if="typeof item === 'string'"
        ></v-text-field>
      </v-row>
      <v-row no-gutters>
        <v-btn type="submit" color="success" class="mr-4"> Submit </v-btn>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
export default {
  name: 'EditConfig',
  emits: ['submit'],
  props: {
    configData: {
      type: Object,
      required: true
    }
  },
  computed: {
    formData() {
      return this.configData
    }
  },
  methods: {
    handleSubmit() {
      if (!this.$refs.config_form.validate()) {
        return
      }
      this.$emit('submit', this.formData)
    }
  }
}
</script>
