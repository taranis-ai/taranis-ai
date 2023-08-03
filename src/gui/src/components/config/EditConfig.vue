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
            :rules="item.rules"
            :disabled="item['disabled']"
            :type="item.type"
          />
        </v-col>
        <v-col v-else cols="12">
          <v-text-field
            v-if="item.type === 'text' || item.type === 'number'"
            v-model="formData[item.name]"
            :label="item.label"
            :rules="item.rules"
            :disabled="item['disabled']"
            :type="item.type"
            :bg-color="item.color"
          />
        </v-col>
        <v-text-field
          v-if="item.type === 'date' && formData[item.name]"
          :model-value="d(formData[item.name], 'long')"
          :disabled="item['disabled']"
          :label="item.label"
          :bg-color="item.color"
        />
        <v-textarea
          v-if="item.type === 'textarea'"
          v-model="formData[item.name]"
          :label="item.label"
          :rules="item.rules"
          :disabled="item['disabled']"
          :type="item.type"
        />
        <v-select
          v-if="item.type === 'select' && item.options"
          v-model="formData[item.name]"
          :label="item.label"
          :rules="item.rules"
          :disabled="item['disabled']"
          :items="item.options"
        />
        <v-switch
          v-if="item.type === 'switch'"
          v-model="formData[item.name]"
          :label="item.label"
          :disabled="item['disabled']"
          true-value="true"
          false-value="false"
        />
        <v-list
          v-if="item.type === 'list'"
          width="100%"
          :items="formData[item.name]"
          :label="item.label"
          variant="outlined"
          density="compact"
          :disabled="true"
        />

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
import { watch } from 'vue'
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'

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
  setup(props, { emit }) {
    const config_form = ref(null)
    const formData = ref(props.configData)

    console.log(props.configData)
    const { d } = useI18n()

    const handleSubmit = () => {
      if (!config_form.value.validate()) {
        return
      }
      emit('submit', formData.value)
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

    const flattenObject = (obj, parent) => {
      let result = []
      let flat_obj = {}
      for (const key in obj) {
        if (typeof obj[key] === 'object') {
          result = result.concat(flattenObject(obj[key], key))
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

    const format = computed(() => {
      if (props.formFormat) {
        return props.formFormat
      }
      return flattenObject(formData.value, null)
    })

    watch(
      () => props.configData,
      (newVal) => {
        formData.value = newVal
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
