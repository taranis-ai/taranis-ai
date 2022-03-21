import ApiService from '@/services/api_service'

export function getAllProducts (filter_data) {
  const filter = `?search=${encodeURIComponent(filter_data.filter.search)}` +
    `&range=${encodeURIComponent(filter_data.filter.range)}` +
    `&sort=${encodeURIComponent(filter_data.filter.sort)}` +
    `&offset=${encodeURIComponent(filter_data.offset)}` +
    `&limit=${encodeURIComponent(filter_data.limit)}`

  return ApiService.get(`/publish/products${filter}`)
}

export function createProduct (data) {
  return ApiService.post('/publish/products', data)
}

export function updateProduct (data) {
  return ApiService.put(`/publish/products/${data.id}`, data)
}

export function deleteProduct (product) {
  return ApiService.delete(`/publish/products/${product.id}`)
}

export function publishProduct (product_id, publisher_id) {
  return ApiService.post(`/publish/products/${product_id}/publishers/${publisher_id}`, {})
}
