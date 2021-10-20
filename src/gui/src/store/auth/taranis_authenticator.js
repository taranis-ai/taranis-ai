import {authenticate, refresh} from "@/api/auth";
import ApiService from "@/services/api_service";

const state = {
    jwt: ''
};

const actions = {

    login(context, userData) {

        return authenticate(userData)
            .then(response => {
                context.commit('setJwtToken', response.data.access_token);
                context.dispatch('setUser', context.getters.getUserData);
            })
            .catch(() => {
                context.commit('clearJwtToken')
            })
    },

    refresh(context) {

        return refresh()
            .then(response => {
                context.commit('setJwtToken', response.data.access_token);
                context.dispatch('setUser', context.getters.getUserData)
            })
            .catch(() => {
                context.commit('clearJwtToken')
            })
    },

    setToken(context, access_token) {

        context.commit('setJwtToken', access_token);
        context.dispatch('setUser', context.getters.getUserData);
    }
};

const mutations = {

    setJwtToken(state, access_token) {
        localStorage.ACCESS_TOKEN = access_token;
        ApiService.setHeader();
        state.jwt = access_token;
    },
    clearJwtToken(state) {
        localStorage.ACCESS_TOKEN = '';
        state.jwt = ''
    }
};

const getters = {

    getUserData(state) {
        const data = JSON.parse(atob(state.jwt.split('.')[1]));
        return data.user_claims
    },

    getSubjectName(state) {
        const data = JSON.parse(atob(state.jwt.split('.')[1]));
        return data.sub
    },

    hasExternalLoginUrl() {
        if (typeof (process.env) == "undefined")
            return (("$VUE_APP_TARANIS_NG_LOGIN_URL" != "") && ("$VUE_APP_TARANIS_NG_LOGIN_URL"[0] != "$"));

        return process.env.VUE_APP_TARANIS_NG_LOGIN_URL != null;
    },

    getLoginURL() {
        if (typeof (process.env) == "undefined") {
            if (("$VUE_APP_TARANIS_NG_LOGIN_URL" != "") && ("$VUE_APP_TARANIS_NG_LOGIN_URL"[0] != "$"))
                return "$VUE_APP_TARANIS_NG_LOGIN_URL";
        } else {
            if (process.env.VUE_APP_TARANIS_NG_LOGIN_URL != null)
                return process.env.VUE_APP_TARANIS_NG_LOGIN_URL;
        }
        return "/login";
    },

    hasExternalLogoutUrl() {
        if (typeof (process.env) == "undefined")
            return (("$VUE_APP_TARANIS_NG_LOGOUT_URL" != "") && ("$VUE_APP_TARANIS_NG_LOGOUT_URL"[0] != "$"));

        return process.env.VUE_APP_TARANIS_NG_LOGOUT_URL != null
    },

    getLogoutURL() {
        if (typeof (process.env) == "undefined") {
            if (("$VUE_APP_TARANIS_NG_LOGOUT_URL" != "") && ("$VUE_APP_TARANIS_NG_LOGOUT_URL"[0] != "$"))
                return "$VUE_APP_TARANIS_NG_LOGOUT_URL";
        } else {
            if (process.env.VUE_APP_TARANIS_NG_LOGOUT_URL != null)
                return process.env.VUE_APP_TARANIS_NG_LOGOUT_URL;
        }
        return "/logout"
    },

    getJWT() {
        return state.jwt
    }
};

export const taranis_authenticator = {
    state,
    actions,
    mutations,
    getters
};
