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
    <v-dialog v-model="dialog" width="auto" min-width="500px">
      <v-form ref="form" @submit.prevent="save">
        <v-card>
          <v-card-text>
            <v-text-field
              v-model="edited_attribute.value"
              :label="$t('form.name')"
              :rules="required"
            />

            <v-text-field
              v-model="edited_attribute.description"
              :label="$t('form.description')"
            />
            <v-text-field
              v-model="edited_attribute.index"
              type="number"
              label="Index"
            />
          </v-card-text>

          <v-card-actions>
            <v-btn
              color="green-darken-3"
              class="ml-4"
              variant="flat"
              type="submit"
            >
              {{ $t('button.save') }}
            </v-btn>
            <v-spacer></v-spacer>
            <v-btn
              color="red-darken-3"
              class="mr-4"
              variant="flat"
              @click="dialog = false"
            >
              {{ $t('button.cancel') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-form>
    </v-dialog>
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
    const dialog = ref(false)

    const attribute = ref(props.attributeProp)

    const rules = {
      required: (value) => Boolean(value) || 'Required.'
    }

    const edited_attribute = ref({
      index: attribute.value.length,
      attribute_id: -1,
      value: '',
      description: ''
    })

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

      emit('submit', attribute.value)
    }

    function deleteItem(item) {
      const index = attribute.value.attribute_enums.indexOf(item)
      console.debug(`Deleting item at index: ${index}`)
      attribute.value.attribute_enums.splice(index, 1)
    }

    function editItem(item) {
      edited_attribute.value = Object.assign({}, item)
      dialog.value = true
    }

    function save(item) {
      console.debug(item)
      dialog.value = false
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
      dialog,
      attribute,
      attribute_enum_headers,
      attribute_types,
      edited_attribute,
      save,
      deleteItem,
      editItem,
      submit
    }
  }
}
</script>
