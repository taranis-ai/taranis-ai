<template>
  <div class="my-4 w-50">
    <v-data-table
      :headers="headers"
      :items="filteredStoryAttributes"
      :items-per-page="5"
      :hide-default-footer="modelValue.length < 5"
      class="elevation-1"
      density="compact"
      data-testid="attributes-table"
    >
      <template #top>
        <v-row class="justify-center">
          <h4>Attributes</h4>
        </v-row>
        <v-row class="justify-space-between">
          <v-btn
            color="primary"
            density="compact"
            class="ml-5"
            text="Add New Key-Value"
            @click="showDialog = true"
            :disabled="disabled"
          />
          <v-switch
            v-if="filterAttributes"
            class="mr-4"
            label="show all attributes"
            v-model="showAllAttributes"
            density="compact"
            hide-details
            color="primary"
            data-testid="show-all-attributes"
          ></v-switch>
          <slot name="top"></slot>
        </v-row>
      </template>
      <template #item="{ item, index }">
        <tr>
          <td v-for="field in fields" :key="field">
            <v-text-field
              v-model="item[field]"
              density="compact"
              variant="outlined"
              @change="updateValue()"
              :disabled="disabled"
            ></v-text-field>
          </td>
          <td>
            <v-btn
              prepend-icon="mdi-delete"
              color="red"
              density="compact"
              class="mb-4"
              text="Delete"
              @click.stop="deleteItem(index)"
              :disabled="disabled"
            ></v-btn>
          </td>
        </tr>
      </template>
    </v-data-table>

    <v-dialog v-model="showDialog" persistent max-width="600px">
      <v-card>
        <v-card-title> Add a new entry </v-card-title>
        <v-card-text>
          <v-text-field
            v-for="field in fields"
            :key="field"
            v-model="newItem[field]"
            :label="field"
          />
        </v-card-text>
        <v-card-actions>
          <v-btn text @click="showDialog = false">Cancel</v-btn>
          <v-btn color="primary" text @click="addItem">Add</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Array, required: true, default: () => [] },
  headerFilter: { type: Array, default: () => ['key', 'value'] },
  order: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  filterAttributes: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])
const showDialog = ref(false)
const newItem = ref({})
const headers = ref([])

function headerTransform(key) {
  if (key === 'order') {
    return {
      title: 'Order',
      key: 'order',
      sortable: false,
      width: '90px'
    }
  }

  if (key === 'actions') {
    return {
      title: 'Actions',
      key: 'actions',
      sortable: false,
      width: '30px'
    }
  }

  return { title: key, key: key }
}

const showAllAttributes = ref(!props.filterAttributes)

const filteredStoryAttributes = computed(() => {
  if (showAllAttributes.value) {
    return props.modelValue
  }
  const filtered_attributes = props.modelValue.filter((attr) => {
    return (
      Object.prototype.hasOwnProperty.call(attr, 'key') &&
      attr.key !== 'sentiment' &&
      attr.key !== 'cybersecurity' &&
      attr.key !== 'TLP' &&
      !attr.key.includes('_BOT')
    )
  })
  return filtered_attributes
})

const fields = computed(() => {
  return props.headerFilter.filter(
    (key) => key !== 'actions' && key !== 'order'
  )
})

function resetNewItem() {
  fields.value.forEach((field) => {
    newItem.value[field] = ''
  })
  if (props.order) {
    newItem.value['index'] = props.modelValue.length
  }
}

function updateValue() {
  emit('update:modelValue', [...props.modelValue])
}

function addItem() {
  const updatedItems = [...props.modelValue, { ...newItem.value }]
  emit('update:modelValue', updatedItems)
  resetNewItem()
  showDialog.value = false
}

function deleteItem(index) {
  const updatedItems = [...props.modelValue]
  updatedItems.splice(index, 1)
  emit('update:modelValue', updatedItems)
}

if (props.headerFilter.length > 0) {
  headers.value = props.headerFilter.map((key) => headerTransform(key))
} else if (props.items.length > 0) {
  headers.value = Object.keys(props.items[0]).map((key) => headerTransform(key))
}
resetNewItem()
</script>
