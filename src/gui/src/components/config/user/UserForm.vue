<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <v-form @submit.prevent="add" id="form" ref="form">
      <v-row no-gutters>
        <v-btn type="submit" color="success" class="mr-4"> Submit </v-btn>
      </v-row>
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
          <v-select
            :disabled="!canUpdate"
            v-model="user.organization.id"
            item-text="name"
            item-value="id"
            :hint="$t('user.organization')"
            :label="$t('user.organization')"
            :items="organizations"
          >
          </v-select>
        </v-col>
        <v-col cols="12" class="pl-1">
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
    </v-form>
  </v-container>
</template>

<script>
import AuthMixin from '../../../services/auth/auth_mixin'
import { createUser, updateUser } from '@/api/config'
import Permissions from '@/services/auth/permissions'
import { mapGetters, mapActions } from 'vuex'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

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
    edit: false,
    roles: [],
    permissions: [],
    organizations: [],
    pwd: '',
    repwd: '',
    pwdvld: true,
    user: {}
  }),
  computed: {
    checkPassEdit() {
      if (this.edit) {
        return this.pwd !== '' || this.repwd !== ''
      }
      return true
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
          notifyFailure('user.validation_error')
          return
        }

        if (this.edit === false || this.pwd !== '') {
          this.user.password = this.pwd
        }

        if (this.edit) {
          updateUser(this.user).then(() => {
            this.$validator.reset()
            notifySuccess('user.successful_edit')
          }).catch(() => {
            notifyFailure('user.error')
          })
        } else {
          createUser(this.user).then(() => {
            this.$validator.reset()
            notifySuccess('user.successful')
          }).catch(() => {
            notifyFailure('user.error')
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
          organization: {
            id: 0
          },
          roles: [],
          permissions: []
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
