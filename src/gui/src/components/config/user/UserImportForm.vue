<template>
  <v-container fluid class="mt-5 pt-0">
    <v-form
      id="form"
      ref="form"
      validate-on="submit"
      @submit.prevent="importUsers"
    >
      <v-row no-gutters>
        <v-col cols="12" class="pa-1">
          <v-file-input
            accept="application/json"
            :label="$t('user.import')"
            :rules="[rules.required]"
            @change="readJSONFile($event)"
          />
        </v-col>
        <v-col cols="12" class="pr-1">
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
      </v-row>
      <v-row no-gutters>
        <v-btn type="submit" block color="success" class="mt-5"> Submit </v-btn>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useConfigStore } from '@/stores/ConfigStore'

export default {
  name: 'UserImportForm',
  emits: ['import'],
  setup(props, { emit }) {
    const configStore = useConfigStore()
    const form = ref(null)
    const user = ref({
      organization: undefined,
      roles: []
    })

    const userList = ref([])

    const headers = [
      {
        title: 'Name',
        align: 'start',
        key: 'name'
      },
      { title: 'Description', key: 'description' }
    ]

    const roles = computed(() => configStore.roles.items)
    const organizations = computed(() => configStore.organizations.items)

    const rules = {
      required: (value) => Boolean(value) || 'Required.'
    }

    async function importUsers() {
      const { valid } = await form.value.validate()
      if (!valid) {
        return
      }

      const result = userList.value.map((item) => {
        return {
          username: item.username,
          name: item.name,
          organization: user.value.organization,
          roles: user.value.roles
        }
      })

      emit('import', result)
    }

    function readJSONFile(event) {
      const file = event.target.files[0]
      const reader = new FileReader()

      reader.onload = (e) => {
        const content = e.target.result
        const data = JSON.parse(content)
        userList.value = data.data
      }

      reader.readAsText(file)
    }

    onMounted(() => {
      configStore.loadOrganizations()
      configStore.loadRoles()
    })

    return {
      headers,
      rules,
      roles,
      organizations,
      userList,
      form,
      user,
      importUsers,
      readJSONFile
    }
  }
}
</script>
