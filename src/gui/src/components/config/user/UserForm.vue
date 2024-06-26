<template>
  <v-container fluid class="mt-5 pt-0">
    <span v-if="edit">ID: {{ user.id }}</span>
    <v-form id="form" ref="form" validate-on="submit" @submit.prevent="addUser">
      <v-row no-gutters>
        <v-col cols="6" class="pa-1">
          <v-text-field
            v-model="user.username"
            :label="$t('user.username')"
            name="username"
            type="text"
            autocomplete="username"
            :rules="[rules.required]"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
            v-model="user.name"
            :label="$t('user.name')"
            name="name"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
            ref="password"
            v-model="user.password"
            :type="showPassword ? 'text' : 'password'"
            :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
            :rules="passwordRules"
            autocomplete="new-password"
            :label="$t('user.password')"
            @click:append-inner="showPassword = !showPassword"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-btn
            color="primary"
            class="mt-4"
            text="generate password"
            @click="user.password = generatePassword()"
          />
        </v-col>
      </v-row>

      <v-row no-gutters>
        <v-col cols="6" class="pr-1">
          <v-select
            v-model="user.organization"
            item-title="name"
            item-value="id"
            :hint="$t('user.organization')"
            :label="$t('user.organization')"
            :items="organizations"
            :rules="[rules.required]"
          >
          </v-select>
        </v-col>
        <v-col cols="12" class="pl-1">
          <v-data-table
            v-model="user.roles"
            :headers="headers"
            :items="roles"
            show-select
          >
            <template #top>
              <v-toolbar-title class="ml-3 text-center">
                {{ $t('user.roles') }}
              </v-toolbar-title>
            </template>
            <template v-if="roles.length < 10" #bottom />
          </v-data-table>
        </v-col>
        <v-col cols="12" class="pt-2">
          <v-data-table
            v-model="user.permissions"
            :headers="headers"
            :items="permissions"
            show-select
          >
            <template #top>
              <v-toolbar-title class="ml-3 text-center">
                {{ $t('user.permissions') }}
              </v-toolbar-title>
            </template>
            <template v-if="permissions.length < 10" #bottom />
          </v-data-table>
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-btn type="submit" block color="success" class="mt-5"> Submit </v-btn>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
import { createUser, updateUser } from '@/api/config'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { ref, computed, onMounted } from 'vue'
import { useConfigStore } from '@/stores/ConfigStore'

export default {
  name: 'UserForm',
  props: {
    userProp: {
      type: Object,
      required: true
    },
    edit: {
      type: Boolean,
      required: true,
      default: false
    }
  },
  emits: ['updated'],
  setup(props, { emit }) {
    const store = useConfigStore()
    const { loadOrganizations, loadRoles, loadPermissions } = store
    const form = ref(null)

    const headers = [
      {
        title: 'Name',
        align: 'start',
        key: 'name'
      },
      { title: 'Description', key: 'description' }
    ]

    const showPassword = ref(false)
    const user = ref(props.userProp)
    const roles = computed(() => store.roles.items)
    const organizations = computed(() => store.organizations.items)
    const permissions = computed(() => {
      return [...store.permissions.items].sort(
        (a, b) =>
          user.value.permissions.indexOf(b.id) -
          user.value.permissions.indexOf(a.id)
      )
    })

    const rules = {
      required: (value) => Boolean(value) || 'Required.'
    }
    const passwordRules = computed(() => {
      return props.edit ? [] : [rules.required]
    })

    function generatePassword(
      length = 20,
      characters = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz~!@-#$'
    ) {
      return Array.from(crypto.getRandomValues(new Uint32Array(length)))
        .map((x) => characters[x % characters.length])
        .join('')
    }

    async function addUser() {
      const { valid } = await form.value.validate()
      if (!valid) {
        return
      }

      if (props.edit) {
        updateUser(user.value)
          .then(() => {
            form.value.reset()
            notifySuccess('user.successful_edit')
            emit('updated')
          })
          .catch(() => {
            notifyFailure('user.error')
          })
      } else {
        createUser(user.value)
          .then(() => {
            form.value.reset()
            notifySuccess('user.successful')
            emit('updated')
          })
          .catch(() => {
            notifyFailure('user.error')
          })
      }
    }

    onMounted(() => {
      loadOrganizations()
      loadRoles()
      loadPermissions()
    })

    return {
      headers,
      rules,
      roles,
      permissions,
      organizations,
      form,
      showPassword,
      passwordRules,
      user,
      generatePassword,
      addUser
    }
  },
  watch: {
    userProp(u) {
      this.user = u
    }
  }
}
</script>

<style scoped>
input::-ms-clear,
input::-ms-reveal {
  display: none;
}
</style>
