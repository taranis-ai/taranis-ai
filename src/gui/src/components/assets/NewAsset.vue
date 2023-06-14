<template>
  <v-row v-bind="UI.DIALOG.ROW.WINDOW">
    <v-btn v-if="editAllowed()" v-bind="UI.BUTTON.ADD_NEW" @click="addAsset">
      <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
      <span>{{ $t('asset.add_new') }}</span>
    </v-btn>
    <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
      <v-card v-bind="UI.DIALOG.BASEMENT">
        <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
          <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
            <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
          </v-btn>

          <v-toolbar-title>
            <span v-if="!edit">{{ $t('asset.add_new') }}</span>
            <span v-else>{{ $t('asset.edit') }}</span>
          </v-toolbar-title>

          <v-spacer></v-spacer>
          <v-btn v-if="editAllowed()" text dark type="submit" form="form">
            <v-icon left>mdi-content-save</v-icon>
            <span>{{ $t('asset.save') }}</span>
          </v-btn>
        </v-toolbar>

        <v-form id="form" ref="form" class="px-4" @submit.prevent="add">
          <v-row no-gutters>
            <v-col cols="6" class="pr-3">
              <v-text-field
                v-model="asset.name"
                v-validate="'required'"
                :disabled="!editAllowed()"
                :label="$t('asset.name')"
                name="name"
                type="text"
                data-vv-name="name"
                :error-messages="errors.collect('name')"
                :spellcheck="spellcheck"
              />
            </v-col>
            <v-col cols="6" class="pr-3">
              <v-text-field
                v-model="asset.serial"
                :disabled="!editAllowed()"
                :label="$t('asset.serial')"
                name="serial"
                type="text"
                :spellcheck="spellcheck"
              />
            </v-col>
            <v-col cols="12" class="pr-3">
              <v-textarea
                v-model="asset.description"
                :disabled="!editAllowed()"
                :label="$t('asset.description')"
                name="description"
                :spellcheck="spellcheck"
              />
            </v-col>
          </v-row>
          <v-row no-gutters>
            <v-col cols="12">
              <CPETable
                :asset-cpes="asset.asset_cpes"
                @update:asset-cpes="update"
              />
            </v-col>
          </v-row>
          <v-row
            v-if="edit"
            no-gutters
            class="mt-4 px-3 grey lighten-4 rounded"
          >
            <v-col cols="12">
              <span
                class="body-1 font-weight-bold text-uppercase primary--text"
                >{{ $t('asset.vulnerabilities') }}</span
              >
            </v-col>
            <v-col cols="12">
              <component
                :is="cardLayout()"
                v-for="vulnerability in vulnerabilities"
                :key="vulnerability.id"
                class="item-selector"
                :card="vulnerability"
                :asset="asset"
                :show-toolbar="true"
              >
              </component>
            </v-col>
          </v-row>

          <v-row no-gutters class="pt-2">
            <v-col cols="12">
              <v-alert v-if="show_validation_error" dense type="error" text>
                {{ $t('asset.validation_error') }}
              </v-alert>
              <v-alert v-if="show_error" dense type="error" text>
                {{ $t('asset.error') }}
              </v-alert>
            </v-col>
          </v-row>
        </v-form>
      </v-card>
    </v-dialog>
  </v-row>
</template>

<script>
import { createAsset, updateAsset } from '@/api/assets'

import CPETable from '@/components/assets/CPETable.vue'
import CardVulnerability from '@/components/assets/CardVulnerability.vue'

import { mapState } from 'pinia'
import { useSettingsStore } from '@/stores/SettingsStore'

export default {
  name: 'NewAsset',
  components: {
    CPETable,
    CardVulnerability
  },
  data: () => ({
    visible: false,
    edit: false,
    show_validation_error: false,
    show_error: false,
    vulnerabilities: [],
    asset: {
      id: -1,
      name: '',
      serial: '',
      description: '',
      asset_cpes: [],
      asset_group_id: ''
    }
  }),
  computed: {
    ...mapState(useSettingsStore, ['spellcheck'])
  },
  methods: {
    editAllowed() {
      return true
    },
    cardLayout() {
      return 'CardVulnerability'
    },
    addAsset() {
      this.visible = true
      this.edit = false
      this.show_error = false
      this.asset.id = -1
      this.asset.name = ''
      this.asset.serial = ''
      this.asset.description = ''
      this.asset.asset_cpes = []
      this.asset.asset_group_id = ''
      this.$validator.reset()
    },

    cancel() {
      this.$validator.reset()
      this.visible = false
    },

    add() {
      this.$validator.validateAll().then(() => {
        if (!this.$validator.errors.any()) {
          this.show_validation_error = false
          this.show_error = false

          if (window.location.pathname.includes('/group/')) {
            const i = window.location.pathname.indexOf('/group/')
            const len = window.location.pathname.length
            this.asset.asset_group_id = window.location.pathname.substring(
              i + 7,
              len
            )
          }

          for (let i = 0; i < this.asset.asset_cpes.length; i++) {
            this.asset.asset_cpes[i].value = this.asset.asset_cpes[
              i
            ].value.replace('*', '%')
          }

          if (this.edit === true) {
            updateAsset(this.asset)
              .then(() => {
                this.$validator.reset()
                this.visible = false
              })
              .catch(() => {
                this.show_error = true
              })
          } else {
            createAsset(this.asset)
              .then(() => {
                this.$validator.reset()
                this.visible = false
              })
              .catch(() => {
                this.show_error = true
              })
          }
        } else {
          this.show_validation_error = true
        }
      })
    },

    update(cpes) {
      this.asset.asset_cpes = cpes
    }
  }
}
</script>
