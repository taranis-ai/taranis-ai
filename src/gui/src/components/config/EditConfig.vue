<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <v-form
      @submit.prevent="handleSubmit"
      id="edit_config_form"
      ref="config_form"
      class="px-4"
    >
      <v-row class="mb-4 grey pt-3 pb-3 rounded">
        <v-btn type="submit" color="success" class="ml-4"> Submit </v-btn>
      </v-row>
      <v-row no-gutters v-for="item in format" :key="item.name">
        <v-col cols="12" v-if="item.parent">
          <v-text-field
            v-model="formData[item.parent][item.name]"
            :label="item.label"
            :required="item.required"
            :disabled="item['disabled'] !== undefined"
            :type="item.type"
            v-if="item.type === 'text' || item.type === 'number'"
          ></v-text-field>
        </v-col>
        <v-col cols="12" v-else>
          <v-text-field
            v-model="formData[item.name]"
            :label="item.label"
            :required="item.required"
            :disabled="item['disabled'] !== undefined"
            :type="item.type"
            v-if="item.type === 'text' || item.type === 'number'"
          ></v-text-field>
        </v-col>
        <v-textarea
          v-model="formData[item.name]"
          :label="item.label"
          :required="item.required"
          :disabled="item['disabled'] !== undefined"
          :type="item.type"
          v-if="item.type === 'textarea'"
        ></v-textarea>
        <v-select
          v-model="formData[item.name]"
          :label="item.label"
          :required="item.required"
          :disabled="item['disabled'] !== undefined"
          :items="item.options"
          v-if="item.type === 'select' && item.options"
        ></v-select>
        <v-col cols="12" v-if="item.type === 'table'">
          <v-data-table
            :label="item.label"
            :headers="item.headers"
            :show-select="item['disabled'] === undefined"
            :items="item.items"
            :hide-default-footer="item.items.length < 10"
            v-model="formData[item.name]"
          ></v-data-table>
        </v-col>
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
    },
    formFormat: {
      type: Array,
      required: false
    }
  },
  computed: {
    formData() {
      return this.configData
    },
    format() {
      if (this.formFormat) {
        return this.formFormat
      }
      return this.flattenObject(this.formData, null)
    }
  },
  methods: {
    handleSubmit() {
      if (!this.$refs.config_form.validate()) {
        return
      }
      this.$emit('submit', this.formData)
    },
    flattenObject(obj, parent) {
      let result = []
      let flat_obj = {}
      for (const key in obj) {
        if (typeof obj[key] === 'object') {
          result = result.concat(this.flattenObject(obj[key], key))
        } else {
          flat_obj = {
            name: key,
            type: typeof obj[key] === 'number' ? 'number' : 'text',
            label: key
          }
          if (parent) {
            flat_obj.parent = parent
          }
          if (key === 'id') {
            flat_obj.disabled = true
            result.unshift(flat_obj)
            continue
          }
          result.push(flat_obj)
        }
      }
      return result
    }
  }
}
</script>
