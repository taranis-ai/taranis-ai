<template>
  <div>
    <DataTable
      v-model:items="acls.items"
      :add-button="true"
      :header-filter="['tag', 'id', 'name', 'username', 'actions']"
      sort-by-item="id"
      tag-icon="mdi-lock-check"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <ACLForm v-if="showForm" :acl-prop="acl" :edit="edit" />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import ACLForm from '@/components/config/user/ACLForm.vue'
import { deleteACLEntry, createACLEntry, updateACLEntry } from '@/api/config'
import { notifySuccess } from '@/utils/helpers'
import { useConfigStore } from '@/stores/ConfigStore'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'ACLsView',
  components: {
    DataTable,
    ACLForm
  },
  setup() {
    const showForm = ref(false)
    const edit = ref(false)
    const acl = ref({})
    const configStore = useConfigStore()
    const { acls } = storeToRefs(configStore)
    const mainStore = useMainStore()

    const updateData = () => {
      configStore.loadACLEntries().then(() => {
        mainStore.itemCountTotal = acls.total_count
        mainStore.itemCountFiltered = acls.items.length
      })
    }

    const addItem = () => {
      acl.value = {
        name: '',
        description: '',
        users: [],
        roles: []
      }
      edit.value = false
      showForm.value = true
    }

    const editItem = (item) => {
      acl.value = item
      edit.value = true
      showForm.value = true
    }

    const handleSubmit = (submittedData) => {
      if (edit.value) {
        updateItem(submittedData)
      } else {
        createItem(submittedData)
      }
      showForm.value = false
    }

    const deleteItem = (item) => {
      deleteACLEntry(item).then(() => {
        notifySuccess(`Successfully deleted ${item.name}`)
        updateData()
      })
    }

    const createItem = (item) => {
      createACLEntry(item).then(() => {
        notifySuccess(`Successfully created ${item.name}`)
        updateData()
      })
    }

    const updateItem = (item) => {
      updateACLEntry(item).then(() => {
        notifySuccess(`Successfully updated ${item.name}`)
        updateData()
      })
    }

    onMounted(() => {
      updateData()
    })

    return {
      showForm,
      acl,
      edit,
      acls,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      createItem,
      updateItem,
      updateData
    }
  }
}
</script>
