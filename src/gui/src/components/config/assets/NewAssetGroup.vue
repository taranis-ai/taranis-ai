<template>
  <v-row v-bind="UI.DIALOG.ROW.WINDOW">
    <v-btn v-bind="UI.BUTTON.ADD_NEW" @click="addGroup">
      <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
      <span>{{ $t('asset_group.add') }}</span>
    </v-btn>
    <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible">
      <v-card v-bind="UI.DIALOG.BASEMENT">
        <v-toolbar v-bind="UI.DIALOG.TOOLBAR">
          <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
            <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
          </v-btn>

          <v-toolbar-title>
            <span v-if="!edit">{{ $t('asset_group.add_new') }}</span>
            <span v-else>{{ $t('asset_group.edit') }}</span>
          </v-toolbar-title>

          <v-spacer></v-spacer>
          <v-btn text type="submit" form="form">
            <v-icon left>mdi-content-save</v-icon>
            <span>{{ $t('asset_group.save') }}</span>
          </v-btn>
        </v-toolbar>

        <v-form id="form" ref="form" class="px-4" @submit.prevent="add">
          <v-row no-gutters>
            <v-col cols="12" class="pa-1">
              <v-text-field
                v-model="group.name"
                v-validate="'required'"
                :label="$t('asset_group.name')"
                name="name"
                type="text"
                data-vv-name="name"
                :error-messages="errors.collect('name')"
                :spellcheck="spellcheck"
              />
            </v-col>
            <v-col cols="12" class="pa-1">
              <v-textarea
                v-model="group.description"
                :label="$t('asset_group.description')"
                name="description"
                :spellcheck="spellcheck"
              />
            </v-col>
          </v-row>
          <v-row no-gutters>
            <v-col cols="12">
              <v-data-table
                v-model="selected_users"
                :headers="headers"
                :items="users"
                item-key="id"
                show-select
                class="elevation-1"
              >
                <template #top>
                  <v-toolbar flat color="white">
                    <v-toolbar-title>{{
                      $t('asset_group.allowed_users')
                    }}</v-toolbar-title>
                  </v-toolbar>
                </template>
              </v-data-table>
            </v-col>
            <v-col cols="12" class="pt-3">
              <v-data-table
                v-model="selected_templates"
                :headers="headers_template"
                :items="templates"
                item-key="id"
                show-select
                class="elevation-1"
              >
                <template #top>
                  <v-toolbar flat color="white">
                    <v-toolbar-title>{{
                      $t('asset_group.notification_templates')
                    }}</v-toolbar-title>
                  </v-toolbar>
                </template>
              </v-data-table>
            </v-col>
          </v-row>
          <v-row no-gutters class="pt-2">
            <v-col cols="12">
              <v-alert v-if="show_validation_error" dense type="error" text>
                {{ $t('asset_group.validation_error') }}
              </v-alert>
              <v-alert v-if="show_error" dense type="error" text>
                {{ $t('asset_group.error') }}
              </v-alert>
            </v-col>
          </v-row>
        </v-form>
      </v-card>
    </v-dialog>
  </v-row>
</template>

<script>
import { createAssetGroup, updateAssetGroup } from '@/api/assets'

import { mapActions, mapState } from 'pinia'
import { useSettingsStore } from '@/stores/SettingsStore'
import { useConfigStore } from '@/stores/ConfigStore'
import { useAssetsStore } from '@/stores/AssetsStore'

export default {
  name: 'NewAssetGroup',
  data: () => ({
    visible: false,
    edit: false,
    headers: [
      {
        title: 'Username',
        align: 'start',
        key: 'username'
      },
      { title: 'Name', key: 'name' }
    ],
    headers_template: [
      {
        title: 'Name',
        align: 'start',
        key: 'name'
      },
      { title: 'Description', key: 'description' }
    ],
    selected_users: [],
    templates: [],
    selected_templates: [],
    show_validation_error: false,
    show_error: false,
    group: {
      id: '',
      name: '',
      description: '',
      users: [],
      templates: []
    }
  }),
  computed: {
    ...mapState(useSettingsStore, ['spellcheck']),
    ...mapState(useAssetsStore, ['notification_templates']),
    ...mapState(useConfigStore, ['users'])
  },
  async mounted() {
    await this.getAllExternalUsers({ search: '' })

    this.getAllNotificationTemplates({ search: '' }).then(() => {
      this.templates = this.notification_templates.items
    })

    this.$root.$on('show-edit', (data) => {
      this.visible = true
      this.edit = true
      this.show_error = false
      this.group.id = data.id
      this.group.name = data.name
      this.group.description = data.description
      this.selected_users = data.users
      this.selected_templates = data.templates
    })
  },
  methods: {
    ...mapActions(useConfigStore, [
      'getAllNotificationTemplates',
      'getAllExternalUsers'
    ]),
    addGroup() {
      this.visible = true
      this.edit = false
      this.show_error = false
      this.group.name = ''
      this.group.description = ''
      this.group.users = []
      this.group.templates = []
      this.selected_users = []
      this.selected_templates = []
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

          this.group.users = []
          for (let i = 0; i < this.selected_users.length; i++) {
            this.group.users.push({
              id: this.selected_users[i].id
            })
          }

          this.group.templates = []
          for (let i = 0; i < this.selected_templates.length; i++) {
            this.group.templates.push({
              id: this.selected_templates[i].id
            })
          }

          if (this.edit) {
            updateAssetGroup(this.group)
              .then(() => {
                this.$validator.reset()
                this.visible = false
              })
              .catch(() => {
                this.show_error = true
              })
          } else {
            createAssetGroup(this.group)
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
    }
  }
}
</script>
