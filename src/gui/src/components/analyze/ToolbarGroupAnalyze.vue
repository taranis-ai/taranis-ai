<template>
    <div class="multiselect">
        <v-row class="ml-5 mt-0 mb-2">
            <v-btn :class="multi_select === true ? 'multi-select-button-pressed' : ''" small icon
                   @click.stop="multiSelect" data-btn="multi_select" :title="$t('analyze.tooltip.toggle_selection')">
                <v-icon small color="white">mdi-checkbox-multiple-marked-outline</v-icon>
            </v-btn>
            <v-icon center color="grey lighten-2" class="ma-0 pa-0 pt-1">mdi-drag-vertical</v-icon>
            <v-btn v-if="canCreateProduct" class="ml-1" small icon :disabled="!multi_select" @click.stop="analyze"
                   data-btn="analyze" :title="$t('analyze.tooltip.publish_items')">
                <v-icon small color="white">mdi-file-outline</v-icon>
            </v-btn>
            <v-btn v-if="canDelete" class="ml-1" small icon :disabled="!multi_select" @click.stop="action('DELETE')"
                   data-btn="delete" :title="$t('analyze.tooltip.delete_items')">
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
    name: "ToolbarGroupAnalyze",
    data: () => ({
        multi_select: false
    }),
    mixins: [AuthMixin],
    computed: {
        canDelete() {
            return this.checkPermission(Permissions.ANALYZE_DELETE)
        },

        canCreateProduct() {
            return this.checkPermission(Permissions.PUBLISH_CREATE)
        }
    },
    methods: {
        multiSelect() {
            this.multi_select = !this.multi_select
            this.$store.dispatch("multiSelectReport", this.multi_select)
            if (this.multi_select === false) {
                this.$root.$emit('multi-select-off');
            }
        },

        analyze() {
            let selection = this.$store.getters.getSelectionReport
            let items = []
            for (let i = 0; i < selection.length; i++) {
                items.push(selection[i].item)
            }
            if (items.length > 0) {
                this.multi_select = false
                this.$store.dispatch("multiSelectReport", this.multi_select)
                this.$root.$emit('multi-select-off');
                this.$root.$emit('new-product', items);
            }
        },

        action(type) {
            let selection = this.$store.getters.getSelectionReport
            let items = []
            for (let i = 0; i < selection.length; i++) {
                items.push({
                    'id': selection[i].id
                })
            }
            if (items.length > 0) {
                groupAction({'group': this.getGroupId(), 'action': type, 'items': items}).then(() => {
                    this.multiSelect()
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