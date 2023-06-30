<template>
  <v-card>
    <v-toolbar density="compact">
      <v-toolbar-title>{{ container_title }}</v-toolbar-title>
      <v-spacer></v-spacer>
      <v-btn
        prepend-icon="mdi-content-save"
        color="success"
        variant="flat"
        @click="saveProduct"
      >
        {{ $t('product.publish') }}
      </v-btn>
    </v-toolbar>
    <v-card-text>
      <v-form id="form" ref="form" class="px-4">
        <v-row no-gutters>
          <v-col cols="6" class="pr-3">
            <v-select
              v-model="product.product_type_id"
              :items="product_types"
              item-value="id"
              no-data-text="No Product Types available - please create one under Admin > Product Types"
              :label="$t('product.product_type')"
            />
          </v-col>
          <v-col cols="6" class="pr-3">
            <v-text-field
              v-model="product.title"
              :label="$t('product.title')"
              name="title"
            />
          </v-col>
          <v-col cols="12" class="pr-3">
            <v-textarea
              v-model="product.description"
              :label="$t('product.description')"
              name="description"
            />
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col cols="12">
            {{ product.report_items }}
          </v-col>
        </v-row>
        <v-row no-gutters>
          <v-col cols="12">
            <v-select
              v-model="preset.selected"
              :items="publisher_presets"
              item-title="name"
              item-value="id"
              :label="$t('product.publisher')"
              multiple
            >
            </v-select>
          </v-col>
        </v-row>
        <v-row no-gutters class="pt-4">
          <v-col cols="6">
            <v-btn depressed small @click="previewProduct">
              <v-icon left>mdi-eye-outline</v-icon>
              <span>{{ $t('product.preview') }}</span>
            </v-btn>
          </v-col>
        </v-row>
      </v-form>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { createProduct, updateProduct } from '@/api/publish'
import { useI18n } from 'vue-i18n'
import { useConfigStore } from '@/stores/ConfigStore'
import { notifyFailure, notifySuccess } from '@/utils/helpers'
import { useRouter } from 'vue-router'

export default {
  name: 'CardProduct',
  props: {
    productProp: {
      type: Object,
      required: true
    },
    edit: { type: Boolean, default: false }
  },
  emits: ['productcreated'],
  setup(props, { emit }) {
    const { t } = useI18n()
    const store = useConfigStore()
    const { loadProductTypes, loadPublisherPresets } = store
    const product_types = computed(() => {
      return store.product_types.items
    })
    const publisher_presets = computed(() => {
      return store.publisher_presets.items
    })
    const product = ref(props.productProp)
    const preset = ref({ selected: null, name: 'Preset' })
    const required = [(v) => !!v || 'Required']
    const router = useRouter()

    const container_title = computed(() => {
      return props.edit
        ? `${t('button.edit')} product - ${product.value.title}`
        : `${t('button.create')} product`
    })

    const saveProduct = () => {
      console.debug('Creating product', product.value)

      if (props.edit) {
        updateProduct(product.value.id, product.value)
      } else {
        createProduct(product.value)
          .then((response) => {
            router.push('/product/' + response.data)
            emit('productcreated', response.data)
            notifySuccess('Product created ' + response.data)
          })
          .catch((error) => {
            console.error(error)
            notifyFailure("Couldn't create product")
          })
      }
    }

    const previewProduct = () => {
      // this.$router.push('/product/' + product.value.id)
      notifyFailure('Not implemented yet')
      console.debug('TODO: IMPLEMENT')
    }

    onMounted(() => {
      loadProductTypes()
      loadPublisherPresets()
    })

    return {
      product,
      required,
      preset,
      container_title,
      product_types,
      publisher_presets,
      saveProduct,
      previewProduct
    }
  }
}
</script>
