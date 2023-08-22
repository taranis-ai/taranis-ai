<template>
  <div>
    <DataTable
      v-model:items="attributes.items"
      :add-button="true"
      :header-filter="['tag', 'id', 'name', 'description']"
      sort-by-item="id"
      :action-column="true"
      @delete-item="deleteItem"
      @edit-item="editItem"
      @add-item="addItem"
      @update-items="updateData"
    />
    <EditConfig
      v-if="showForm"
      :config-data="formData"
      :form-format="formFormat"
      :title="editTitle"
      @submit="handleSubmit"
    ></EditConfig>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import DataTable from '@/components/common/DataTable.vue'
import EditConfig from '@/components/config/EditConfig.vue'
import { deleteAttribute, createAttribute, updateAttribute } from '@/api/config'
import { useConfigStore } from '@/stores/ConfigStore'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useMainStore } from '@/stores/MainStore'
import { storeToRefs } from 'pinia'

export default {
  name: 'AttributesView',
  components: {
    DataTable,
    EditConfig
  },
  setup() {
    const formData = ref({})
    const edit = ref(false)
    const showForm = ref(false)

    const formFormat = [
      {
        name: 'id',
        label: 'ID',
        type: 'text',
        disabled: true
      },
      {
        name: 'name',
        label: 'Name',
        type: 'text',
        rules: [(v) => !!v || 'Required']
      },
      {
        name: 'description',
        label: 'Description',
        type: 'textarea',
        rules: [(v) => !!v || 'Required']
      },
      {
        name: 'default_value',
        label: 'Default Value',
        type: 'text'
      },
      {
        name: 'type',
        label: 'Type',
        type: 'select',
        items: [
          'STRING',
          'NUMBER',
          'BOOLEAN',
          'RADIO',
          'ENUM',
          'TEXT',
          'RICH_TEXT',
          'DATE',
          'TIME',
          'DATE_TIME',
          'LINK',
          'ATTACHMENT',
          'TLP',
          'CVE',
          'CPE',
          'CVSS'
        ],
        rules: [(v) => !!v || 'Required']
      },
      {
        name: 'validator',
        label: 'Validator',
        type: 'select',
        items: ['NONE', 'EMAIL', 'NUMBER', 'RANGE', 'REGEXP']
      },
      {
        name: 'validator_parameter',
        label: 'Validator Parameter',
        type: 'text'
      }
    ]
    const configStore = useConfigStore()
    const mainStore = useMainStore()

    const { attributes } = storeToRefs(configStore)

    const updateData = async () => {
      configStore.loadAttributes().then(() => {
        mainStore.itemCountTotal = attributes.value.total_count
        mainStore.itemCountFiltered = attributes.value.items.length
      })
    }

    const editTitle = computed(() => {
      return edit.value
        ? `Edit Attribute: '${formData.value['name']}'`
        : 'Add Attribute'
    })

    const addItem = () => {
      formData.value = {}
      edit.value = false
      showForm.value = true
    }

    const editItem = (item) => {
      console.debug(item)
      formData.value = item
      edit.value = true
      showForm.value = true
    }

    const handleSubmit = (submittedData) => {
      const nonemptyEntries = Object.entries(submittedData).filter(
        ([_, value]) => value !== ''
      )
      const nonemptyValues = Object.fromEntries(nonemptyEntries)
      if (edit.value) {
        updateItem(nonemptyValues)
      } else {
        createItem(nonemptyValues)
      }
      showForm.value = false
    }

    const deleteItem = (item) => {
      if (!item.default) {
        deleteAttribute(item)
          .then(() => {
            notifySuccess(`Successfully deleted ${item.name}`)
            updateData()
          })
          .catch(() => {
            notifyFailure(`Failed to delete ${item.name}`)
          })
      }
    }

    const createItem = (item) => {
      createAttribute(item)
        .then(() => {
          notifySuccess(`Successfully created ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to create ${item.name}`)
        })
    }

    const updateItem = (item) => {
      updateAttribute(item)
        .then(() => {
          notifySuccess(`Successfully updated ${item.name}`)
          updateData()
        })
        .catch(() => {
          notifyFailure(`Failed to update ${item.name}`)
        })
    }

    onMounted(() => {
      updateData()
    })

    return {
      formData,
      editTitle,
      formFormat,
      attributes,
      showForm,
      addItem,
      editItem,
      handleSubmit,
      deleteItem,
      updateData
    }
  }
}
</script>
