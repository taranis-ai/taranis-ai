<template>
  <v-card>
    <v-toolbar density="compact">
      <v-toolbar-title>{{ container_title }}</v-toolbar-title>
      <v-btn
        prepend-icon="mdi-content-save"
        color="success"
        variant="flat"
        @click="saveAsset"
      >
        {{ $t('button.save') }}
      </v-btn>
    </v-toolbar>
    <v-card-text>
      <v-row no-gutters>
        <v-col cols="6">
          <v-text-field
            v-model="asset.name"
            :label="$t('form.name')"
            :rules="required"
          />
        </v-col>
        <v-col cols="5" offset="1">
          <v-text-field v-model="asset.serial" :label="$t('asset.serial')" />
        </v-col>
        <v-col cols="12">
          <v-textarea
            v-model="asset.description"
            :label="$t('form.description')"
          />
        </v-col>
        <v-col cols="12">
          <v-select
            v-model="asset.group"
            :label="$t('asset.group')"
            :items="asset_groups.items"
            item-value="id"
            item-title="name"
            menu-icon="mdi-chevron-down"
          />
        </v-col>
      </v-row>
      <v-row no-gutters>
        <v-col cols="12">
          {{ asset.asset_cpes }}
        </v-col>
        <v-col cols="12">
          {{ vulnerabilities }}
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { createAsset, updateAsset } from '@/api/assets'
import { notifySuccess, notifyFailure } from '@/utils/helpers'
import { useAssetsStore } from '@/stores/AssetsStore'
import { useI18n } from 'vue-i18n'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'

export default {
  name: 'AssetItem',
  props: {
    assetProp: { type: Object, required: true },
    edit: { type: Boolean, default: false }
  },
  emits: ['assetcreated'],
  setup(props, { emit }) {
    const { t } = useI18n()
    const assetsStore = useAssetsStore()

    const required = ref([(v) => !!v || 'Required'])
    const vulnerabilities = ref([])
    const asset = ref(props.assetProp)
    const { asset_groups } = storeToRefs(assetsStore)
    const router = useRouter()

    const container_title = computed(() => {
      return props.edit
        ? `${t('button.edit')} asset`
        : `${t('button.add_new')} asset`
    })

    const saveAsset = () => {
      if (props.edit) {
        updateAsset(asset.value)
          .then(() => {
            notifySuccess('asset.successful_edit')
          })
          .catch(() => {
            notifyFailure('asset.failed')
          })
      } else {
        createAsset(asset.value)
          .then(() => {
            router.push('/asset/' + response.data.id)
            emit('assetcreated', response.data.id)
          })
          .catch(() => {
            notifyFailure('asset.failed')
          })
      }
    }

    onMounted(() => {
      assetsStore.loadAssetGroups()
    })

    const update = (cpes) => {
      asset.value.asset_cpes = cpes
    }

    return {
      required,
      vulnerabilities,
      asset,
      container_title,
      asset_groups,
      saveAsset,
      update
    }
  }
}
</script>
