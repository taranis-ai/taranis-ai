
const state = {
    multi_select_osint_source: false,
    selection: []
};

const actions = {
    multiSelectOSINTSource(context, data) {
        context.commit('setMultiSelect', data);
    },

    selectOSINTSource(context, data) {
        context.commit('addSelection', data);
    },

    deselectOSINTSource(context, data) {
        context.commit('removeSelection', data);
    }
};

const mutations = {
    setMultiSelect(state, enable) {
        state.multi_select_osint_source = enable;
        state.selection = [];
        state.select_all = false;
    },

    addSelection(state, selected_item) {
        state.selection.push(selected_item);
    },

    removeSelection(state, selectedItem) {
        for (let i = 0; i < state.selection.length; i++) {
            if (state.selection[i].type === selectedItem.type && state.selection[i].id === selectedItem.id) {
                state.selection.splice(i, 1);
                break;
            }
        }
    }
};

const getters = {
    getOSINTSourcesItem(state) {
        return state.newsitems;
    },

    getOSINTSourcesMultiSelect(state) {
        return state.multi_select_osint_source;
    },

    getOSINTSourcesSelection(state) {
        return state.selection;
    }
}

export const osint_source = {
    state,
    actions,
    mutations,
    getters
}