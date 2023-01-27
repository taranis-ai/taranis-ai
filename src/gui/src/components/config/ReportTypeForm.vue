<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
    <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
      <v-row no-gutters>
        <v-col cols="12" class="cation grey--text" v-if="edit">
          ID:{{ report_type.id }}
        </v-col>
        <v-col cols="12">
          <v-text-field
            :disabled="!canUpdate"
            :label="$t('report_type.name')"
            name="name"
            v-model="report_type.title"
            v-validate="'required'"
            data-vv-name="name"
            :error-messages="errors.collect('name')"
            :spellcheck="$store.state.settings.spellcheck"
          />
        </v-col>
        <v-col cols="12">
          <v-textarea
            :disabled="!canUpdate"
            :label="$t('report_type.description')"
            name="description"
            v-model="report_type.description"
            :spellcheck="$store.state.settings.spellcheck"
          />
        </v-col>
      </v-row>

      <v-row no-gutters>
        <v-col cols="12">
          <v-btn v-if="canUpdate" color="primary" @click="addAttributeGroup">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{ $t('report_type.new_group') }}</span>
          </v-btn>
        </v-col>
        <v-col cols="12">
          <v-card
            style="margin-top: 8px"
            v-for="(group, index) in report_type.attribute_groups"
            :key="group.id"
          >
            <v-toolbar dark height="32px">
              <v-spacer></v-spacer>
              <v-toolbar-items v-if="canUpdate">
                <v-icon @click="moveAttributeGroupUp(index)">
                  mdi-arrow-up-bold
                </v-icon>
                <v-icon @click="moveAttributeGroupDown(index)">
                  mdi-arrow-down-bold
                </v-icon>

                <v-icon @click="deleteAttributeGroup(index)"> delete </v-icon>
              </v-toolbar-items>
            </v-toolbar>

            <v-card-text>
              <v-text-field
                :disabled="!canUpdate"
                :label="$t('report_type.name')"
                name="name"
                type="text"
                v-model="group.title"
                :spellcheck="$store.state.settings.spellcheck"
              ></v-text-field>
              <v-textarea
                :disabled="!canUpdate"
                :label="$t('report_type.description')"
                name="description"
                v-model="group.description"
                :spellcheck="$store.state.settings.spellcheck"
              ></v-textarea>
              <v-text-field
                :disabled="!canUpdate"
                :label="$t('report_type.section_title')"
                name="section_title"
                v-model="group.section_title"
                :spellcheck="$store.state.settings.spellcheck"
              ></v-text-field>
              <ConfigTable
                :addButton="true"
                :showSearch="false"
                :items.sync="
                  report_type.attribute_groups[index].attribute_group_items
                "
                :actionColumn="true"
                @delete-item="(item) => deleteAttributeItem(index, item)"
                @edit-item="(item) => editAttributeItem(index, item)"
                @add-item="() => addAttributeItem(index)"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-form>
  </v-container>
</template>

<script>
import { createReportItemType, updateReportItemType } from '@/api/config'
import ConfigTable from '../../components/config/ConfigTable'
import AuthMixin from '@/services/auth/auth_mixin'
import Permissions from '@/services/auth/permissions'
import { mapActions, mapGetters } from 'vuex'
import { notifySuccess, notifyFailure } from '@/utils/helpers'

export default {
  name: 'NewReportType',
  components: {
    ConfigTable
  },
  data: () => ({
    edit: false,
    attribute_templates: [],
    report_type: {
      id: -1,
      title: '',
      description: '',
      attribute_groups: []
    }
  }),
  props: {
    report_type_data: Object
  },
  mixins: [AuthMixin],
  computed: {
    canCreate() {
      return this.checkPermission(Permissions.CONFIG_REPORT_TYPE_CREATE)
    },
    canUpdate() {
      return (
        this.checkPermission(Permissions.CONFIG_REPORT_TYPE_UPDATE) ||
        !this.edit
      )
    }
  },
  methods: {
    ...mapGetters('config', ['getAttributes']),
    ...mapActions('config', ['loadAttributes']),
    addAttributeItem(index) {
      const default_attribute = {
        index: 0,
        id: -1,
        attribute_id: -1,
        attribute_name: '',
        title: '',
        description: '',
        min_occurrence: 0,
        max_occurrence: 1
      }
      this.report_type.attribute_groups[index].attribute_group_items = default_attribute
      console.debug(`Add Attribute Item ${default_attribute}`)
    },
    editAttributeItem(index, item) {
      console.debug(`Edit Attribute Item ${item}`)
    },
    deleteAttributeItem(index, item) {
      console.debug(`Delete Attribute Item ${item}`)
    },
    addReportType() {
      this.edit = false
      this.report_type.id = -1
      this.report_type.title = ''
      this.report_type.description = ''
      this.report_type.categories = []
      this.report_type.attribute_groups = []
      this.$validator.reset()
    },

    addAttributeGroup() {
      this.report_type.attribute_groups.push({
        index: this.report_type.attribute_groups.length,
        id: -1,
        title: '',
        description: '',
        section: -1,
        section_title: '',
        attribute_group_items: []
      })
    },

    moveAttributeGroupUp(index) {
      if (index > 0) {
        this.report_type.attribute_groups.splice(
          index - 1,
          0,
          this.report_type.attribute_groups.splice(index, 1)[0]
        )
      }
    },

    moveAttributeGroupDown(index) {
      if (index < this.report_type.attribute_groups.length - 1) {
        this.report_type.attribute_groups.splice(
          index + 1,
          0,
          this.report_type.attribute_groups.splice(index, 1)[0]
        )
      }
    },

    deleteAttributeGroup(index) {
      this.report_type.attribute_groups.splice(index, 1)
    },

    add() {
      this.$validator.validateAll().then(() => {
        if (!this.$validator.errors.any()) {
          for (let x = 0; x < this.report_type.attribute_groups.length; x++) {
            this.report_type.attribute_groups[x].index = x

            for (
              let y = 0;
              y <
              this.report_type.attribute_groups[x].attribute_group_items.length;
              y++
            ) {
              this.report_type.attribute_groups[x].attribute_group_items[
                y
              ].index = y
            }
          }

          if (this.edit) {
            updateReportItemType(this.report_type)
              .then(() => {
                this.$validator.reset()
                notifySuccess('report_type.successful_edit')
              })
              .catch(() => {
                notifyFailure('report_type.error')
              })
          } else {
            createReportItemType(this.report_type)
              .then(() => {
                this.$validator.reset()
                notifySuccess('report_type.successful')
              })
              .catch(() => {
                notifyFailure('report_type.error')
              })
          }
        } else {
          notifyFailure('report_type.validation_error')
        }
      })
    }
  },
  mounted() {
    this.loadAttributes().then(() => {
      this.attribute_templates = this.getAttributes().items
    })

    if (this.report_type_data) {
      this.edit = true
      this.report_type = this.report_type_data
    }
  }
}
</script>
