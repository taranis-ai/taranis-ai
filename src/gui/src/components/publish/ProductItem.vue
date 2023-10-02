<template>
  <v-card>
    <v-toolbar density="compact">
      <v-toolbar-title>{{ container_title }}</v-toolbar-title>
      <v-spacer />
      <v-switch
        v-model="verticalView"
        style="max-width: 150px"
        :label="$t('product.preview')"
        hide-details
        color="success"
        density="compact"
      />
      <v-btn
        variant="outlined"
        prepend-icon="mdi-eye-outline"
        @click="rerenderProduct()"
      >
        <span>{{ $t('product.render') }}</span>
      </v-btn>
      <v-btn
        prepend-icon="mdi-content-save"
        color="success"
        class="ml-3"
        variant="flat"
        @click="saveProduct"
      >
        <span v-if="edit">
          {{ $t('button.save') }}
        </span>
        <span v-else>
          {{ $t('button.create') }}
        </span>
      </v-btn>
    </v-toolbar>
    <v-card-text>
      <v-row no-gutters>
        <v-col
          :cols="verticalView ? 6 : 12"
          :class="verticalView ? 'taranis-ng-vertical-view' : ''"
        >
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
            <v-row no-gutters>
              <v-col cols="12">
                <v-autocomplete
                  v-model="product.report_items"
                  :items="reportItems"
                  :label="$t('nav_menu.report_items')"
                  multiple
                />
              </v-col>
            </v-row>
          </v-form>
        </v-col>
        <v-col
          v-if="verticalView"
          :cols="6"
          class="pa-5 taranis-ng-vertical-view"
        >
          <span v-if="render_direct" v-dompurify-html="renderedProduct"></span>

          <vue-pdf-embed
            v-else
            :source="'data:application/pdf;base64,' + renderedProduct"
          />
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import {
  createProduct,
  updateProduct,
  getRenderdProduct,
  triggerRenderProduct
} from '@/api/publish'
import { useI18n } from 'vue-i18n'
import { useConfigStore } from '@/stores/ConfigStore'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import VuePdfEmbed from 'vue-pdf-embed'

import { notifyFailure, notifySuccess } from '@/utils/helpers'
import { useRouter } from 'vue-router'

export default {
  name: 'ProductItem',
  components: {
    VuePdfEmbed
  },
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
    const configStore = useConfigStore()
    const analyzeStore = useAnalyzeStore()
    const verticalView = ref(props.edit)

    const reportItems = computed(() => analyzeStore.getReportItemsList)
    const renderedProduct = ref(null)
    const renderedProductMimeType = ref(null)

    const product_types = computed(() => {
      return configStore.product_types.items
    })
    const publisher_presets = computed(() => {
      return configStore.publisher_presets.items
    })
    const product = ref(props.productProp)
    const preset = ref({ selected: null, name: 'Preset' })
    const required = [(v) => !!v || 'Required']
    const router = useRouter()

    const render_direct = computed(() => {
      return (
        renderedProductMimeType.value === 'text/html' ||
        renderedProductMimeType.value === 'application/json' ||
        renderedProductMimeType.value === 'text/plain'
      )
    })

    const container_title = computed(() => {
      return props.edit
        ? `${t('button.edit')} product - ${product.value.title}`
        : `${t('button.create')} product`
    })

    const saveProduct = () => {
      if (props.edit) {
        updateProduct(product.value)
      } else {
        createProduct(product.value)
          .then((response) => {
            const new_id = response.data.id
            router.push('/product/' + new_id)
            console.debug('Created product', new_id)
            emit('productcreated', new_id)
            notifySuccess('Product created ' + new_id)
          })
          .catch((error) => {
            console.error(error)
            notifyFailure("Couldn't create product")
          })
      }
    }

    function rerenderProduct() {
      triggerRenderProduct(product.value.id)
        .then(() => {
          console.debug('Triggered render for product ' + product.value.id)
        })
        .catch(() => {
          console.error(
            'Failed to trigger render for product ' + product.value.id
          )
        })
    }

    function renderProduct() {
      getRenderdProduct(product.value.id)
        .then((blob) => {
          renderedProduct.value = blob.data
          renderedProductMimeType.value = blob.headers['content-type']
        })
        .catch(() => {
          console.error('Failed to render product ' + product.value.id)
        })
    }

    onMounted(() => {
      configStore.loadProductTypes()
      configStore.loadPublisherPresets()
      analyzeStore.loadReportItems()
      renderProduct()
    })

    return {
      product,
      required,
      preset,
      container_title,
      product_types,
      publisher_presets,
      verticalView,
      reportItems,
      renderedProduct,
      render_direct,
      saveProduct,
      renderProduct,
      rerenderProduct
    }
  }
}
</script>
