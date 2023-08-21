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
        <v-text-field
          v-if="item.type === 'text' || item.type === 'number'"
          v-model="formData[item.flatKey]"
          :label="item.label"
          :rules="item.rules"
          :disabled="item['disabled']"
          :type="item.type"
          :bg-color="item.color"
        />
        <v-text-field
          v-if="item.type === 'date' && formData[item.flatKey]"
          :model-value="d(formData[item.flatKey], 'long')"
          :disabled="item['disabled']"
          :label="item.label"
          :bg-color="item.color"
        />
        <v-textarea
          v-if="item.type === 'textarea'"
          v-model="formData[item.flatKey]"
          :label="item.label"
          :rules="item.rules"
          :disabled="item['disabled']"
          :type="item.type"
        />
        <v-select
          v-if="item.type === 'select' && item.items"
          v-model="formData[item.flatKey]"
          :label="item.label"
          :rules="item.rules"
          :disabled="item['disabled']"
          :items="item.items"
        />
        <v-switch
          v-if="item.type === 'switch'"
          v-model="formData[item.flatKey]"
          :label="item.label"
          :disabled="item['disabled']"
          true-value="true"
          false-value="false"
        />
        <v-list
          v-if="item.type === 'list'"
          width="100%"
          :items="formData[item.flatKey]"
          :label="item.label"
          variant="outlined"
          density="compact"
          :disabled="true"
        />
        <v-row
          v-if="item.type === 'checkbox' && item.items !== undefined"
          no-gutters
        >
          <v-col v-for="checkbox in item.items" :key="checkbox.label" cols="3">
            <v-checkbox
              v-model="formData[item.flatKey]"
              :label="checkbox.label"
              :value="checkbox.value"
              :rules="item.rules"
            />
          </v-col>
        </v-row>

        <v-col
          v-if="item.type === 'table' && item.items !== undefined"
          cols="12"
          class="mt-1 mb-2"
        >
          <v-data-table
            v-model="formData[item.flatKey]"
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
import { watch, computed } from 'vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  objectFromFormat,
  reconstructFormData,
  flattenFormData
} from '@/utils/helpers'

export default {
  name: 'EditConfig',
  props: {
    configData: {
      type: Object,
      required: false,
      default: null
    },
    formFormat: {
      type: Array,
      required: true
    },
    parameters: {
      type: Object,
      required: false,
      default: null
    }
  },
  emits: ['submit'],
  setup(props, { emit }) {
    const config_form = ref(null)
    const formData = ref(
      flattenFormData(props.configData, props.formFormat) ||
        objectFromFormat(props.formFormat)
    )

    console.log(formData.value)
    const { d } = useI18n()

    const handleSubmit = () => {
      if (!config_form.value.validate()) {
        return
      }
      emit('submit', reconstructFormData(formData.value, format.value))
    }

    const addItem = (name) => {
      const newRow = {}
      const headers = format.value.find((row) => row.name === name).headers
      headers.forEach((header) => {
        newRow[header.value] =
          header.type === 'number' ? 0 : `new${header.value}`
      })
      formData.value[name].push(newRow)
    }

    const selectedParameters = computed(() => {
      if (!formData.value.type || !props.parameters) {
        return []
      }
      return props.parameters[formData.value.type]
    })

    const format = computed(() => {
      const formats = [...props.formFormat, ...selectedParameters.value]
      return formats.map((item) => {
        return {
          ...item,
          flatKey: item.parent ? `${item.parent}.${item.name}` : item.name
        }
      })
    })

    formData.value =
      flattenFormData(props.configData, format.value) ||
      objectFromFormat(format.value)

    watch(
      () => props.configData,
      (newVal) => {
        formData.value =
          flattenFormData(newVal, format.value) ||
          objectFromFormat(format.value)
      }
    )

    return {
      d,
      config_form,
      formData,
      format,
      addItem,
      handleSubmit
    }
  }
}
</script>
