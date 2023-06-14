<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <span v-if="edit" class="caption">ID: {{ acl.id }}</span>
    <v-form id="form" ref="form" validate-on="submit" @submit.prevent="add">
      <v-row no-gutters>
        <v-btn type="submit" color="success" class="mr-4"> Submit </v-btn>
      </v-row>
      <v-row no-gutters>
        <v-col cols="12" class="pa-1">
          <v-text-field
            v-model="acl.name"
            :label="$t('acl.name')"
            name="name"
            type="text"
            :rules="[rules.required]"
          />
        </v-col>
        <v-col cols="12" class="pa-1">
          <v-textarea
            v-model="acl.description"
            :label="$t('acl.description')"
            name="description"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-combobox
            v-model="selected_type"
            :items="types"
            item-title="title"
            :label="$t('acl.item_type')"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
            v-model="acl.item_id"
            :label="$t('acl.item_id')"
            name="item_id"
            type="text"
          />
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col cols="12" class="d-flex">
          <v-checkbox
            v-model="acl.see"
            class="pr-8"
            :label="$t('acl.see')"
            name="see"
          />
          <v-checkbox
            v-model="acl.access"
            class="pr-8"
            :label="$t('acl.access')"
            name="access"
          />
          <v-checkbox
            v-model="acl.modify"
            class="pr-8"
            :label="$t('acl.modify')"
            name="modify"
          />
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col cols="12">
          <v-checkbox
            v-model="acl.everyone"
            :label="$t('acl.everyone')"
            name="everyone"
          />
        </v-col>
        <v-col cols="12">
          <v-data-table
            v-model="selected_users"
            :headers="headers_user"
            :items="users"
            item-key="id"
            :show-select="true"
            class="elevation-1"
          >
            <template #top>
              <v-toolbar flat color="white">
                <v-toolbar-title>{{ $t('acl.users') }}</v-toolbar-title>
              </v-toolbar>
            </template>
          </v-data-table>
        </v-col>
        <v-col cols="12" class="pt-2">
          <v-data-table
            v-model="selected_roles"
            :headers="headers_role"
            :items="roles"
            item-key="id"
            :show-select="true"
            class="elevation-1"
          >
            <template #top>
              <v-toolbar flat color="white">
                <v-toolbar-title>{{ $t('acl.roles') }}</v-toolbar-title>
              </v-toolbar>
            </template>
          </v-data-table>
        </v-col>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
import { createACLEntry, updateACLEntry } from '@/api/config'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useConfigStore } from '@/stores/ConfigStore'
import { ref, computed, onMounted } from 'vue'

export default {
  name: 'NewACL',
  props: {
    aclProp: {
      type: Object,
      required: true
    },
    edit: {
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const store = useConfigStore()
    const { loadUsers, loadRoles } = store
    const form = ref(null)
    const acl = ref(props.aclProp)
    const roles = computed(() => store.roles.items)
    const users = computed(() => store.users.items)
    const rules = {
      required: (value) => !!value || 'Required.'
    }

    const headers_user = [
      {
        title: 'Username',
        key: 'username'
      },
      { title: 'Name', key: 'name' }
    ]

    const headers_role = [
      {
        title: 'Name',
        key: 'name'
      },
      { title: 'Description', key: 'description' }
    ]

    const types = [
      { id: 'COLLECTOR', title: 'Collector' },
      { id: 'DELEGATION', title: 'Delegation' },
      { id: 'OSINT_SOURCE', title: 'OSINT Source' },
      { id: 'OSINT_SOURCE_GROUP', title: 'OSINT Source Group' },
      { id: 'PRODUCT_TYPE', title: 'Product Type' },
      { id: 'REPORT_ITEM', title: 'Report Item' },
      { id: 'REPORT_ITEM_TYPE', title: 'Report Item Type' },
      { id: 'WORD_LIST', title: 'Word List' }
    ]
    const selected_type = null

    const selected_users = []
    const selected_roles = []

    const add = () => {
      if (props.edit) {
        if (selected_type !== null) {
          acl.value.item_type = selected_type.id
        }

        acl.value.users = selected_users.map((user) => ({ id: user.id }))
        acl.value.roles = selected_roles.map((role) => ({ id: role.id }))

        if (edit) {
          updateACLEntry(acl.value)
            .then(() => {
              notifySuccess('acl.successful_edit')
            })
            .catch(() => {
              notifyFailure('acl.error_edit')
            })
        } else {
          createACLEntry(acl.value)
            .then(() => {
              notifySuccess('acl.successful')
            })
            .catch(() => {
              notifyFailure(roles, 'acl.error')
            })
        }
      }
    }

    onMounted(() => {
      loadUsers()
      loadRoles()
    })

    return {
      acl,
      form,
      rules,
      headers_user,
      headers_role,
      selected_roles,
      selected_users,
      selected_type,
      types,
      roles,
      users,
      add
    }
  }
}
</script>
