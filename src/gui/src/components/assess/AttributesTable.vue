<template>
  <v-container class="d-flex mx-0 my-0">
    <v-data-table
      :headers="headers"
      :items="modelValue"
      :items-per-page="5"
      class="elevation-1"
    >
      <template #top>
        <v-row class="justify-center">
          <h3>Attributes</h3>
        </v-row>
        <v-row class="justify-center">
          <v-btn
            color="primary"
            text="Add New Key-Value"
            max-width="50%"
            class=""
            @click="showDialog = true"
          />
        </v-row>
      </template>
      <template #item="{ item }">
        <tr>
          <td>
            <v-text-field
              v-model="item.key"
              dense
              solo
              flat
              hide-details
              @change="updateValue()"
            ></v-text-field>
          </td>
          <td>
            <v-text-field
              v-model="item.value"
              dense
              solo
              flat
              hide-details
              @change="updateValue()"
            ></v-text-field>
          </td>
          <td>
            <v-tooltip left text="Delete">
              <template #activator="{ props: tprops }">
                <v-icon
                  v-bind="tprops"
                  color="red"
                  icon="mdi-delete"
                  @click.stop="deleteItem(item)"
                />
              </template>
            </v-tooltip>
          </td>
        </tr>
      </template>
    </v-data-table>

    <v-dialog v-model="showDialog" persistent max-width="600px">
      <v-card>
        <v-card-title> Add a new key-value pair </v-card-title>
        <v-card-text>
          <v-text-field v-model="newItem.key" label="Key"></v-text-field>
          <v-text-field v-model="newItem.value" label="Value"></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn text @click="showDialog = false">Cancel</v-btn>
          <v-btn color="primary" text @click="addItem">Add</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: { type: Array, required: true, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])
const showDialog = ref(false)
const newItem = ref({ key: '', value: '' })
const headers = [
  { title: 'Key', key: 'key' },
  { title: 'Value', key: 'value' },
  { title: 'Actions', key: 'actions', sortable: false, width: '30px' }
]

function updateValue() {
  emit('update:modelValue', [...props.modelValue])
}

function addItem() {
  const updatedItems = [...props.modelValue, { ...newItem.value }]
  emit('update:modelValue', updatedItems)
  newItem.value = { key: '', value: '' }
  showDialog.value = false
}

function deleteItem(index) {
  const updatedItems = [...props.modelValue]
  updatedItems.splice(index, 1)
  emit('update:modelValue', updatedItems)
}
</script>
