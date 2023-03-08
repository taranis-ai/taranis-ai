<template>
  <v-container fluid>
    <v-app-bar :elevation="2" app class="mt-12">
      <v-toolbar-title>{{ container_title }}</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn color="success" class="mr-2" @click="saveReportItem">
        <v-icon left>mdi-content-save</v-icon>
        <span>{{ $t('button.save') }}</span>
      </v-btn>
    </v-app-bar>

    <v-row no-gutters>
      <v-col cols="6" class="pr-3">
        <v-text-field
          :label="$t('asset.name')"
          v-model="asset.name"
          :rules="required"
        />
      </v-col>
      <v-col cols="6" class="pr-3">
        <v-text-field :hint="$t('asset.serial')" v-model="asset.serial" />
      </v-col>
      <v-col cols="12" class="pr-3">
        <v-textarea
          :label="$t('asset.description')"
          v-model="asset.description"
          :spellcheck="$store.state.settings.spellcheck"
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

export default {
  name: 'Asset',
  components: {},
  props: {
    asset_prop: { type: Object, default: () => {}, required: true },
    edit: { type: Boolean, default: false }
  },
  emits: ['reportcreated'],
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
    addAsset() {
      this.visible = true
      this.asset.id = -1
      this.asset.name = ''
      this.asset.serial = ''
      this.asset.description = ''
      this.asset.asset_cpes = []
      this.asset.asset_group_id = ''
      this.$validator.reset()
    },

    add() {
      if (this.edit === true) {
        updateAsset(this.asset)
          .then(() => {
            this.$validator.reset()
            this.visible = false
            this.$root.$emit('notification', {
              type: 'success',
              loc: 'asset.successful_edit'
            })
          })
          .catch(() => {
            this.show_error = true
          })
      } else {
        createAsset(this.asset)
          .then(() => {
            this.$validator.reset()
            this.visible = false
            this.$root.$emit('notification', {
              type: 'success',
              loc: 'asset.successful'
            })
          })
          .catch(() => {
            this.show_error = true
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
