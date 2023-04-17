import ApiService from '@/services/api_service'

export function getAllProducts(filter_data) {
  const filter = ApiService.getQueryStringFromNestedObject(filter_data)
  return ApiService.get(`/publish/products?${filter}`)
}

export function createProduct(data) {
  return ApiService.post('/publish/products', data)
}

export function updateProduct(data) {
  return ApiService.put(`/publish/products/${data.id}`, data)
}

export function getProduct(product) {
  return ApiService.get(`/publish/products/${product.id}`)
}

export function deleteProduct(product) {
  return ApiService.delete(`/publish/products/${product.id}`)
}

export function publishProduct(product_id, publisher_id) {
  return ApiService.post(
    `/publish/products/${product_id}/publishers/${publisher_id}`,
    {}
  )
}
