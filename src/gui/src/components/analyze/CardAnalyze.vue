<template>
    <v-container v-bind="UI.CARD.CONTAINER" class="card-item" data-type="report-item">
        <v-row no-gutters>
            <v-col v-if="multiSelectActive" :style="UI.STYLE.card_selector_zone">
                <v-row justify="center" align="center">
                    <v-checkbox v-if="!preselected" v-model="selected" @change="selectionChanged"></v-checkbox>
                </v-row>
            </v-col>

            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{hover}">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2"
                            @click.stop="cardItemToolbar"
                            :color="selectedColor">

                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" :class="'status ' + itemStatus">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col :style="UI.STYLE.card_tag">
                                    <v-icon center>{{ card.tag }}</v-icon>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('card_item.title')}}</div>
                                    <span>{{card.title}}</span>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ $t('card_item.created') }}</div>
                                    <span>{{ card.created }}</span>
                                </v-col>
                                <v-col :style="UI.STYLE.card_hover_toolbar">
                                    <!--HOVER TOOLBAR-->
                                    <div v-if="hover">
                                        <v-row v-if="!multiSelectActive && !publish_selector"
                                               v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                            <v-col v-bind="UI.CARD.COL.TOOLS">
                                                <v-btn v-if="canDelete" icon class="red"
                                                       @click.stop="cardItemToolbar('delete')"
                                                       :title="$t('analyze.tooltip.delete_item')">
                                                    <v-icon color="white">mdi-trash-can-outline</v-icon>
                                                </v-btn>
                                                <v-btn v-if="canCreateProduct" icon
                                                       @click.stop="cardItemToolbar('new')"
                                                       :title="$t('analyze.tooltip.publish_item')">
                                                    <v-icon color="info">mdi-file-outline</v-icon>
                                                </v-btn>
                                            </v-col>
                                        </v-row>
                                        <v-row v-if="publish_selector"
                                               v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                            <v-col v-bind="UI.CARD.COL.TOOLS">
                                                <v-btn v-if="canModify" icon
                                                       @click.stop="cardItemToolbar('remove')">
                                                    <v-icon color="accent">mdi-minus-circle-outline</v-icon>
                                                </v-btn>
                                            </v-col>
                                        </v-row>
                                    </div>
                                </v-col>
                            </v-row>
                        </v-layout>
                    </v-card>
                </v-hover>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
import Permissions from "@/services/auth/permissions";
import AuthMixin from "@/services/auth/auth_mixin";

export default {
    name: "CardAnalyze",
    props: {
        card: Object,
        publish_selector: Boolean,
        preselected: Boolean,
    },
    mixins: [AuthMixin],
    data: () => ({
        toolbar: false,
        selected: false,
        status: "in_progress"
    }),
    computed: {

        canModify() {
            return this.checkPermission(Permissions.ANALYZE_UPDATE) && (this.card.modify === true || this.card.remote_user !== null)
        },

        canDelete() {
            return this.checkPermission(Permissions.ANALYZE_DELETE) && (this.card.modify === true || this.card.remote_user !== null)
        },

        canCreateProduct() {
            return this.checkPermission(Permissions.PUBLISH_CREATE) && !window.location.pathname.includes('/group/')
        },

        multiSelectActive() {
            return this.$store.getters.getMultiSelectReport
        },

        selectedColor() {
            if (this.selected === true || this.preselected) {
                return "orange lighten-4"
            } else {
                return ""
            }
        },
        itemStatus() {
            if (this.card.completed) {
                return "completed"
            } else {
                return "in_progress"
            }
        }
    },
    methods: {

        selectionChanged() {
            if (this.selected === true) {
                this.$store.dispatch("selectReport", {'id': this.card.id, 'item': this.card})
            } else {
                this.$store.dispatch("deselectReport", {'id': this.card.id, 'item': this.card})
            }
        },

        itemClicked(data) {
            if (this.checkPermission(Permissions.ANALYZE_ACCESS) && (this.card.access === true || data.remote_user !== null)) {
                if (data.remote_user === null) {
                    this.$emit('show-report-item-detail', data);
                } else {
                    this.$emit('show-remote-report-item-detail', data);
                }
            }
        },
        deleteClicked(data) {
            this.$root.$emit('delete-report-item', data)
        },
        cardItemToolbar(action) {
            switch (action) {
                case "delete":
                    this.deleteClicked(this.card);
                    break;

                case "new":
                    this.$root.$emit('new-product', [this.card]);
                    break;

                case "remove":
                    this.$emit('remove-report-item-from-selector', this.card);
                    break;

                default:
                    this.toolbar = false;
                    this.itemClicked(this.card);
                    break;
            }
        },

        multiSelectOff() {
            this.selected = false
        }
    },
    mounted() {
        this.$root.$on('multi-select-off', this.multiSelectOff);
    },
    beforeDestroy() {
        this.$root.$off('multi-select-off', this.multiSelectOff);
    }
}
</script>