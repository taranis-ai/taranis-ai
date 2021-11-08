import {getProfile} from "@/api/user";
import {updateProfile} from "@/api/user";

const state = {
    hotkeys: [
        {key_code: 38, key: 'ArrowUp', alias: 'collection_up', icon: 'mdi-arrow-up-bold-box-outline'},
        {key_code: 40, key: 'ArrowDown', alias: 'collection_down', icon: 'mdi-arrow-down-bold-box-outline'},
        {key_code: 37, key: 'ArrowLeft', alias: 'close_item', icon: 'mdi-close-circle-outline'},
        {key_code: 39, key: 'ArrowRight', alias: 'show_item', icon: 'mdi-text-box'},
        {key_code: 82, key: 'r', alias: 'read_item', icon: 'mdi-eye'},
        {key_code: 73, key: 'i', alias: 'important_item', icon: 'mdi-star'},
        {key_code: 76, key: 'l', alias: 'like_item', icon: 'mdi-thumb-up'},
        {key_code: 68, key: 'd', alias: 'unlike_item', icon: 'mdi-thumb-down'},
        {key_code: 46, key: 'Delete', alias: 'delete_item', icon: 'mdi-delete'},
        {key_code: 83, key: 's', alias: 'selection', icon: 'mdi-checkbox-multiple-marked-outline'},
        {key_code: 71, key: 'g', alias: 'group', icon: 'mdi-group'},
        {key_code: 85, key: 'u', alias: 'ungroup', icon: 'mdi-ungroup'},
        {key_code: 78, key: 'n', alias: 'new_product', icon: 'mdi-file-outline'},
        {key_code: 65, key: 'a', alias: 'aggregate_open', icon: 'mdi-arrow-right-drop-circle'}
    ],
    spellcheck: true,
    dark_theme: false,
    word_lists: []
};

const actions = {

    getUserProfile(context) {

        return getProfile()
            .then(response => {
                context.commit('setUserProfile', response.data);
            })
    },

    saveUserProfile(context, data) {

        return updateProfile(data)
            .then(response => {
                context.commit('setUserProfile', response.data);
            })
    },
};

const mutations = {

    setUserProfile(state, profile) {
        state.spellcheck = profile.spellcheck
        state.dark_theme = profile.dark_theme
        state.word_lists = profile.word_lists
        for (let i = 0; i < state.hotkeys.length; i++) {
            for (let j = 0; j < profile.hotkeys.length; j++) {
                if (state.hotkeys[i].alias === profile.hotkeys[j].alias) {
                    state.hotkeys[i].key = profile.hotkeys[j].key
                    state.hotkeys[i].key_code = profile.hotkeys[j].key_code
                }
            }
        }
    }
};

const getters = {

    getProfileSpellcheck(state) {
        return state.spellcheck;
    },

    getProfileDarkTheme(state) {
        return state.dark_theme;
    },

    getProfileHotkeys(state) {
        return state.hotkeys;
    },

    getProfileWordLists(state) {
        return state.word_lists;
    }
};

export const settings = {
    state,
    actions,
    mutations,
    getters
}