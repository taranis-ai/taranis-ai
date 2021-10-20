import AuthService from "@/services/auth/auth_service";
import Permissions from "@/services/auth/permissions";

var AuthMixin = {

    data: () => ({
        permissions: Permissions
    }),

    methods: {
        isAuthenticated() {
            return AuthService.isAuthenticated()
        },
        needTokenRefresh() {
            return AuthService.needTokenRefresh()
        },
        checkPermission(permission) {
            return AuthService.hasPermission(permission)
        }
    }
};

export default AuthMixin
