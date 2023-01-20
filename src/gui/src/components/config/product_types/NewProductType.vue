<template>
  <v-container fluid class="ma-5 mt-5 pa-5 pt-0">
  <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
    <v-row no-gutters>
      <v-col
        cols="12"
        class="caption grey--text"
        v-if="edit"
      >ID: {{ product.id }}</v-col>
      <v-col cols="12">
        <v-combobox
          :disabled="edit"
          v-model="selected_presenter"
          :items="presenters"
          item-text="name"
          :label="$t('product_type.presenter')"
        />
      </v-col>
    </v-row>

    <v-row no-gutters>
      <v-col cols="12">
        <v-text-field
          v-if="selected_presenter"
          :disabled="!canUpdate"
          :label="$t('product_type.name')"
          name="name"
          type="text"
          v-model="product.title"
          v-validate="'required'"
          data-vv-name="name"
          :error-messages="errors.collect('name')"
          :spellcheck="$store.state.settings.spellcheck"
        />
      </v-col>
      <v-col cols="12">
        <v-textarea
          v-if="selected_presenter"
          :disabled="!canUpdate"
          :label="$t('product_type.description')"
          name="description"
          v-model="product.description"
          :spellcheck="$store.state.settings.spellcheck"
        />
      </v-col>
    </v-row>

    <v-row no-gutters>
      <v-col cols="12">
        <FormParameters
          v-if="selected_presenter"
          :disabled="!canUpdate"
          ui="text"
          :sources="selected_presenter.parameters"
          :values="values"
        />
      </v-col>
    </v-row>

    <v-row no-gutters class="pt-2">
      <v-col cols="12">
        <v-alert v-if="show_validation_error" dense type="error" text>
          {{ $t('product_type.validation_error') }}
        </v-alert>
        <v-alert v-if="show_error" dense type="error" text>
          {{ $t('product_type.error') }}
        </v-alert>
      </v-col>
    </v-row>

    <ProductTypeHelp></ProductTypeHelp>
  </v-form>
  </v-container>
</template>

<script>
import { createProductType, updateProductType } from '@/api/config'
import FormParameters from '../../common/FormParameters'
import ProductTypeHelp from './ProductTypeHelp'
import AuthMixin from '@/services/auth/auth_mixin'
import Permissions from '@/services/auth/permissions'

export default {
  name: 'NewProductType',
  components: {
    FormParameters,
    ProductTypeHelp
  },
  data: () => ({
    edit: false,
    selected_type: null,
    show_validation_error: false,
    show_error: false,
    selected_presenter: null,
    values: [],
    presenters: ['PDF', 'HTML', 'TEXT', 'MISP'],
    product: {
      id: -1,
      title: '',
      description: '',
      presenter_id: '',
      parameter_values: []
    }
  }),
  mixins: [AuthMixin],
  computed: {
    canCreate() {
      return this.checkPermission(Permissions.CONFIG_PRODUCT_TYPE_CREATE)
    },
    canUpdate() {
      return (
        this.checkPermission(Permissions.CONFIG_PRODUCT_TYPE_UPDATE) ||
        !this.edit
      )
    }
  },

  methods: {
    addProduct() {
      this.edit = false
      this.show_error = false
      this.selected_presenter = null
      this.product.id = -1
      this.product.title = ''
      this.product.description = ''
      this.product.presenter_id = ''
      this.values = []
      this.product.parameter_values = []
      this.$validator.reset()
    },

    cancel() {
      this.$validator.reset()
    },

    add() {
      this.$validator.validateAll().then(() => {
        if (!this.$validator.errors.any()) {
          this.show_validation_error = false
          this.show_error = false

          this.product.presenter_id = this.selected_presenter.id

          for (let i = 0; i < this.selected_presenter.parameters.length; i++) {
            this.product.parameter_values[i] = {
              value: this.values[i],
              parameter: this.selected_presenter.parameters[i]
            }
          }

          if (this.edit) {
            updateProductType(this.product)
              .then(() => {
                this.$validator.reset()
                this.visible = false
                this.$root.$emit('notification', {
                  type: 'success',
                  loc: 'product_type.successful_edit'
                })
              })
              .catch(() => {
                this.show_error = true
              })
          } else {
            createProductType(this.product)
              .then(() => {
                this.$validator.reset()
                this.$root.$emit('notification', {
                  type: 'success',
                  loc: 'product_type.successful'
                })
              })
              .catch(() => {
                this.show_error = true
              })
          }
        } else {
          this.show_validation_error = true
        }
      })
    }
  },
  mounted() {
    this.loadPresenters().then(() => {
      this.presenters = this.getPresenters()
    })

    if (this.product_id) {
      this.edit = true
      this.show_error = false

      // this.product.id = data.id
      // this.product.title = data.title
      // this.product.description = data.description
      // this.product.presenter_id = data.presenter_id

      this.product.parameter_values = []
    }
  },
  beforeDestroy() {
    this.$root.$off('show-edit')
  }
}
</script>
