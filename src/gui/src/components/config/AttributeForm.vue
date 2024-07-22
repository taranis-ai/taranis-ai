<template>
  <v-container fluid class="mt-5 pt-0">
    <span v-if="edit" class="ml-2">ID: {{ attribute.id }}</span>
    <v-form id="form" ref="form" validate-on="submit" @submit.prevent="submit">
      <v-row no-gutters>
        <v-col cols="12" class="pa-1">
          <v-text-field
            v-model="attribute.name"
            label="Name"
            name="name"
            type="text"
            :rules="[rules.required]"
          />
        </v-col>
        <v-col cols="12" class="pa-1">
          <v-textarea
            v-model="attribute.description"
            label="Description"
            name="description"
            type="text"
            :rules="[rules.required]"
          />
        </v-col>
        <v-col cols="12" class="pa-1">
          <v-text-field
            v-model="attribute.default_value"
            label="Default Value"
            name="default_value"
            type="text"
          />
        </v-col>
        <v-col cols="12" class="pa-1">
          <v-select
            v-model="attribute.type"
            label="Type"
            :items="attribute_types"
            clearable
            :rules="[rules.required]"
            menu-icon="mdi-chevron-down"
          />
        </v-col>
        <v-col v-if="attribute.type === 'ENUM'" cols="12" class="pl-1">
          <attributes-table
            v-model="attribute.attribute_enums"
            :header-filter="['description', 'value', 'actions', 'order']"
            :order="true"
          />
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-btn type="submit" block color="success" class="mt-5"> Submit </v-btn>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
import { ref, watch } from 'vue'
import AttributesTable from '@/components/common/AttributesTable.vue'

export default {
  name: 'AttributeForm',
  components: {
    AttributesTable
  },
  props: {
    attributeProp: {
      type: Object,
      required: true
    },
    edit: {
      type: Boolean,
      required: true,
      default: false
    }
  },
  emits: ['submit'],
  setup(props, { emit }) {
    const form = ref(null)

    const attribute = ref(props.attributeProp)

    const rules = {
      required: (value) => Boolean(value) || 'Required.'
    }

    const attribute_enum_headers = [
      { title: 'Description', key: 'description', sortable: true },
      { title: 'Value', key: 'value', sortable: true },
      { title: 'Actions', key: 'actions', align: 'right', sortable: false }
    ]

    const attribute_types = [
      'STRING',
      'NUMBER',
      'BOOLEAN',
      'RADIO',
      'ENUM',
      'TEXT',
      'RICH_TEXT',
      'DATE',
      'TIME',
      'DATE_TIME',
      'LINK',
      'ATTACHMENT',
      'TLP',
      'CVE',
      'CPE',
      'CVSS',
      'STORY'
    ]

    async function submit() {
      const { valid } = await form.value.validate()
      if (!valid) {
        return
      }

      console.debug(attribute.value)

      emit('submit', attribute.value)
    }

    function deleteItem(item) {
      const index = attribute.value.attribute_enums.indexOf(item)
      console.debug(`Deleting item at index: ${index}`)
      attribute.value.attribute_enums.splice(index, 1)
    }

    watch(
      () => props.attributeProp,
      (a) => {
        attribute.value = a
      }
    )

    return {
      form,
      rules,
      attribute,
      attribute_enum_headers,
      attribute_types,
      deleteItem,
      submit
    }
  }
}
</script>
