<template>
  <v-container>      <v-toolbar flat color="white">
        <v-toolbar-title>{{ $t('attribute.attributes') }}</v-toolbar-title>
        <v-divider class="mx-4" inset vertical></v-divider>
        <v-spacer></v-spacer>
        <v-dialog v-if="!disabled" v-model="dialog" max-width="500px">
          <template v-slot:activator="{ on }">
            <v-btn color="primary" dark class="mb-2" v-on="on">
              <v-icon left>mdi-plus</v-icon>
              <span>{{ $t('attribute.new_attribute') }}</span>
            </v-btn>
          </template>
          <v-card>
            <v-card-title>
              <span class="headline">{{ formTitle }}</span>
            </v-card-title>

            <v-card-text>
              <v-combobox
                v-model="attribute_type"
                :items="attribute_templates"
                item-text="name"
                :label="$t('attribute.attribute')"
              ></v-combobox>

              <v-text-field
                v-model="edited_attribute.title"
                :label="$t('attribute.name')"
                :spellcheck="$store.state.settings.spellcheck"
              ></v-text-field>

              <v-text-field
                v-model="edited_attribute.description"
                :label="$t('attribute.description')"
                :spellcheck="$store.state.settings.spellcheck"
              ></v-text-field>

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

    <v-data-table
    :headers="headers"
    :items="attribute_contents"
    :hide-default-footer="attribute_contents.length < 10"
    :sort-by="index"
  >
    <template v-slot:[`item.actions`]="{ item }">
      <v-icon v-if="!disabled" small class="mr-2" @click="editItem(item)">
        edit
      </v-icon>
      <v-icon v-if="!disabled" small @click="deleteItem(item)"> delete </v-icon>
    </template>
  </v-data-table>
  </v-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex'

export default {
  name: 'AttributeTable',
  props: {
    attributes: {
      type: Array,
      default: () => []
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
    attribute_contents() {
      return this.attributes || []
    },
    headers() {
      return [
        { text: 'Type', value: 'attribute_name', align: 'left', sortable: false },
        { text: 'Name', value: 'title', sortable: false },
        { text: 'Description', value: 'description', sortable: false },
        { text: 'Min Occurence', value: 'min_occurrence', sortable: false },
        { text: 'Max Occurence', value: 'max_occurrence', sortable: false },
        { text: 'Actions', value: 'actions', align: 'right', sortable: false }
      ]
    },

    formTitle() {
      return this.edited_index === -1 ? 'Add Attribute' : 'Edit Attribute'
    }
  },
  watch: {
    dialog(val) {
      val || this.close()
    }
  },
  methods: {
    ...mapGetters('config', ['getAttributes']),
    ...mapActions('config', ['loadAttributes']),
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
  },
  mounted() {
    this.loadAttributes().then(() => {
      this.attribute_templates = this.getAttributes().items
    })
    this.edited_attribute.index = this.attribute_contents.length
  }
}
</script>
