import {store} from '@/store/store'
import {Base64} from "js-base64";


const AuthService = {

    isAuthenticated() {
        let jwt = store.getters.getJWT
        if (!jwt || jwt.split('.').length < 3) {
            return false
        }
        const data = JSON.parse(Base64.decode(jwt.split('.')[1]));
        const exp = new Date(data.exp * 1000);
        const now = new Date();
        return now < exp
    },

    needTokenRefresh() {
        let jwt = store.getters.getJWT
        if (!jwt || jwt.split('.').length < 3) {
            return false
        }
        const data = JSON.parse(Base64.decode(jwt.split('.')[1]));
        const exp = new Date((data.exp - 300) * 1000);
        const now = new Date();
        return now > exp
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