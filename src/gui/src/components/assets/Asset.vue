<template>
  <v-container fluid>
    <v-app-bar :elevation="2" app class="mt-12">
      <v-toolbar-title>{{ container_title }}</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn color="success" class="mr-2" @click="saveAsset">
        <v-icon left>mdi-content-save</v-icon>
        <span>{{ $t('button.save') }}</span>
      </v-btn>
    </v-app-bar>

    <v-row no-gutters>
      <v-col cols="6">
        <v-text-field
          v-model="asset.name"
          :label="$t('form.name')"
          :rules="required"
        />
      </v-col>
      <v-col cols="6">
        <v-text-field v-model="asset.serial" :label="$t('asset.serial')" />
      </v-col>
      <v-col cols="12">
        <v-textarea
          v-model="asset.description"
          :label="$t('asset.description')"
          :spellcheck="spellcheck"
        />
      </v-col>
      <v-col cols="12">
        <v-select
          v-model="asset.group"
          :label="$t('asset.group')"
          :items="['foo', 'bar', 'fizz', 'buzz']"
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
  </v-container>
</template>

<script>
import { createAsset, updateAsset } from '@/api/assets'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

import { mapState } from 'pinia'
import { useSettingsStore } from '@/stores/SettingsStore'

export default {
  name: 'AssetView',
  props: {
    assetProp: { type: Object, required: true },
    edit: { type: Boolean, default: false }
  },
  data: function () {
    return {
      required: [(v) => !!v || 'Required'],
      vulnerabilities: [],
      asset: this.assetProp
    }
  },
  computed: {
    container_title() {
      return this.edit
        ? `${this.$t('button.edit')} asset`
        : `${this.$t('button.add_new')} asset`
    },
    ...mapState(useSettingsStore, ['spellcheck'])
  },
  methods: {
    saveAsset() {
      if (this.edit) {
        updateAsset(this.asset)
          .then(() => {
            notifySuccess('asset.successful_edit')
          })
          .catch(() => {
            notifyFailure('asset.failed')
          })
      } else {
        createAsset(this.asset)
          .then(() => {
            notifySuccess('asset.successful')
          })
          .catch(() => {
            notifyFailure('asset.failed')
          })
      }
    },

    update(cpes) {
      this.asset.asset_cpes = cpes
    }
  }
}
</script>
