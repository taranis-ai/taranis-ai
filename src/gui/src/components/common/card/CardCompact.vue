<template>
    <v-container v-bind="UI.CARD.CONTAINER">
        <v-row>
            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{hover}">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2" @click.stop="cardItemToolbar">
                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" class="status">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col :style="UI.STYLE.card_tag">
                                    <v-icon center>{{card.tag}}</v-icon>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('card_item.title')}}</div>
                                    <span>{{card.title}}</span>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('card_item.description')}}</div>
                                    <span>{{card.subtitle}}</span>
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
        name: "CardCompact",
        props: ['card', 'deletePermission'],
        mixins: [AuthMixin],
        data: () => ({
            toolbar: false
        }),
        methods: {
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
            }
        },
        mounted() {
            //window.console.debug(this.card.tag);
        }
    }
</script>