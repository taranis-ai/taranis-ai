import Vue from 'vue'
import Vuex from 'vuex'

import {authenticator} from "@/store/authenticator"
import {assess} from "@/store/assess";
import {config} from "@/store/config";
import {analyze} from "@/store/analyze";
import {publish} from "@/store/publish"
import {settings} from "@/store/settings";
import {assets} from "@/store/assets";
import {dashboard} from "@/store/dashboard";
import {osint_source} from "@/store/osint_source";

Vue.use(Vuex);

const state = {
    user: {
        id: '',
        name: '',
        organization_name: '',
        permissions: []
    }
};

const actions = {

    setUser(context, userData) {
        context.commit("setUser", userData)
    },

    logout(context) {
        context.commit('clearJwtToken')
    }
};

const mutations = {

    setUser(state, userData) {
        state.user = userData
    }
};

const getters = {

    getUserId(state) {
        return state.user.id;
    },

    getUserName(state) {
        return state.user.name;
    },

    getOrganizationName(state) {
        return state.user.organization_name;
    },

    getPermissions(state) {
        return state.user.permissions;
    }
};

export const store = new Vuex.Store({
    state,
    actions,
    mutations,
    getters,
    modules: {
        authenticator,
        assess,
        config,
        analyze,
        publish,
        settings,
        assets,
        dashboard,
        osint_source
    }
});