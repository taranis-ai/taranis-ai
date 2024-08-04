import { apiService } from '@/main'

export function getAllProducts(filter = '') {
  return apiService.get(`/publish/products?${filter}`)
}

export function createProduct(data) {
  return apiService.post('/publish/products', data)
}

export function updateProduct(data) {
  return apiService.put(`/publish/products/${data.id}`, data)
}

export function getProduct(product) {
  return apiService.get(`/publish/products/${product}`)
}

export function getRenderdProduct(product) {
  return apiService.get(`/publish/products/${product}/render`)
}

export function triggerRenderProduct(product) {
  return apiService.post(`/publish/products/${product}/render`)
}

export function deleteProduct(product_id) {
  return apiService.delete(`/publish/products/${product_id}`)
}

export function getAllProductTypes() {
  return apiService.get('/publish/product-types')
}

export function publishProduct(product_id, publisher_id) {
  return apiService.post(
    `/publish/products/${product_id}/publishers/${publisher_id}`,
    {}
  )
}
