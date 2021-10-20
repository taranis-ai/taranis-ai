import ApiService from "@/services/api_service";

export function authenticate(userData) {
    return ApiService.post(`/auth/login`, userData)
}

export function refresh() {
    return ApiService.get(`/auth/refresh`)
}