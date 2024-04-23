<template>
  <v-card>
    <v-toolbar density="compact">
      <v-toolbar-title>{{ container_title }}</v-toolbar-title>
      <v-btn
        v-if="edit"
        prepend-icon="mdi-delete"
        color="error"
        variant="flat"
        @click="deleteGroup"
      >
        {{ $t('button.delete') }}
      </v-btn>
      <v-btn
        prepend-icon="mdi-content-save"
        color="success"
        variant="flat"
        class="ml-3"
        @click="saveAssetGroup"
      >
        {{ $t('button.save') }}
      </v-btn>
    </v-toolbar>
    <v-card-text>
      <v-row no-gutters>
        <v-col cols="12">
          <v-text-field
            v-model="assetGroup.name"
            :label="$t('form.name')"
            :rules="required"
          />
        </v-col>
        <v-col cols="12">
          <v-textarea
            v-model="assetGroup.description"
            :label="$t('form.description')"
          />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, computed } from 'vue'
import {
  createAssetGroup,
  updateAssetGroup,
  deleteAssetGroup
} from '@/api/assets'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

import { useI18n } from 'vue-i18n'

export default {
  name: 'AssetGroupItem',
  props: {
    assetGroupProp: { type: Object, required: true },
    edit: { type: Boolean, default: false }
  },
  setup(props) {
    const { t } = useI18n()

    const required = ref([(v) => !!v || 'Required'])
    const vulnerabilities = ref([])
    const assetGroup = ref(props.assetGroupProp)

    const container_title = computed(() => {
      return props.edit
        ? `${t('button.edit')} Asset Group`
        : `${t('button.add_new')} Asset Group`
    })

    const saveAssetGroup = () => {
      if (props.edit) {
        updateAssetGroup(assetGroup.value)
          .then(() => {
            notifySuccess('asset.successful_edit')
          })
          .catch(() => {
            notifyFailure('asset.failed')
          })
      } else {
        createAssetGroup(assetGroup.value)
          .then(() => {
            notifySuccess('asset.successful')
          })
          .catch(() => {
            notifyFailure('asset.failed')
          })
      }
    }

    const deleteGroup = () => {
      deleteAssetGroup(assetGroup.value)
        .then(() => {
          notifySuccess('asset.successful_delete')
        })
        .catch(() => {
          notifyFailure('asset.failed')
        })
    }

    const update = (cpes) => {
      assetGroup.value.asset_cpes = cpes
    }

    return {
      required,
      vulnerabilities,
      assetGroup,
      container_title,
      saveAssetGroup,
      deleteGroup,
      update
    }
  }
}
</script>
