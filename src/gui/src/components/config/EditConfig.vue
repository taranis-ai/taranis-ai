<template>
  <v-card class="ma-3 mt-5 pa-3 pt-0">
    <v-form
      id="edit_config_form"
      ref="config_form"
      class="px-4"
      @submit.prevent="handleSubmit"
    >
      <v-card-title class="bg-grey-lighten-2 mb-5">
        <span v-if="title" class="ml-5"> {{ title }}</span>
        <slot name="titlebar"></slot>
      </v-card-title>

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
        <v-file-input
          v-if="item.type === 'icon'"
          @change="handleFileUpload(item.type, $event)"
          :rules="[rules.filesize]"
          accept="image/png"
          :label="item.label"
          placeholder="Pick an avatar"
          prepend-icon="mdi-camera"
        ></v-file-input>
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

        <v-col v-if="item.type === 'table'" cols="12" class="mt-1 mb-2">
          <v-data-table
            v-model="formData[item.flatKey]"
            :headers="item.headers"
            :search="search[item.flatKey]"
            :show-select="!item['disabled']"
            :group-by="item.groupBy"
            :items="item.items || formData[item.flatKey]"
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
              <v-row no-gutters>
                <v-text-field
                  v-model="search[item.flatKey]"
                  append-inner-icon="mdi-magnify"
                  density="compact"
                  label="Search"
                  single-line
                  class="mr-4"
                  hide-details
                />
              </v-row>
            </template>
            <template
              v-if="typeof item.items !== 'undefined' && item.items.length < 10"
              #bottom
            />
          </v-data-table>
        </v-col>
      </v-row>
      <slot name="additionalData"></slot>
      <v-btn block class="mt-3" type="submit" color="success"> Submit </v-btn>
    </v-form>
  </v-card>
</template>

<script>
import { watch, computed, onUpdated, onMounted } from 'vue'
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
    },
    title: {
      type: String,
      required: false,
      default: null
    }
  },
 
  emits: ['submit'],
  setup(props, { emit }) {
    const config_form = ref(null)
    const search = ref({})
    const formData = ref(
      flattenFormData(props.configData, props.formFormat) ||
        objectFromFormat(props.formFormat)
    )

    const rulesDict = {
      required: (v) => Boolean(v) || 'Required',
      email: (v) => /.+@.+\..+/.test(v) || 'E-mail must be valid'
    }

    const { d } = useI18n()

    const handleSubmit = async () => {
      const { valid } = await config_form.value.validate()
      if (!valid) {
        return
      }

      emit('submit', reconstructFormData(formData.value, format.value))
    }

    const rules = {
      filesize: (file) =>  file.length ? file[0].size <  2 * 1024 * 1024 || 'Avatar size must be less than 2 MB!': true
    }
   

    const handleFileUpload = async (type, event) => {
      const base64String =  await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(event.target.files[0]);
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = error => reject(error);
      });
      formData.value[type] = base64String
      return base64String; 
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

    const getRules = (rules) => {
      if (!rules) {
        return []
      }
      return rules
        .filter((rule) => rulesDict[rule])
        .map((rule) => rulesDict[rule])
    }

    const selectedParameters = computed(() => {
      if (!formData.value.type || !props.parameters) {
        return []
      }
      if (!props.parameters[formData.value.type]) {
        return [] 
      }
      return props.parameters[formData.value.type]
    })

    const format = computed(() => {
      const formats = [...props.formFormat, ...selectedParameters.value]
      return formats.map((item) => {
        return {
          ...item,
          flatKey: item.parent ? `${item.parent}.${item.name}` : item.name,
          rules: getRules(item.rules)
        }
      })
    })

    formData.value =
      flattenFormData(props.configData, format.value) ||
      objectFromFormat(format.value)

    onUpdated(() => {
      config_form.value.scrollIntoView({ behavior: 'smooth' })
    })

    onMounted(() => {
      config_form.value.scrollIntoView({ behavior: 'smooth' })
    })

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
      search,
      addItem,
      handleSubmit,
      handleFileUpload, 
      rules      
    }
  }
}
</script>
