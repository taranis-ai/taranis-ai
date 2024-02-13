<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <span v-if="edit" class="caption">ID: {{ acl.id }}</span>
    <v-form id="form" ref="form" validate-on="submit" @submit.prevent="add">
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
            v-model="acl.item_type"
            :items="types"
            item-title="title"
            item-value="id"
            :return-object="false"
            :label="$t('acl.item_type')"
            :rules="[rules.required]"
          />
        </v-col>
        <v-col cols="6" class="pa-1">
          <v-text-field
            v-model="acl.item_id"
            :label="$t('acl.item_id')"
            name="item_id"
            type="text"
            :rules="[rules.required]"
          />
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col cols="12" class="d-flex">
          <v-checkbox
            v-model="acl.writeable"
            class="pr-8"
            :label="$t('acl.writeable')"
            name="writeable"
          />
        </v-col>
      </v-row>
      <v-row no-gutters>
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
              <h2 class="ml-4 mb-2">{{ $t('acl.roles') }}</h2>
            </template>
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
import { createACLEntry, updateACLEntry } from '@/api/config'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useConfigStore } from '@/stores/ConfigStore'
import { ref, computed, onMounted } from 'vue'

export default {
  name: 'ACLForm',
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
    const configStore = useConfigStore()
    const form = ref(null)
    const acl = ref(props.aclProp)
    const roles = computed(() => configStore.roles.items)
    const rules = {
      required: (v) => Boolean(v) || 'Required.'
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
      { id: 'NEWS_ITEM', title: 'News Item'},
      { id: 'OSINT_SOURCE', title: 'OSINT Source' },
      { id: 'OSINT_SOURCE_GROUP', title: 'OSINT Source Group' },
      { id: 'PRODUCT_TYPE', title: 'Product Type' },
      { id: 'REPORT_ITEM', title: 'Report Item' },
      { id: 'REPORT_ITEM_TYPE', title: 'Report Item Type' },
      { id: 'WORD_LIST', title: 'Word List' }
    ]

    const selected_roles = []

    const add = async () => {
      const { valid } = await form.value.validate()
      if (!valid) {
        return
      }

      acl.value.roles = selected_roles.map((role) => ({ id: role.id }))

      if (props.edit) {
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

    onMounted(() => {
      configStore.loadRoles()
    })

    return {
      acl,
      form,
      rules,
      headers_user,
      headers_role,
      selected_roles,
      types,
      roles,
      add
    }
  }
}
</script>
