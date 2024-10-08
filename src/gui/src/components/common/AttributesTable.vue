<template>
  <v-container class="d-flex mx-0 my-0">
    <v-data-table
      :headers="headers"
      :items="modelValue"
      :items-per-page="5"
      :hide-default-footer="modelValue.length < 5"
      class="elevation-1"
    >
      <template #top>
        <v-row class="justify-center">
          <h4>Attributes</h4>
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
      <template #item="{ item, index }">
        <tr>
          <td v-for="field in fields" :key="field">
            <v-text-field
              v-model="item[field]"
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
                  @click.stop="deleteItem(index)"
                />
              </template>
            </v-tooltip>
          </td>
          <td v-if="order">
            <v-btn
              density="compact"
              variant="flat"
              icon="mdi-arrow-up"
              :disabled="index === 0"
              @click="setIndex(item, index - 1)"
            />
            <v-btn
              density="compact"
              variant="flat"
              icon="mdi-arrow-down"
              :disabled="index === modelValue.length - 1"
              @click="setIndex(item, index + 1)"
            />
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
  </v-container>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Array, required: true, default: () => [] },
  headerFilter: { type: Array, default: () => ['key', 'value'] },
  order: { type: Boolean, default: false }
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

function setIndex(item, newIndex) {
  const updatedItems = [...props.modelValue]
  const currentIndex = updatedItems.indexOf(item)
  if (currentIndex !== -1 && newIndex >= 0 && newIndex < updatedItems.length) {
    const itemToSwap = updatedItems[newIndex]
    updatedItems[newIndex] = item
    updatedItems[currentIndex] = itemToSwap

    // Update index field
    updatedItems[newIndex].index = newIndex
    updatedItems[currentIndex].index = currentIndex

    emit('update:modelValue', updatedItems)
  }
}

if (props.headerFilter.length > 0) {
  headers.value = props.headerFilter.map((key) => headerTransform(key))
} else if (props.items.length > 0) {
  headers.value = Object.keys(props.items[0]).map((key) => headerTransform(key))
}
resetNewItem()
</script>
