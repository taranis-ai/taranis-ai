<template>
  <v-row v-bind="UI.DIALOG.ROW.WINDOW">
    <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="canCreate" @click="addNode">
      <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
      <span>{{$t('nodes.add_btn')}}</span>
    </v-btn>
    <v-dialog v-model="visible" max-width="600" persistent>
      <v-card v-bind="UI.DIALOG.BASEMENT">
        <v-toolbar v-bind="UI.DIALOG.TOOLBAR">
          <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
            <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
          </v-btn>
          <v-toolbar-title v-if="!edit">{{$t('nodes.add_new')}}</v-toolbar-title>
          <v-toolbar-title v-if="edit">{{$t('nodes.edit')}}</v-toolbar-title>
          <v-spacer></v-spacer>
          <v-btn v-if="canUpdate" text type="submit" form="form">
            <v-icon left>mdi-content-save</v-icon>
            <span>{{$t('nodes.save')}}</span>
          </v-btn>
        </v-toolbar>

        <v-card-text>
          <v-form @submit.prevent="add" id="form" ref="form">
            <v-select
              v-model="node.type"
              :items="node_type"
              label="Node Type"
              solo
            ></v-select>
            <v-text-field :disabled="!canUpdate"
                    :label="$t('nodes.name')"
                    name="name"
                    type="text"
                    v-model="node.name"
                    v-validate="'required'"
                    data-vv-name="name"
                    :error-messages="errors.collect('name')"
                    :spellcheck="$store.state.settings.spellcheck"
            ></v-text-field>
            <v-textarea :disabled="!canUpdate"
                  :label="$t('nodes.description')"
                  name="description"
                  v-model="node.description"
                  :spellcheck="$store.state.settings.spellcheck"
            ></v-textarea>
            <v-text-field :disabled="!canUpdate"
                    :label="$t('nodes.url')"
                    name="url"
                    type="text"
                    v-model="node.api_url"
                    v-validate="'required'"
                    data-vv-name="url"
                    :error-messages="errors.collect('url')"
            ></v-text-field>
            <v-text-field :disabled="!canUpdate"
                    :label="$t('nodes.key')"
                    name="key"
                    type="text"
                    v-model="node.api_key"
                    v-validate="'required'"
                    data-vv-name="key"
                    :error-messages="errors.collect('key')"
            ></v-text-field>

            <v-alert v-if="show_validation_error" dense type="error" text>
              {{$t('nodes.validation_error')}}
            </v-alert>
            <v-alert v-if="show_error" dense type="error" text>{{$t('nodes.error')}}
            </v-alert>
          </v-form>
        </v-card-text>
      </v-card>
    </v-dialog>
  </v-row>
</template>

<script>
import { createNode, updateNode } from '@/api/config'

import AuthMixin from '@/services/auth/auth_mixin'
import Permissions from '@/services/auth/permissions'

export default {
  name: 'EditNode',
  data: () => ({
    visible: false,
    edit: false,
    node_type: ['Collector', 'Bot', 'Publisher', 'Presenter'],
    show_validation_error: false,
    show_error: false,
    node: {
      name: '',
      description: '',
      api_url: '',
      api_key: '',
      type: ''
    }
  }),
  mixins: [AuthMixin],
  computed: {
    canCreate () {
      return this.checkPermission(Permissions.CONFIG_COLLECTORS_NODE_CREATE)
    },
    canUpdate () {
      return this.checkPermission(Permissions.CONFIG_COLLECTORS_NODE_UPDATE) || !this.edit
    }
  },
  methods: {
    addNode () {
      this.visible = true
      this.edit = false
      this.show_error = false
      this.node.name = ''
      this.node.description = ''
      this.node.api_url = ''
      this.node.api_key = ''
      this.$validator.reset()
    },

    cancel () {
      this.$validator.reset()
      this.visible = false
    },

    add () {
      this.$validator.validateAll().then(() => {
        if (!this.$validator.errors.any()) {
          this.show_validation_error = false
          this.show_error = false

          if (this.edit) {
            updateNode(this.node).then(() => {
              this.$validator.reset()
              this.visible = false
              this.$root.$emit('notification',
                {
                  type: 'success',
                  loc: 'nodes.successful_edit'
                }
              )
            }).catch(() => {
              this.show_error = true
            })
          } else {
            createNode(this.node).then(() => {
              this.$validator.reset()
              this.visible = false
              this.$root.$emit('notification',
                {
                  type: 'success',
                  loc: 'nodes.successful'
                }
              )
            }).catch(() => {
              this.show_error = true
            })
          }
        } else {
          this.show_validation_error = true
        }
      })
    }
  },
  mounted () {
    this.$root.$on('show-edit', (data) => {
      this.visible = true
      this.edit = true
      this.show_error = false
      this.node.id = data.id
      this.node.name = data.name
      this.node.description = data.description
      this.node.api_url = data.api_url
      this.node.api_key = data.api_key
      this.node.type = data.type
    })
  },
  beforeDestroy () {
    this.$root.$off('show-edit')
  }
}
</script>
