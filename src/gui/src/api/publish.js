import { getApiService } from '@/services/api_service'

export function getAllProducts(filter = '') {
  return getApiService().get(`/publish/products?${filter}`)
}

export function createProduct(data) {
  return getApiService().post('/publish/products', data)
}

export function updateProduct(data) {
  return getApiService().put(`/publish/products/${data.id}`, data)
}

export function getProduct(product) {
  return getApiService().get(`/publish/products/${product}`)
}

export function getRenderdProduct(product) {
  return getApiService().get(`/publish/products/${product}/render`)
}

export function triggerRenderProduct(product) {
  return getApiService().post(`/publish/products/${product}/render`)
}

export function deleteProduct(product_id) {
  return getApiService().delete(`/publish/products/${product_id}`)
}

export function getAllProductTypes() {
  return getApiService().get('/publish/product-types')
}

export function publishProduct(product_id, publisher_id) {
  return getApiService().post(
    `/publish/products/${product_id}/publishers/${publisher_id}`,
    {}
  )
}
