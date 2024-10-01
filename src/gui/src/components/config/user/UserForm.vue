<template>
  <v-container fluid class="mt-5 pt-0">
    <div v-if="user_id === user.id" class="alert">
      <v-icon color="error">mdi-alert-circle</v-icon>
      <span class="alert-text">
        Please be aware, you are editing your own user. You could lock yourself
        out!
      </span>
    </div>
    <v-text-field
      v-if="edit"
      label="ID"
      density="compact"
      :disabled="true"
      :model-value="user.id"
    />
    <v-form id="form" ref="form" validate-on="submit" @submit.prevent="addUser">
      <v-row no-gutters>
        <v-col cols="6" class="pa-1">
          <v-text-field
            v-model="user.username"
            :label="$t('user.username')"
            variant="outlined"
            name="username"
            type="text"
            autocomplete="username"
            :rules="[rules.required]"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
            v-model="user.name"
            variant="outlined"
            :label="$t('user.name')"
            name="name"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
            ref="password"
            v-model="user.password"
            variant="outlined"
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
            block
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
            variant="outlined"
            item-title="name"
            item-value="id"
            :hint="$t('user.organization')"
            :label="$t('user.organization')"
            :items="organizations"
            :rules="[rules.required]"
            menu-icon="mdi-chevron-down"
          />
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
import { ref, computed, onBeforeMount, watch, onUpdated, onMounted } from 'vue'
import { useConfigStore } from '@/stores/ConfigStore'
import { useUserStore } from '@/stores/UserStore'

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
    const { user_id } = useUserStore()
    // const user_id = userStore.user_id
    const store = useConfigStore()
    const { loadOrganizations, loadRoles } = store
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

    onUpdated(() => {
      form.value.scrollIntoView({ behavior: 'smooth' })
    })

    onBeforeMount(() => {
      loadOrganizations()
      loadRoles()
    })

    onMounted(() => {
      form.value.scrollIntoView({ behavior: 'smooth' })
    })

    watch(
      () => props.userProp,
      (u) => {
        user.value = u
      }
    )

    return {
      headers,
      rules,
      roles,
      organizations,
      form,
      showPassword,
      passwordRules,
      user,
      user_id,
      generatePassword,
      addUser
    }
  }
}
</script>

<style scoped>
.alert {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

/* Use Vuetify's CSS variable for the error color */
.alert-text {
  color: var(--v-theme-error);
  /* Optional: Adjust font size or other styles */
  font-size: 16px;
}
input::-ms-clear,
input::-ms-reveal {
  display: none;
}
</style>
