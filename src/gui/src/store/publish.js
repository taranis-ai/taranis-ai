import { getAllProducts } from '@/api/publish'
import { getAllUserPublishersPresets } from '@/api/user'
import { filter } from '@/store/filter'

const state = {
  products: { total_count: 0, items: [] },
  products_publisher_presets: { total_count: 0, items: [] }
}

const actions = {
  loadProducts(context, data) {
    return getAllProducts(data).then((response) => {
      context.commit('setProducts', response.data)
    })
  },

  updateProducts(context) {
    return getAllProducts(filter.state.productFilter).then((response) => {
      context.commit('setProducts', response.data)
    })
  },

  loadUserPublishersPresets(context, data) {
    return getAllUserPublishersPresets(data).then((response) => {
      context.commit('setProductsPublisherPresets', response.data)
    })
  }
}

const mutations = {
  setProducts(state, new_product) {
    state.products = new_product
  },

  setProductsPublisherPresets(state, new_publisher_presets) {
    state.products_publisher_presets = new_publisher_presets
  }
}

const getters = {
  getProducts(state) {
    return state.products.items
  },

  getProductsPublisherPresets(state) {
    return state.products_publisher_presets
  },

  getPreviewLink(state, product) {
    return (
      this.$store.getters.getCoreAPIURL +
      '/publish/products/' +
      product +
      '/overview?jwt=' +
      this.$store.getters.getJWT
    )
  }
}

export const publish = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}
