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
              :items="attribute_templates"
              item-title="name"
              :label="$t('attribute.attribute')"
            />

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
            <v-btn color="primary" dark @click="save">{{
              $t('attribute.save')
            }}</v-btn>
            <v-btn color="primary" text @click="close">{{
              $t('attribute.cancel')
            }}</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-toolbar>

    <v-data-table :headers="headers" :items="attribute_contents">
      <template #item.actions="{ item }">
        <div class="d-inline-flex">
          <v-tooltip left>
            <template #activator="{ props }">
              <v-icon v-bind="props" @click.stop="editItem(item.raw)">
                mdi-pencil
              </v-icon>
            </template>
            <span>Edit</span>
          </v-tooltip>
          <v-tooltip left>
            <template #activator="{ props }">
              <v-icon
                v-bind="props"
                color="red"
                @click.stop="deleteItem(item.raw)"
              >
                mdi-delete
              </v-icon>
            </template>
            <span>Delete</span>
          </v-tooltip>
        </div>
      </template>
      <template v-if="attribute_contents.length < 10" #bottom />
    </v-data-table>
  </v-container>
</template>

<script>
import { mapActions, mapState } from 'pinia'
import { useConfigStore } from '@/stores/ConfigStore'

export default {
  name: 'AttributeTable',
  props: {
    attributes: {
      type: Object,
      default: () => ({})
    },
    disabled: Boolean
  },
  emits: ['update'],
  data: () => ({
    dialog: false,
    attribute_type: null,
    edited_index: -1,
    attribute_templates: [],
    edited_attribute: {
      index: 0,
      id: -1,
      attribute_id: -1,
      attribute_name: '',
      title: '',
      description: '',
      min_occurrence: 0,
      max_occurrence: 1
    },
    default_attribute: {
      index: 0,
      id: -1,
      attribute_id: -1,
      attribute_name: '',
      title: '',
      description: '',
      min_occurrence: 0,
      max_occurrence: 1
    }
  }),
  computed: {
    ...mapState(useConfigStore, { store_attributes: 'attributes' }),
    attribute_contents() {
      return this.attributes
    },
    headers() {
      return [
        {
          title: 'Type',
          key: 'attribute_name',
          align: 'left',
          sortable: false
        },
        { title: 'Name', key: 'title', sortable: false },
        { title: 'Description', key: 'description', sortable: false },
        { title: 'Min Occurence', key: 'min_occurrence', sortable: false },
        { title: 'Max Occurence', key: 'max_occurrence', sortable: false },
        { title: 'Actions', key: 'actions', align: 'right', sortable: false }
      ]
    },

    formTitle() {
      return this.edited_index === -1 ? 'Add Attribute' : 'Edit Attribute'
    }
  },
  mounted() {
    this.loadAttributes().then(() => {
      this.attribute_templates = this.store_attributes.items
    })
    this.edited_attribute.index = this.attribute_contents.length
  },
  methods: {
    ...mapActions(useConfigStore, ['loadAttributes']),
    close() {
      this.dialog = false
      this.$nextTick(() => {
        this.edited_attribute = Object.assign({}, this.default_attribute)
        this.edited_attribute.index = this.attribute_contents.length
        this.edited_index = -1
      })
    },

    save() {
      this.edited_attribute.attribute_id = this.attribute_type.id
      this.edited_attribute.attribute_name = this.attribute_type.name
      if (this.edited_index > -1) {
        Object.assign(
          this.attribute_contents[this.edited_index],
          this.edited_attribute
        )
      } else {
        this.attribute_contents.push(this.edited_attribute)
      }
      this.attribute_type = null
      this.$emit('update', this.attribute_contents)
      this.close()
    },

    deleteItem(item) {
      const index = this.attribute_contents.indexOf(item)
      this.attribute_contents.splice(index, 1)
    },

    editItem(item) {
      this.edited_index = this.attribute_contents.indexOf(item)
      this.edited_attribute = Object.assign({}, item)
      this.dialog = true
      this.attribute_type = this.attribute_templates.find(
        (attribute_template) =>
          attribute_template.id === this.edited_attribute.attribute_id
      )
    }
  }
}
</script>
