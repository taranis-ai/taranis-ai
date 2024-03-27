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
          <v-combobox
            v-model="acl.item_id"
            :items="item_ids"
            :return-object="false"
            item-title="title"
            item-value="id"
            :label="$t('acl.item_id')"
            :rules="[rules.required]"
          />
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col cols="4" offset="1" class="d-flex">
          <v-btn-toggle v-model="acl.read_only" class="w-100">
            <v-btn
              class="flex-grow-1"
              :value="true"
              :text="$t('acl.readonly')"
            />
            <v-btn
              class="flex-grow-1"
              border-color="red-darken-4"
              :value="false"
              :text="$t('acl.writeable')"
            />
          </v-btn-toggle>
        </v-col>
        <v-col cols="3" offset="3" class="d-flex">
          <v-switch
            v-model="acl.enabled"
            color="success"
            :label="acl.enabled ? $t('acl.enabled') : $t('acl.disabled')"
          />
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col cols="12" class="pt-2">
          <v-data-table
            v-model="acl.roles"
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
import { useConfigStore } from '@/stores/ConfigStore'
import { ref, computed, onBeforeMount, watch } from 'vue'

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
  emits: ['submit'],
  setup(props, { emit }) {
    const configStore = useConfigStore()
    const form = ref(null)
    const acl = ref(props.aclProp)
    const roles = computed(() => configStore.roles.items)
    const rules = {
      required: (v) => Boolean(v) || 'Required.'
    }

    const item_ids = ref([])

    const headers_role = [
      {
        title: 'Name',
        key: 'name'
      },
      { title: 'Description', key: 'description' }
    ]

    const types = [
      { id: 'osint_source', title: 'OSINT Source' },
      { id: 'osint_source_group', title: 'OSINT Source Group' },
      { id: 'product_type', title: 'Product Type' },
      { id: 'report_item_type', title: 'Report Type' },
      { id: 'word_list', title: 'Word List' }
    ]

    const add = async () => {
      const { valid } = await form.value.validate()
      if (!valid) {
        return
      }

      emit('submit', acl.value)
    }

    const load_item_ids = async (item_type) => {
      if (item_type === 'osint_source') {
        await configStore.loadOSINTSources()
        item_ids.value = configStore.osint_sources.items.map((item) => ({
          id: item.id.toString(),
          title: item.name
        }))
      } else if (item_type === 'osint_source_group') {
        await configStore.loadOSINTSourceGroups()
        item_ids.value = configStore.osint_source_groups.items.map((item) => ({
          id: item.id.toString(),
          title: item.name
        }))
      } else if (item_type === 'product_type') {
        await configStore.loadProductTypes()
        item_ids.value = configStore.product_types.items.map((item) => ({
          id: item.id.toString(),
          title: item.title
        }))
      } else if (item_type === 'report_item_type') {
        await configStore.loadReportTypes()
        item_ids.value = configStore.report_item_types.items.map((item) => ({
          id: item.id.toString(),
          title: item.title
        }))
      } else if (item_type === 'word_list') {
        await configStore.loadWordLists()
        item_ids.value = configStore.word_lists.items.map((item) => ({
          id: item.id.toString(),
          title: item.name
        }))
      }
    }

    onBeforeMount(async () => {
      await load_item_ids(acl.value.item_type)
      configStore.loadRoles()
    })

    watch(
      () => acl.value.item_type,
      (newVal) => {
        load_item_ids(newVal)
      }
    )

    watch(
      () => props.aclProp,
      (newVal) => {
        acl.value = newVal
      }
    )

    return {
      acl,
      form,
      rules,
      headers_role,
      item_ids,
      types,
      roles,
      add
    }
  }
}
</script>
