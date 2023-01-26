<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <v-form @submit.prevent="add" id="form" ref="form">
      <v-row no-gutters>
        <v-col cols="6" class="pa-1">
          <v-text-field
            :disabled="!canUpdate"
            :label="$t('user.username')"
            name="username"
            type="text"
            v-model="user.username"
            v-validate="'required'"
            data-vv-name="username"
            :error-messages="errors.collect('username')"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
            :disabled="!canUpdate"
            :label="$t('user.name')"
            name="name"
            v-model="user.name"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
            ref="password"
            type="password"
            v-model="pwd"
            v-validate="checkPassEdit ? 'required' : ''"
            :error-messages="errors.collect('password_check')"
            :label="$t('user.password')"
            data-vv-name="password_check"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
            v-model="repwd"
            type="password"
            v-validate="checkPassEdit ? 'required|confirmed:password' : ''"
            :error-messages="errors.collect('password_check')"
            :label="$t('user.password_check')"
            data-vv-name="password_check"
          />
        </v-col>
      </v-row>

      <v-row no-gutters>
        <v-col cols="6" class="pr-1">
          <v-data-table
            :disabled="!canUpdate"
            v-model="user.organizations"
            :headers="headers"
            :items="organizations"
            item-key="id"
            :show-select="canUpdate"
            :hide-default-footer="organizations.length < 10"
            class="elevation-1"
          >
            <template v-slot:top>
              <v-toolbar flat color="white">
                <v-toolbar-title>{{
                  $t('user.organizations')
                }}</v-toolbar-title>
              </v-toolbar>
            </template>
          </v-data-table>
        </v-col>
        <v-col cols="6" class="pl-1">
          <v-data-table
            :disabled="!canUpdate"
            v-model="user.roles"
            :headers="headers"
            :items="roles"
            item-key="id"
            :show-select="canUpdate"
            :hide-default-footer="roles.length < 10"
            class="elevation-1"
          >
            <template v-slot:top>
              <v-toolbar flat color="white">
                <v-toolbar-title>{{ $t('user.roles') }}</v-toolbar-title>
              </v-toolbar>
            </template>
          </v-data-table>
        </v-col>
        <v-col cols="12" class="pt-2">
          <v-data-table
            :disabled="!canUpdate"
            v-model="user.permissions"
            :headers="headers"
            :items="permissions"
            item-key="id"
            :show-select="canUpdate"
            :hide-default-footer="permissions.length < 10"
            class="elevation-1"
          >
            <template v-slot:top>
              <v-toolbar flat color="white">
                <v-toolbar-title>{{ $t('user.permissions') }}</v-toolbar-title>
              </v-toolbar>
            </template>
          </v-data-table>
        </v-col>
      </v-row>

      <v-row no-gutters class="pt-2">
        <v-col>
          <v-alert v-if="show_validation_error" dense type="error" text>
            {{ $t('user.validation_error') }}
          </v-alert>
          <v-alert v-if="show_error" dense type="error" text>
            {{ $t('user.error') }}
          </v-alert>
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-btn type="submit" color="success" class="mr-4"> Submit </v-btn>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
import AuthMixin from '../../../services/auth/auth_mixin'
import { createUser, updateUser } from '@/api/config'
import Permissions from '@/services/auth/permissions'
import { mapGetters, mapActions } from 'vuex'

export default {
  name: 'UserForm',
  components: {},
  props: {
    user_id: {
      type: Number,
      required: false
    }
  },
  data: () => ({
    headers: [
      {
        text: 'Name',
        align: 'start',
        value: 'name'
      },
      { text: 'Description', value: 'description' }
    ],

    visible: false,
    show_validation_error: false,
    edit: false,
    show_error: false,
    selected_roles: [],
    selected_permissions: [],
    selected_organizations: [],
    roles: [],
    permissions: [],
    organizations: [],
    pwd: '',
    repwd: '',
    pwdvld: true,
    user: {
      id: -1,
      username: '',
      name: '',
      roles: [],
      permissions: [],
      organizations: []
    }
  }),
  computed: {
    checkPassEdit() {
      if (this.edit) {
        return this.pwd !== '' || this.repwd !== ''
      } else {
        return true
      }
    },
    canCreate() {
      return this.checkPermission(Permissions.CONFIG_USER_CREATE)
    },
    canUpdate() {
      return this.checkPermission(Permissions.CONFIG_USER_UPDATE)
    }
  },
  watch: {
    user_id: function () {
      this.loadUser()
    }
  },
  methods: {
    ...mapActions('config', [
      'loadOrganizations',
      'loadRoles',
      'loadPermissions',
      'loadUsers'
    ]),
    ...mapGetters('config', [
      'getUsers',
      'getOrganizations',
      'getRoles',
      'getPermissions',
      'getUserByID'
    ]),
    add() {
      this.$validator.validateAll().then(() => {
        if (this.$validator.errors.any()) {
          this.show_validation_error = true
          return
        }
        this.show_validation_error = false
        this.show_error = false

        if (this.edit === false || this.pwd !== '') {
          this.user.password = this.pwd
        }

        if (this.edit) {
          updateUser(this.user)
            .then(() => {
              this.$validator.reset()

              this.$root.$emit('notification', {
                type: 'success',
                loc: 'user.successful_edit'
              })
            })
            .catch(() => {
              this.show_error = true
            })
        } else {
          createUser(this.user)
            .then(() => {
              this.$validator.reset()

              this.$root.$emit('notification', {
                type: 'success',
                loc: 'user.successful'
              })
            })
            .catch(() => {
              this.show_error = true
            })
        }
      })
    },
    loadUser() {
      if (this.user_id !== undefined && this.user_id !== null) {
        this.loadUsers().then(() => {
          const stored_user = this.getUserByID()(this.user_id)
          if (stored_user !== null) {
            this.user = stored_user
            this.edit = true
          }
        })
      } else {
        this.user = {
          id: -1,
          username: '',
          name: '',
          roles: [],
          permissions: [],
          organizations: []
        }
      }
    }
  },
  mixins: [AuthMixin],
  mounted() {
    this.loadOrganizations().then(() => {
      this.organizations = this.getOrganizations().items
    })

    this.loadRoles().then(() => {
      this.roles = this.getRoles().items
    })

    this.loadPermissions().then(() => {
      this.permissions = this.getPermissions().items
    })

    this.loadUser()
  },
  beforeDestroy() {}
}
</script>