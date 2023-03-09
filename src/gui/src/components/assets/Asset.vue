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
          :label="$t('form.name')"
          v-model="asset.name"
          :rules="required"
        />
      </v-col>
      <v-col cols="6">
        <v-text-field :label="$t('asset.serial')" v-model="asset.serial" />
      </v-col>
      <v-col cols="12">
        <v-textarea
          :label="$t('asset.description')"
          v-model="asset.description"
          :spellcheck="$store.state.settings.spellcheck"
        />
      </v-col>
      <v-col cols="12">
        <v-select
          :label="$t('asset.group')"
          v-model="asset.group"
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

export default {
  name: 'Asset',
  components: {},
  props: {
    asset_prop: { type: Object, default: () => {}, required: true },
    edit: { type: Boolean, default: false }
  },
  data: function () {
    return {
      required: [(v) => !!v || 'Required'],
      vulnerabilities: [],
      asset: this.asset_prop
    }
  },
  computed: {
    container_title() {
      return this.edit
        ? `${this.$t('title.edit')} asset`
        : `${this.$t('title.add_new')} asset`
    }
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
  },
  mounted() {}
}
</script>
