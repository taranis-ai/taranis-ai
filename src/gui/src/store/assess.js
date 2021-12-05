import {getManualOSINTSources, getNewsItemsByGroup} from "@/api/assess";

const state = {
    newsitems: {total_count: 0, items: []},
    multi_select: false,
    selection: [],
    current_group_id: "",
    manual_osint_sources: [],
    filter: {},
};

const actions = {

    getNewsItemsByGroup(context, data) {

        return getNewsItemsByGroup(data.group_id, data.data)
            .then(response => {
                context.commit('setNewsItems', response.data);
            })
    },

    multiSelect(context, data) {
        context.commit('setMultiSelect', data);
    },

    select(context, data) {
        context.commit('addSelection', data);
    },

    deselect(context, data) {
        context.commit('removeSelection', data);
    },

    changeCurrentGroup(context, data) {
        context.commit('setCurrentGroup', data);
    },

    getManualOSINTSources(context) {

        return getManualOSINTSources()
            .then(response => {
                context.commit('setManualOSINTSources', response.data);
            })
    },

    filter(context, data) {
        context.commit('setFilter', data);
    },
};

const mutations = {

    setNewsItems(state, news_items) {
        state.newsitems = news_items
    },

    setMultiSelect(state, enable) {
        state.multi_select = enable
        state.selection = []
    },

    addSelection(state, selected_item) {
        state.selection.push(selected_item)
    },

    removeSelection(state, selectedItem) {
        for (let i = 0; i < state.selection.length; i++) {
            if (state.selection[i].type === selectedItem.type && state.selection[i].id === selectedItem.id) {
                state.selection.splice(i, 1);
                break
            }
        }
    },

    setCurrentGroup(state, group_id) {
        state.current_group_id = group_id
    },

    setManualOSINTSources(state, new_manual_osint_sources) {
        state.manual_osint_sources = new_manual_osint_sources
    },

    setFilter(state, data) {
        state.filter = data
    },
};

const getters = {

    getNewsItems(state) {
        return state.newsitems
    },

    getMultiSelect(state) {
        return state.multi_select
    },

    getSelection(state) {
        return state.selection
    },

    getCurrentGroup(state) {
        return state.current_group_id
    },

    getManualOSINTSources(state) {
        return state.manual_osint_sources
    },

    getFilter(state) {
        return state.filter
    },
};

export const assess = {
    state,
    actions,
    mutations,
    getters
};