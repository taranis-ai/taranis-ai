import {store} from '@/store/store'

const AuthService = {

    isAuthenticated() {
        return store.getters.isAuthenticated
    },

    hasPermission(permission) {

        return store.getters.getPermissions.includes(permission)
    },

    hasAnyPermission(permissions) {

        for (let i = 0; i < permissions.length; i++) {
            if (AuthService.hasPermission(permissions[i])) {
                return true;
            }
        }

        return false;
    },
};

export default AuthService