<template>
    <div class="multiselect">
        <v-row class="ml-5 mt-0 mb-2">
            <v-btn :class="multi_select === true ? 'multi-select-button-pressed' : ''" small icon @click.stop="multiSelect" data-btn="multi_select" :title="$t('assess.tooltip.toggle_selection')">
                <v-icon small color="white">mdi-checkbox-multiple-marked-outline</v-icon>
            </v-btn>
            <v-icon center color="grey lighten-2" class="ma-0 pa-0 pt-1">mdi-drag-vertical</v-icon>
            <v-btn v-if="canModify" small icon :disabled="!multi_select" @click.stop="action('GROUP')" data-btn="group" :title="$t('assess.tooltip.group_items')">
                <v-icon small color="white">mdi-group</v-icon>
            </v-btn>
            <v-btn v-if="canModify" class="ml-1" small icon :disabled="!multi_select" @click.stop="action('UNGROUP')" data-btn="ungroup" :title="$t('assess.tooltip.ungroup_items')">
                <v-icon small color="white">mdi-ungroup</v-icon>
            </v-btn>
            <v-btn v-if="canCreateReport" class="ml-1" small icon :disabled="!multi_select" @click.stop="analyze" data-btn="analyze" :title="$t('assess.tooltip.analyze_items')">
                <v-icon small color="white">mdi-file-outline</v-icon>
            </v-btn>
            <v-btn v-if="canModify" class="ml-1" small icon :disabled="!multi_select" @click.stop="action('READ')" data-btn="read" :title="$t('assess.tooltip.read_items')">
                <v-icon small color="white">mdi-eye</v-icon>
            </v-btn>
            <v-btn v-if="canModify" class="ml-1" small icon :disabled="!multi_select" @click.stop="action('IMPORTANT')" data-btn="important" :title="$t('assess.tooltip.important_items')">
                <v-icon small color="white">mdi-star</v-icon>
            </v-btn>
            <v-btn v-if="canModify" class="ml-1" small icon :disabled="!multi_select" @click.stop="action('LIKE')" data-btn="like" :title="$t('assess.tooltip.like_items')">
                <v-icon small color="white">mdi-thumb-up</v-icon>
            </v-btn>
            <v-btn v-if="canModify" class="ml-1" small icon :disabled="!multi_select" @click.stop="action('DISLIKE')" data-btn="dislike" :title="$t('assess.tooltip.dislike_items')">
                <v-icon small color="white">mdi-thumb-down</v-icon>
            </v-btn>
            <v-btn v-if="canDelete" class="ml-1" small icon :disabled="!multi_select" @click.stop="action('DELETE')" data-btn="delete" :title="$t('assess.tooltip.delete_items')">
                <v-icon small color="white">mdi-delete</v-icon>
            </v-btn>
        </v-row>
    </div>
</template>

<script>
    import AuthMixin from "../../services/auth/auth_mixin";
    import {groupAction} from "@/api/assess";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "ToolbarGroupAssess",
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

<style>

    .view .view-panel button.multi-select-button-pressed {
        background-color: orange !important;
    }

</style>