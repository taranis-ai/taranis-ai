<template>
  <v-card>
    <v-toolbar density="compact">
      <v-toolbar-title>{{ container_title }}</v-toolbar-title>
      <v-spacer />
      <v-btn
        v-if="renderedProduct"
        variant="outlined"
        class="ml-3 mr-3"
        @click="downloadProduct()"
      >
        <span>{{ $t('product.download') }}</span>
      </v-btn>
      <v-btn
        v-if="edit"
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
          :cols="showPreview ? 6 : 12"
          :class="showPreview ? 'taranis-vertical-view' : ''"
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
                  :disabled="edit"
                  :rules="required"
                  required
                />
              </v-col>
              <v-col cols="6" class="pr-3">
                <v-text-field
                  v-model="product.title"
                  :label="$t('product.title')"
                  name="title"
                  :rules="required"
                  required
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
            <v-row v-if="product.product_type_id" no-gutters>
              <v-col cols="12">
                <v-data-table
                  v-model="product.report_items"
                  :headers="report_item_headers"
                  :items="reportItems"
                  show-select
                >
                  <template v-if="reportItems.length < 10" #bottom />
                </v-data-table>
              </v-col>
            </v-row>
            <v-row no-gutters>
              <v-col cols="12">
                <v-btn
                  v-if="edit && renderedProduct"
                  color="primary"
                  class="mt-3"
                  block
                  @click="publishDialog = true"
                >
                  Publish
                </v-btn>
              </v-col>
            </v-row>
          </v-form>
          <v-dialog v-model="publishDialog" width="auto">
            <popup-publish-product
              :product-id="product.id"
              :dialog="publishDialog"
              @close="publishDialog = false"
            />
          </v-dialog>
        </v-col>
        <v-col v-if="showPreview" :cols="6" class="pa-5 taranis-vertical-view">
          <div v-if="renderedProduct">
            <span v-if="render_html" v-dompurify-html="renderedProduct"></span>

            <vue-pdf-embed
              v-if="renderedProductMimeType === 'application/pdf'"
              :source="'data:application/pdf;base64,' + renderedProduct"
            />

            <pre v-if="renderedProductMimeType === 'text/plain'">
              {{ renderedProduct }}
            </pre>
          </div>
          <div v-else>
            <v-row class="justify-center mb-4">
              <h2>No rendered Product Found</h2>
            </v-row>
            <v-row class="justify-center mt-5">
              <v-btn
                variant="outlined"
                prepend-icon="mdi-eye-outline"
                @click="rerenderProduct()"
              >
                <span>{{ $t('product.render') }}</span>
              </v-btn>
            </v-row>
          </div>
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
  triggerRenderProduct
} from '@/api/publish'
import PopupPublishProduct from '../popups/PopupPublishProduct.vue'
import { useI18n } from 'vue-i18n'
import { useAnalyzeStore } from '@/stores/AnalyzeStore'
import { usePublishStore } from '@/stores/PublishStore'
import VuePdfEmbed from 'vue-pdf-embed'

import { notifyFailure, notifySuccess } from '@/utils/helpers'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'

export default {
  name: 'ProductItem',
  components: {
    VuePdfEmbed,
    PopupPublishProduct
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
    const analyzeStore = useAnalyzeStore()
    const publishStore = usePublishStore()
    const showPreview = ref(props.edit)
    const publishDialog = ref(false)
    const form = ref(null)

    const { renderedProduct, renderedProductMimeType } =
      storeToRefs(publishStore)

    const product_types = computed(() => {
      return publishStore.product_types.items
    })

    const product = ref(props.productProp)
    const preset = ref({ selected: null, name: 'Preset' })
    const required = [(v) => Boolean(v) || 'Required']
    const router = useRouter()

    const supported_report_types = computed(() => {
      const p = product_types.value.find(
        (item) => item.id === product.value.product_type_id
      )
      return p ? p.report_types : []
    })

    const reportItems = computed(() => {
      return analyzeStore.getReportItemsByIDs(supported_report_types.value)
    })
    const render_html = computed(() => {
      return (
        renderedProductMimeType.value === 'text/html' ||
        renderedProductMimeType.value === 'application/json'
      )
    })

    const report_item_headers = [
      { title: 'ID', key: 'id' },
      { title: 'Title', key: 'title' },
      { title: 'Type', key: 'type' },
      { title: 'Created', key: 'created' },
      { title: 'Completed', key: 'completed' }
    ]

    const container_title = computed(() => {
      return props.edit
        ? `${t('button.edit')} product - ${product.value.title}`
        : `${t('button.create')} product`
    })

    const saveProduct = async () => {
      const { valid } = await form.value.validate()
      if (!valid) return
      if (props.edit) {
        updateProduct(product.value)
          .then((response) => {
            console.debug('Updated product', response.data.id)
            notifySuccess('Product updated ' + response.data.id)
          })
          .catch((error) => {
            console.error(error)
            notifyFailure("Couldn't update product")
          })
      } else {
        createProduct(product.value)
          .then((response) => {
            const new_id = response.data.id
            product.value.id = new_id
            router.push('/product/' + new_id)
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
          notifySuccess('Render triggered please refresh the page')
        })
        .catch(() => {
          console.error(
            'Failed to trigger render for product ' + product.value.id
          )
        })
    }

    function getExtensionFromMimeType(mimeType) {
      const mimeToExtension = {
        'text/html': 'html',
        'application/json': 'json',
        'text/plain': 'txt',
        'application/pdf': 'pdf'
      }

      return mimeToExtension[mimeType] || null
    }

    function downloadProduct() {
      let bytes
      if (render_html.value) {
        bytes = new TextEncoder().encode(renderedProduct.value)
      } else {
        bytes = base64ToArrayBuffer(renderedProduct.value)
      }
      const blob = createBlobFromBytes(bytes, renderedProductMimeType.value)
      const extension = getExtensionFromMimeType(renderedProductMimeType.value)

      if (extension) {
        downloadBlobAsFile(blob, `${product.value.title}.${extension}`)
      }
    }

    function base64ToArrayBuffer(base64) {
      const binaryString = window.atob(base64)
      const len = binaryString.length
      const bytes = new Uint8Array(len)

      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }

      return bytes.buffer
    }

    function createBlobFromBytes(bytes, mimeType) {
      return new Blob([bytes], { type: mimeType })
    }

    function downloadBlobAsFile(blob, filename) {
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      link.download = filename
      link.click()
    }

    onMounted(() => {
      publishStore.loadProductTypes()
      analyzeStore.loadReportItems()
      analyzeStore.loadReportTypes()
      if (props.edit) {
        publishStore.loadRenderedProduct(product.value.id)
      }
    })

    return {
      form,
      product,
      required,
      preset,
      container_title,
      product_types,
      publishDialog,
      showPreview,
      reportItems,
      renderedProduct,
      report_item_headers,
      supported_report_types,
      renderedProductMimeType,
      render_html,
      saveProduct,
      downloadProduct,
      rerenderProduct
    }
  }
}
</script>
