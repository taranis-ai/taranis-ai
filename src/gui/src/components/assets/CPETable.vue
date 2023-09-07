<template>
  <v-data-table
    :headers="headers"
    :items="cpes"
    sort-by="value"
    class="elevation-1"
  >
    <template #top>
      <v-toolbar flat color="white">
        <v-toolbar-title>{{ $t('asset.cpes') }}</v-toolbar-title>
        <v-divider class="mx-4" inset vertical></v-divider>
        <v-spacer></v-spacer>
        <v-dialog v-model="dialog" max-width="700px">
          <template v-if="editAllowed()" #activator="{ on }">
            <v-btn color="primary" dark class="mb-2" v-on="on">
              <v-icon left>mdi-plus</v-icon>
              <span>{{ $t('asset.new_cpe') }}</span>
            </v-btn>
          </template>
          <v-card>
            <v-card-title>
              <span class="headline">{{ formTitle }}</span>
            </v-card-title>

            <v-card-text>
              <v-row>
                <v-col class="mt-6" style="flex-grow: 0">
                  <EnumSelector
                    :attribute-id="cpe_attribute_id"
                    cpe-only
                    @enum-selected="enumSelected"
                  />
                </v-col>

                <v-col cols="10">
                  <v-text-field
                    v-model="edited_cpe.value"
                    :label="$t('asset.value')"
                    :spellcheck="spellcheck"
                  ></v-text-field>
                </v-col>
              </v-row>
            </v-card-text>

            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn color="primary" dark @click="save">{{
                $t('asset.save')
              }}</v-btn>
              <v-btn color="primary" text @click="close">{{
                $t('asset.cancel')
              }}</v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>

        <v-dialog v-model="dialog_csv" max-width="500px">
          <template v-if="editAllowed()" #activator="{ on }">
            <v-btn color="primary" dark class="mb-2 ml-1" v-on="on">
              <v-icon left>mdi-upload</v-icon>
              <span>{{ $t('asset.import_csv') }}</span>
            </v-btn>
          </template>
          <v-card>
            <v-card-title>
              <span class="headline">{{ $t('asset.import_from_csv') }}</span>
            </v-card-title>

            <v-row class="ma-6">
              <VueCsvImport
                v-model="csv"
                :map-fields="['value', 'description']"
              >
                <template #next="{ load }">
                  <button class="load" @click.prevent="load">
                    {{ $t('asset.load_csv_file') }}
                  </button>
                </template>
              </VueCsvImport>
            </v-row>

            <v-card-actions>
              <v-spacer></v-spacer>
              <v-checkbox
                v-model="csv_delete_exist_list"
                label="Delete existing CPE codes"
              ></v-checkbox>
              <v-spacer></v-spacer>
              <v-btn color="primary" dark @click="importCSV">
                {{ $t('asset.import') }}
              </v-btn>
              <v-btn color="primary" text @click="closeCSV">
                {{ $t('asset.cancel') }}
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
      </v-toolbar>
    </template>
    <template v-if="editAllowed()" #item.action="{ item }">
      <v-icon small class="mr-2" @click="editItem(item)"> edit </v-icon>
      <v-icon small @click="deleteItem(item)"> delete </v-icon>
    </template>
  </v-data-table>
</template>

<script>
import Permissions from '@/services/auth/permissions'
import EnumSelector from '@/components/common/EnumSelector.vue'
import { findAttributeCPE } from '@/api/assets'

import VueCsvImport from '@/components/common/ImportCSV.vue'

import { mapState } from 'pinia'
import { useSettingsStore } from '@/stores/SettingsStore'

export default {
  name: 'CPETable',
  components: {
    VueCsvImport,
    EnumSelector
  },
  props: {
    assetCpes: {
      type: Array,
      required: true
    }
  },
  emits: ['update:assetCpes'],
  data: () => ({
    csv: null,
    cpes: this.assetCpes,
    csv_delete_exist_list: false,
    csv_preview: false,
    csv_data: null,
    headers: [
      { text: 'Value', value: 'value', align: 'left', sortable: true },
      { text: 'Actions', value: 'action', align: 'right', sortable: false }
    ],
    dialog: false,
    dialog_csv: false,
    cpe_attribute_id: null,
    selected_cpe: null,
    edited_index: -1,
    edited_cpe: {
      value: ''
    },
    default_cpe: {
      value: ''
    }
  }),
  computed: {
    formTitle() {
      return this.edited_index === -1 ? 'Add CPE Code' : 'Edit CPE Code'
    },
    ...mapState(useSettingsStore, ['spellcheck'])
  },
  watch: {
    dialog(val) {
      val || this.close()
    }
  },
  mounted() {
    findAttributeCPE().then((response) => {
      this.cpe_attribute_id = response.data
    })
  },
  methods: {
    enumSelected(data) {
      this.edited_cpe.value = data.value
    },

    editAllowed() {
      return this.checkPermission(Permissions.MY_ASSETS_CREATE)
    },
    close() {
      this.dialog = false
      setTimeout(() => {
        this.edited_cpe = Object.assign({}, this.default_cpe)
        this.edited_index = -1
      }, 300)
    },

    save() {
      if (this.edited_index > -1) {
        Object.assign(this.cpes[this.edited_index], this.edited_cpe)
      } else {
        this.cpes.push(this.edited_cpe)
      }
      this.selected_cpe = null
      this.close()
    },

    importCSV() {
      if (this.csv_delete_exist_list) {
        this.$emit('update:assetCpes', this.csv)
      } else {
        const arrayWithDuplicates = this.cpes.concat(this.csv)

        const removeDuplicates = function (originalArray, prop) {
          let i
          const newArray = []
          const lookupObject = {}

          for (i in originalArray) {
            lookupObject[originalArray[i][prop]] = originalArray[i]
          }

          for (i in lookupObject) {
            newArray.push(lookupObject[i])
          }

          return newArray
        }

        const uniqueArray = removeDuplicates(arrayWithDuplicates, 'value')
        this.$emit('update:assetCpes', uniqueArray)
      }

      this.dialog_csv = false
      this.csv = null
      this.csv_delete_exist_list = false
      this.$root.$emit('reset-csv-dialog')
    },

    closeCSV() {
      this.dialog_csv = false
      this.csv = null
      this.csv_delete_exist_list = false
      this.$root.$emit('reset-csv-dialog')
    },

    editItem(item) {
      this.edited_index = this.cpes.indexOf(item)
      this.edited_cpe = Object.assign({}, item)
      this.dialog = true
    },

    deleteItem(item) {
      const index = this.cpes.indexOf(item)
      this.cpes.splice(index, 1)
    }
  }
}
</script>
