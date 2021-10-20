<template>
    <div class="card-item" data-type="report-item">
        <v-row>
            <v-col v-if="multiSelectActive" cols="1">
                <v-row justify="center" align="center">
                    <v-checkbox v-if="!preselected" v-model="selected" @change="selectionChanged"></v-checkbox>
                </v-row>
            </v-col>

            <v-col class="pa-0">
                <v-hover v-slot:default="{hover}" close-delay="150">
                    <v-card flat class="card mb-1" :elevation="hover ? 12 : 2"
                            @click.stop="cardItemToolbar"
                            @mouseenter.native="toolbar=true"
                            @mouseleave.native="toolbar=false"
                            :color="selectedColor"
                    >
                        <v-layout row wrap class="pa-1 pl-0 status" v-bind:class="itemStatus()">
                            <v-row justify="center">
                                <v-flex>
                                    <v-row>

                                        <!-- Icon -->
                                        <v-col class="cs-card-col-0">
                                            <div>
                                                <v-icon center class="pa-1 pt-2">{{ card.tag }}</v-icon>
                                            </div>
                                        </v-col>

                                        <!--Title-->
                                        <v-col class="cs-card-col-1">
                                            <div class="caption grey--text">{{ $t('card_item.title') }}</div>
                                            <span>{{ card.title }}</span>
                                        </v-col>

                                        <!--Date/Time-->
                                        <v-col class="cs-card-col-2">
                                            <div class="caption grey--text">{{ $t('card_item.created') }}</div>
                                            <span>{{ card.created }}</span>
                                        </v-col>

                                        <!-- Toolbar -->
                                        <v-col class="cs-card-col-3">
                                            <v-speed-dial v-if="!multiSelectActive && !publish_selector"
                                                          v-model="toolbar"
                                                          direction="left"
                                                          transition='slide-x-reverse-transition'
                                            >

                                                <v-btn v-if="canDelete" fab x-small color="red"
                                                       @click.stop="cardItemToolbar('delete')"
                                                       :title="$t('analyze.tooltip.delete_item')">
                                                    <v-icon color="white">mdi-trash-can-outline</v-icon>
                                                </v-btn>

                                                <v-btn v-if="canCreateProduct" icon
                                                       @click.stop="cardItemToolbar('new')"
                                                       :title="$t('analyze.tooltip.publish_item')">
                                                    <v-icon color="info">mdi-file-outline</v-icon>
                                                </v-btn>
                                            </v-speed-dial>

                                            <v-speed-dial class="newdialshort" v-if="publish_selector"
                                                          v-model="toolbar"
                                                          direction="left"
                                                          transition='slide-x-reverse-transition'
                                                          bottom>
                                                <v-item-group>
                                                    <v-btn v-if="canModify" icon
                                                           @click.stop="cardItemToolbar('remove')">
                                                        <v-icon color="accent">mdi-minus-circle-outline</v-icon>
                                                    </v-btn>
                                                </v-item-group>

                                            </v-speed-dial>
                                        </v-col>

                                    </v-row>
                                </v-flex>
                            </v-row>
                        </v-layout>
                    </v-card>
                </v-hover>
            </v-col>
        </v-row>
    </div>
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
        itemStatus: function () {
            if (this.card.completed) {
                return "completed"
            } else {
                return "in_progress"
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

<style>

.card .cs-card-col-0 {
    max-width: 5%;
}

.card .cs-card-col-1 {
    max-width: 60%;
}

.card .cs-card-col-2 {
    max-width: 30%;
}

.card .cs-card-col-3 {
    max-width: 5%;
}

.card .status.in_progress {
    border-left: 4px solid #ffd556;
}

.card .status.completed {
    border-left: 4px solid #33DD40;
}

.card .status.alert {
    border-left: 4px solid red;
}
</style>