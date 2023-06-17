<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <v-form
      id="edit_config_form"
      ref="config_form"
      class="px-4"
      @submit.prevent="handleSubmit"
    >
      <v-row class="mb-4 grey pt-3 pb-3 rounded">
        <v-btn type="submit" color="success" class="ml-4"> Submit </v-btn>
      </v-row>
      <v-row v-for="item in format" :key="item.name" no-gutters>
        <v-col v-if="item.parent" cols="12">
          <v-text-field
            v-if="item.type === 'text' || item.type === 'number'"
            v-model="formData[item.parent][item.name]"
            :label="item.label"
            :required="item.required"
            :disabled="item['disabled']"
            :type="item.type"
          ></v-text-field>
        </v-col>
        <v-col v-else cols="12">
          <v-text-field
            v-if="item.type === 'text' || item.type === 'number'"
            v-model="formData[item.name]"
            :label="item.label"
            :required="item.required"
            :disabled="item['disabled']"
            :type="item.type"
          ></v-text-field>
        </v-col>
        <v-textarea
          v-if="item.type === 'textarea'"
          v-model="formData[item.name]"
          :label="item.label"
          :required="item.required"
          :disabled="item['disabled']"
          :type="item.type"
        ></v-textarea>
        <v-select
          v-if="item.type === 'select' && item.options"
          v-model="formData[item.name]"
          :label="item.label"
          :required="item.required"
          :disabled="item['disabled']"
          :items="item.options"
        ></v-select>
        <v-switch
          v-if="item.type === 'switch'"
          v-model="formData[item.name]"
          :label="item.label"
          :disabled="item['disabled']"
          true-value="true"
          false-value="false"
        ></v-switch>

        <v-col
          v-if="item.type === 'table' && item.items !== undefined"
          cols="12"
        >
          <v-data-table
            v-model="formData[item.name]"
            :headers="item.headers"
            :show-select="!item['disabled']"
            :items="item.items"
          >
            <template #top>
              <v-row justify="space-between">
                <v-col md="4">
                  <h2 class="ml-4">{{ item.label }}</h2>
                </v-col>
                <v-col md="1">
                  <v-btn v-if="item.addButton" @click="addItem(item.name)">
                    Add
                  </v-btn>
                </v-col>
              </v-row>
            </template>
            <template v-if="item.items.length < 10" #bottom />
          </v-data-table>
        </v-col>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
export default {
  name: 'EditConfig',
  props: {
    configData: {
      type: Object,
      required: true
    },
    formFormat: {
      type: Array,
      required: false,
      default: null
    }
  },
  emits: ['submit'],
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
    addItem(name) {
      const newRow = {}
      const headers = this.format.find((row) => row.name === name).headers
      headers.forEach((header) => {
        newRow[header.value] =
          header.type === 'number' ? 0 : `new${header.value}`
      })
      this.formData[name].push(newRow)
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
