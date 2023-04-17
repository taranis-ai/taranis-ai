<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <v-form @submit.prevent="add" id="form" ref="form">
      <v-row no-gutters>
        <v-btn type="submit" color="success" class="mr-4"> Submit </v-btn>
      </v-row>
      <v-row no-gutters>
        <v-col cols="6" class="pa-1">
          <v-text-field
            :label="$t('user.username')"
            name="username"
            type="text"
            v-model="user.username"
            :rules="[rules.required]"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
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
            :rules="passwordRules"
            :label="$t('user.password')"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
            v-model="repwd"
            type="password"
            :rules="passwordRules"
            :label="$t('user.password_check')"
          />
        </v-col>
      </v-row>

      <v-row no-gutters>
        <v-col cols="6" class="pr-1">
          <v-select
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
            v-model="user.roles"
            :headers="headers"
            :items="roles"
            item-key="id"
            :show-select="true"
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
            v-model="user.permissions"
            :headers="headers"
            :items="permissions"
            item-key="id"
            :show-select="true"
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
import { createUser, updateUser } from '@/api/config'
import { mapGetters, mapActions } from 'vuex'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { ref, computed } from 'vue'

export default {
  name: 'UserForm',
  props: {
    user_id: {
      type: Number,
      required: false
    }
  },
  computed: {},
  watch: {
    user_id(uid) {
      this.loadUser(uid)
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
          updateUser(this.user)
            .then(() => {
              this.$validator.reset()
              notifySuccess('user.successful_edit')
            })
            .catch(() => {
              notifyFailure('user.error')
            })
        } else {
          createUser(this.user)
            .then(() => {
              this.$validator.reset()
              notifySuccess('user.successful')
            })
            .catch(() => {
              notifyFailure('user.error')
            })
        }
      })
    },
    loadUser(user_id) {
      if (user_id !== undefined && user_id !== null) {
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
        this.edit = false
      }
    }
  },
  created() {
    this.loadOrganizations().then(() => {
      this.organizations = this.getOrganizations().items
    })

    this.loadRoles().then(() => {
      this.roles = this.getRoles().items
    })

    this.loadPermissions().then(() => {
      this.permissions = this.getPermissions().items
    })

    console.debug('Loading User: ' + this.user_id)
    this.loadUser(this.user_id)
    console.debug(this.user)
  },

  setup() {
    const headers = [
      {
        text: 'Name',
        align: 'start',
        value: 'name'
      },
      { text: 'Description', value: 'description' }
    ]

    const edit = ref(false)
    const pwd = ref('')
    const repwd = ref('')
    const organizations = ref([])
    const roles = ref([])
    const permissions = ref([])
    const user = ref({
      id: -1,
      username: '',
      name: '',
      organization: {
        id: 0
      },
      roles: [],
      permissions: []
    })

    const rules = {
      required: (value) => !!value || 'Required.',
      matchPassword: (value) => {
        if (!edit.value) {
          return !!value || 'Required.'
        }
        if (!value && !pwd.value) {
          return true
        }
        return value === pwd.value || 'Passwords must match.'
      }
    }
    const passwordRules = computed(() => {
      return edit.value
        ? [rules.matchPassword]
        : [rules.required, rules.matchPassword]
    })

    return {
      headers,
      rules,
      edit,
      roles,
      permissions,
      organizations,
      pwd,
      repwd,
      user,
      passwordRules
    }
  }
}
</script>
