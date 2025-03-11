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
          variant="outlined"
          :label="item.label"
          :rules="item.rules"
          :disabled="item['disabled']"
          :type="item.type"
          :bg-color="item.color"
        />
        <v-text-field
          v-if="item.type === 'date' && formData[item.flatKey]"
          :model-value="d(formData[item.flatKey], 'long')"
          variant="outlined"
          :disabled="item['disabled']"
          :label="item.label"
          :bg-color="item.color"
        />
        <v-textarea
          v-if="item.type === 'textarea'"
          v-model="formData[item.flatKey]"
          variant="outlined"
          :label="item.label"
          :rules="item.rules"
          :disabled="item['disabled']"
          :type="item.type"
        />
        <v-select
          v-if="item.type === 'select' && item.items"
          v-model="formData[item.flatKey]"
          variant="outlined"
          :label="item.label"
          :rules="item.rules"
          :disabled="item['disabled']"
          :items="item.items"
          clearable
          menu-icon="mdi-chevron-down"
        />
        <v-switch
          v-if="item.type === 'switch'"
          v-model="formData[item.flatKey]"
          variant="outlined"
          :label="item.label"
          :disabled="item['disabled']"
          true-value="true"
          false-value="false"
        />
        <v-list
          v-if="item.type === 'list'"
          variant="outlined"
          width="100%"
          :items="formData[item.flatKey]"
          :label="item.label"
          density="compact"
          :disabled="true"
        />
        <v-file-input
          v-if="item.type === 'file'"
          variant="outlined"
          :rules="item.rules"
          accept="image/png"
          :label="item.label"
          :placeholder="item.placeholder"
          :prepend-icon="item.icon"
          show-size
          @change="handleFileUpload(item.flatKey, $event)"
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
        <TimeIntervalFields
          v-if="item.type === 'cron_interval'"
          v-model="formData[item.flatKey]"
          :type="configType"
        />

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
                  <v-btn
                    v-if="item.addButton"
                    :text="$t('button.add')"
                    @click="addItem(item.name)"
                  />
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
      <v-btn
        block
        class="mt-3"
        type="submit"
        color="success"
        :text="$t('button.submit')"
      />
    </v-form>
  </v-card>
</template>

<script>
import TimeIntervalFields from '@/components/config/TimeIntervalFields.vue'
import { watch, computed, onUpdated, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  objectFromFormat,
  reconstructFormData,
  flattenFormData
} from '@/utils/helpers'

export default {
  name: 'EditConfig',
  components: {
    TimeIntervalFields
  },
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
    const route = useRoute()
    const configType = ref(null)
    const formData = ref(
      flattenFormData(props.configData, props.formFormat) ||
        objectFromFormat(props.formFormat)
    )

    const rulesDict = {
      required: (v) => Boolean(v) || 'Required',
      email: (v) => (v && /.+@.+\..+/.test(v)) || 'E-mail must be valid',
      filesize: (v) => {
        if (!v || !Array.isArray(v) || v.length === 0) return true
        return v[0].size < 2 * 1024 * 1024 || 'Filesize must be less than 2MB'
      },
      tlp: (v) =>
        ['red', 'amber', 'amber+strict', 'green', 'clear', undefined].includes(
          v
        ) ||
        'Invalid TLP allowed values: red, amber, amber+strict, green, clear',
      json: (v) => {
        if (!v || v.length === 0) return true
        try {
          JSON.parse(v)
          return true
        } catch (error) {
          return 'Invalid JSON format'
        }
      }
    }

    const { d } = useI18n()

    const validationStates = ref({})

    const handleSubmit = async () => {
      const { valid } = await config_form.value.validate()

      const cronValidation = Object.values(validationStates.value).every(
        (state) => state
      )

      if (!valid || !cronValidation) {
        return
      }

      emit('submit', reconstructFormData(formData.value, format.value))
    }
    const handleFileUpload = async (flatKey, event) => {
      if (!(event.target.files[0] instanceof Blob)) {
        return
      }

      const base64String = await new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.readAsDataURL(event.target.files[0])
        reader.onload = () => resolve(reader.result.split(',')[1])
        reader.onerror = (error) => reject(error)
      })
      formData.value[flatKey] = base64String
      return base64String
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

      const path = route.path
      if (path === '/config/sources') {
        configType.value = path.split('/').pop()
      }
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
      configType
    }
  }
}
</script>
