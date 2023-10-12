<template>
  <v-container>
    <v-toolbar flat color="white">
      <v-toolbar-title>{{ $t('attribute.attributes') }}</v-toolbar-title>
      <v-divider class="mx-4" inset vertical></v-divider>
      <v-spacer></v-spacer>
      <v-btn
        color="primary"
        dark
        class="mb-2"
        prepend-icon="mdi-plus"
        @click="dialog = true"
      >
        {{ $t('attribute.new_attribute') }}
      </v-btn>

      <v-dialog v-model="dialog" width="auto">
        <v-card>
          <v-card-title>
            {{ formTitle }}
          </v-card-title>

          <v-card-text>
            <v-combobox
              v-model="attribute_type"
              :items="attributeTemplates"
              item-title="name"
              :label="$t('attribute.attribute')"
            >
              <template #item="{ item, props }">
                <v-list-item v-bind="props">
                  <template #prepend>
                    <v-icon :icon="item.value.tag"></v-icon>
                  </template>
                </v-list-item>
              </template>
            </v-combobox>

            <v-text-field
              v-model="edited_attribute.title"
              :label="$t('attribute.name')"
            />

            <v-text-field
              v-model="edited_attribute.description"
              :label="$t('attribute.description')"
            />

            <v-row>
              <v-col>
                <v-text-field
                  v-model="edited_attribute.min_occurrence"
                  type="number"
                  :label="$t('attribute.min_occurrence')"
                ></v-text-field>
              </v-col>
              <v-col>
                <v-text-field
                  v-model="edited_attribute.max_occurrence"
                  type="number"
                  :label="$t('attribute.max_occurrence')"
                ></v-text-field>
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <v-text-field
                  v-model="edited_attribute.index"
                  type="number"
                  label="Index"
                ></v-text-field>
              </v-col>
            </v-row>
          </v-card-text>

          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn color="primary" dark @click="save">
              {{ $t('attribute.save') }}
            </v-btn>
            <v-btn color="primary" text @click="close">
              {{ $t('attribute.cancel') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-toolbar>

    <v-data-table :headers="headers" :items="attribute_contents">
      <template #item.actions="{ item }">
        <div class="d-inline-flex">
          <v-tooltip left>
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                icon="mdi-pencil"
                @click.stop="editItem(item)"
              />
            </template>
            <span>Edit</span>
          </v-tooltip>
          <v-tooltip left>
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                color="red"
                icon="mdi-delete"
                @click.stop="deleteItem(item)"
              />
            </template>
            <span>Delete</span>
          </v-tooltip>
        </div>
      </template>
      <template #item.attribute_id="{ item }">
        <v-icon :icon="item.attribute.tag" />
        {{ item.attribute.name }}
      </template>

      <template v-if="attribute_contents.length < 10" #bottom />
    </v-data-table>
  </v-container>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'AttributeTable',
  props: {
    attributes: {
      type: Array,
      default: () => []
    },
    attributeTemplates: {
      type: Array,
      default: () => []
    }
  },
  emits: ['update'],
  setup(props, { emit }) {
    const dialog = ref(false)
    const attribute_type = ref(null)
    const edited_index = ref(-1)
    const attribute_contents = ref(props.attributes)
    const edited_attribute = ref({
      index: attribute_contents.value.length,
      attribute_id: -1,
      title: '',
      description: '',
      min_occurrence: 0,
      max_occurrence: 1,
      attribute: []
    })
    const default_attribute = ref({
      index: attribute_contents.value.length,
      attribute_id: -1,
      title: '',
      description: '',
      min_occurrence: 0,
      max_occurrence: 1,
      attribute: []
    })

    const headers = computed(() => [
      {
        title: 'Type',
        key: 'attribute_id',
        align: 'left',
        sortable: false
      },
      { title: 'Name', key: 'title', sortable: false },
      { title: 'Description', key: 'description', sortable: false },
      { title: 'Min Occurence', key: 'min_occurrence', sortable: false },
      { title: 'Max Occurence', key: 'max_occurrence', sortable: false },
      { title: 'Actions', key: 'actions', align: 'right', sortable: false }
    ])

    const formTitle = computed(() =>
      edited_index.value === -1 ? 'Add Attribute' : 'Edit Attribute'
    )

    const close = () => {
      dialog.value = false
      edited_attribute.value = Object.assign({}, default_attribute.value)
      edited_attribute.value.index = attribute_contents.value.length
      edited_index.value = -1
    }

    const save = () => {
      edited_attribute.value.attribute_id = attribute_type.value.id
      edited_attribute.value.attribute = attribute_type.value
      if (edited_index.value > -1) {
        Object.assign(
          attribute_contents.value[edited_index.value],
          edited_attribute.value
        )
      } else {
        attribute_contents.value.push(edited_attribute.value)
      }
      attribute_type.value = null
      emit('update', attribute_contents.value)
      close()
    }

    const deleteItem = (item) => {
      const index = attribute_contents.value.indexOf(item)
      attribute_contents.value.splice(index, 1)
    }

    const editItem = (item) => {
      edited_index.value = attribute_contents.value.indexOf(item)
      edited_attribute.value = Object.assign({}, item)
      dialog.value = true
      attribute_type.value = props.attributeTemplates.find(
        (attribute_template) =>
          attribute_template.id === edited_attribute.value.attribute_id
      )
    }

    return {
      dialog,
      attribute_type,
      edited_index,
      edited_attribute,
      default_attribute,
      attribute_contents,
      headers,
      formTitle,
      close,
      save,
      deleteItem,
      editItem
    }
  }
}
</script>
