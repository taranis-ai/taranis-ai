<template>
    <div :class="UI.CLASS.multiselect">
        <v-btn v-bind="UI.TOOLBAR.BUTTON.SELECTOR" :style="multi_select ? UI.STYLE.multiselect_active : ''"
               @click.stop="multiSelect" data-btn="multi_select" :title="$t('assess.tooltip.toggle_selection')">
            <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR">{{ UI.ICON.MULTISELECT }}</v-icon>
        </v-btn>
        <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR_SEPARATOR">{{ UI.ICON.SEPARATOR }}</v-icon>
        <div v-for="btn in actions" :key="btn.action" :class="UI.CLASS.multiselect_buttons">
            <v-btn v-bind="UI.TOOLBAR.BUTTON.SELECTOR"
                   v-if="btn.can" :disabled="btn.disabled" @click.stop="action(btn.action)" :data-btn="btn.data_btn" :title="btn.title">
                <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR">{{ UI.ICON[btn.ui_icon] }}</v-icon>
            </v-btn>
        </div>
    </div>
</template>

<script>
    import AuthMixin from "../../services/auth/auth_mixin";
    import {groupAction} from "@/api/assess";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "ToolbarGroupAssess",
        components: {
        },
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
                    { can: this.canModify, disabled: !this.multi_select, action: 'GROUP', data_btn: 'group', title: this.$t('assess.tooltip.group_items'), ui_icon: 'GROUP' },
                    { can: this.canModify, disabled: !this.multi_select, action: 'UNGROUP', data_btn: 'ungroup', title: this.$t('assess.tooltip.ungroup_items'), ui_icon: 'UNGROUP' },
                    { can: this.canCreateReport, disabled: !this.multi_select, action: 'ANALYZE', data_btn: 'analyze', title: this.$t('assess.tooltip.analyze_items'), ui_icon: 'ANALYZE' },
                    { can: this.canModify, disabled: !this.multi_select, action: 'READ', data_btn: 'read', title: this.$t('assess.tooltip.read_items'), ui_icon: 'READ' },
                    { can: this.canModify, disabled: !this.multi_select, action: 'IMPORTANT', data_btn: 'important', title: this.$t('assess.tooltip.important_items'), ui_icon: 'IMPORTANT' },
                    { can: this.canModify, disabled: !this.multi_select, action: 'LIKE', data_btn: 'like', title: this.$t('assess.tooltip.like_items'), ui_icon: 'LIKE' },
                    { can: this.canModify, disabled: !this.multi_select, action: 'DISLIKE', data_btn: 'dislike', title: this.$t('assess.tooltip.dislike_items'), ui_icon: 'UNLIKE' },
                    { can: this.canDelete, disabled: !this.multi_select, action: 'DELETE', data_btn: 'delete', title: this.$t('assess.tooltip.delete_items'), ui_icon: 'DELETE' }
                ]
            }
        },
        methods: {
            getGroupId() {
                if (window.location.pathname.includes("/group/")) {
                    let i = window.location.pathname.indexOf("/group/");
                    let len = window.location.pathname.length;
                    return window.location.pathname.substring(i + 7, len);
                } else {
                    return null;
                }
            },

            multiSelect() {
                this.multi_select = !this.multi_select
                this.$store.dispatch("multiSelect", this.multi_select)
                if (this.multi_select === false) {
                    this.$root.$emit('multi-select-off');
                }
            },

            analyze() {
                let selection = this.$store.getters.getSelection
                let items = []
                for (let i = 0; i < selection.length; i++) {
                    if (selection[i].type === 'AGGREGATE') {
                        items.push(selection[i].item)
                    }
                }
                if (items.length > 0) {
                    this.multi_select = false
                    this.$store.dispatch("multiSelect", this.multi_select)
                    this.$root.$emit('multi-select-off');
                    this.$root.$emit('new-report', items);
                }
            },

            action(type) {
                if (type === 'ANALYZE') {
                    this.analyze();
                } else {
                    let selection = this.$store.getters.getSelection
                    let items = []
                    for (let i = 0; i < selection.length; i++) {
                        items.push({
                            'type': selection[i].type,
                            'id': selection[i].id
                        })
                    }
                    if (items.length > 0) {
                        groupAction({'group':this.getGroupId(), 'action': type, 'items': items}).then(() => {
                            this.multiSelect()
                            this.$root.$emit('update-news-items-list');
                        }).catch((error) => {
                            this.$root.$emit('notification',
                                {
                                    type: 'error',
                                    loc: 'error.' + error.response.data
                                }
                            )
                        });
                    }
                }
            },

            disableMultiSelect() {
                if (this.multi_select === true) {
                    this.multiSelect()
                }
            }

        },
        mounted() {
            this.$root.$on('key-multi-select', () => {
                this.multiSelect();
            });
        },
        beforeDestroy() {
            this.$root.$off('key-multi-select')
        }
    }
</script>