<template>
    <v-container v-bind="UI.CARD.CONTAINER">
        <v-row no-gutters>
            <v-col v-if="multiSelect" :style="UI.STYLE.card_selector_zone">
                <v-row justify="center" align="center">
                    <v-checkbox v-model="selected" @change="selectionChanged"/>
                </v-row>
            </v-col>
            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{hover}">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2"
                            @click.stop="cardItemToolbar" :color="selected && multiSelect ? 'green lighten-4' : ''"
                    >
                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" :class="'status ' + cardStatus">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col :style="UI.STYLE.card_tag">
                                    <v-icon center>{{card.tag}}</v-icon>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('card_item.title')}}</div>
                                    <div>{{card.name}}</div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('card_item.description')}}</div>
                                    <div>{{card.description}}</div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('osint_source.type')}}</div>
                                    <div>{{card.collector.type}}</div>
                                </v-col>

                                <!--HOVER TOOLBAR-->
                                <v-col :style="UI.STYLE.card_hover_toolbar">
                                    <v-row v-if="hover" v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                        <v-col v-bind="UI.CARD.COL.TOOLS">
                                            <v-btn v-if="checkPermission(deletePermission)" icon class="red" @click.stop="cardItemToolbar('delete')">
                                                <v-icon color="white">{{ UI.ICON.DELETE }}</v-icon>
                                            </v-btn>
                                        </v-col>
                                    </v-row>
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

    import AuthMixin from "@/services/auth/auth_mixin";

    export default {
        name: "CardSource",
        props: ['card', 'deletePermission'],
        data:() => ({
            toolbar: false,
            selected: false
        }),
        mixins: [AuthMixin],
        computed: {
            cardStatus() {
                if (this.card.status === undefined) {
                    return "status-green"
                } else {
                    return "status-" + this.card.status
                }
            },
            multiSelect() {
                return this.$store.getters.getOSINTSourcesMultiSelect;
            }
        },
        methods: {
            selectionChanged() {
                if(this.selected) {
                    this.$store.dispatch('selectOSINTSource', this.card.id);
                } else {
                    this.$store.dispatch('deselectOSINTSource', this.card.id);
                }
            },

            itemClicked(data) {
                this.$root.$emit('show-edit', data)
            },
            deleteClicked(data) {
                this.$root.$emit('delete-item', data)
            },
            cardItemToolbar(action) {
                switch (action) {
                    case "delete":
                        this.deleteClicked(this.card)
                        break;

                    default:
                        this.toolbar = false;
                        this.itemClicked(this.card);
                        break;
                }
            },

        },
        mounted() {
            this.$root.$on('check-osint-source-card', () => {
                this.selected = true;
                this.$store.commit('addSelection', this.card.id);
            });
            this.$root.$on('uncheck-osint-source-card', () => {
                this.selected = false;
                this.$store.dispatch('deselect', this.card.id);
            });
        },
        beforeDestroy() {
            this.$root.$off('check-osint-source-card');
            this.$root.$off('uncheck-osint-source-card');
        }
    }
</script>