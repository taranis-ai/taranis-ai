<template>
    <div :class="UI.CLASS.multiselect">
        <v-btn v-bind="UI.TOOLBAR.BUTTON.SELECTOR" :style="multi_select ? UI.STYLE.multiselect_active : ''"
               @click.stop="multiSelect" data-btn="multi_select" :title="$t('assess.tooltip.toggle_selection')">
            <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR">{{ UI.ICON.MULTISELECT }}</v-icon>
        </v-btn>
        <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR_SEPARATOR">{{ UI.ICON.SEPARATOR }}</v-icon>
        <div v-for="btn in actions" :key="btn.action" :class="UI.CLASS.multiselect_buttons">
            <v-btn v-bind="UI.TOOLBAR.BUTTON.SELECTOR"
                   v-if="btn.can" :disabled="btn.disabled" @click.stop="action(btn.action)" :data-btn="btn.like" :title="btn.title">
                <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR">{{ UI.ICON[btn.ui_icon] }}</v-icon>
            </v-btn>
        </div>
    </div>
</template>

<script>
import AuthMixin from "../../services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";

export default {
    name: "ToolbarGroupOSINTSource",
    data: () => ({
        multi_select: false
    }),
    mixins: [AuthMixin],
    computed: {
        canModify() {
            return this.checkPermission(Permissions.ASSESS_UPDATE)
        },

        canDelete() {
            return this.checkPermission(Permissions.ASSESS_DELETE)
        },

        canCreateReport() {
            return this.checkPermission(Permissions.ANALYZE_CREATE)
        },

        actions() {
            return [
                { can: true, disabled: !this.multi_select, action: 'SELECT_ALL', data_btn: 'select_all', title: this.$t('osint_source.tooltip.select_all'), ui_icon: 'SELECT_ALL' },
                { can: true, disabled: !this.multi_select, action: 'UNSELECT_ALL', data_btn: 'unselect_all', title: this.$t('osint_source.tooltip.unselect_all'), ui_icon: 'UNSELECT_ALL' },
            ]
        }
    },
    methods: {

        multiSelect() {
            this.multi_select = !this.multi_select
            this.$store.dispatch('multiSelectOSINTSource', this.multi_select);
        },

        action(type) {
            if(type === 'SELECT_ALL') {
                this.$root.$emit('uncheck-osint-source-card');
                setTimeout(() => {
                    this.$root.$emit('check-osint-source-card');
                }, 50);
            } else if(type === 'UNSELECT_ALL') {
                this.$root.$emit('uncheck-osint-source-card');
            }
        },

        disableMultiSelect() {
            if (this.multi_select === true) {
                this.multiSelect()
            }
        }

    }
}
</script>