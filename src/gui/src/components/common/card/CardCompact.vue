<template>
    <v-hover v-slot:default="{hover}" close-delay="150">
        <v-card flat class="card mb-1" :elevation="hover ? 12 : 2"
                @click.stop="cardItemToolbar"
                @mouseenter.native="toolbar=true"
                @mouseleave.native="toolbar=false"
        >
            <v-layout row wrap class="pa-1 pl-0 status">
                <v-row justify="center">
                    <v-flex>
                        <v-row>
                            <v-col class="cs-card-col-0">
                                <div class="caption grey--text">&nbsp;</div>
                                <div>
                                    <v-icon center class="pt-2">{{card.tag}}</v-icon>
                                </div>
                            </v-col>
                            <v-col class="cs-card-col-1">
                                <div class="caption grey--text">{{$t('card_item.title')}}</div>
                                <span>{{card.title}}</span>
                            </v-col>
                            <v-col class="cs-card-col-2">
                                <div class="caption grey--text ">{{$t('card_item.description')}}</div>
                                <span class="font-weight-light caption">{{card.subtitle}}</span>
                            </v-col>
                            <v-col class="cs-card-col-3">
                                <v-speed-dial
                                        v-model="toolbar"
                                        direction="left"
                                        transition='slide-x-reverse-transition'
                                >

                                    <v-btn v-if="checkPermission(deletePermission)" fab x-small color="red" @click.stop="cardItemToolbar('delete')">
                                        <v-icon color="white">mdi-trash-can-outline</v-icon>
                                    </v-btn>
                                </v-speed-dial>
                            </v-col>
                        </v-row>
                    </v-flex>
                </v-row>
            </v-layout>
        </v-card>
    </v-hover>
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
            window.console.debug(this.card.tag);
        }
    }
</script>

<style>
    .card .status {
        border-left: 4px solid #33DD40;
    }
    .card .obj.center {
        text-align: center;
    }
    .card.elevation-12 {
        z-index: 1;
        background-color: rgba(100, 137, 214, 0.1);
    }

    .card .cs-card-col-0 {
        max-width: 5% !important;
    }

    .card .cs-card-col-1 {
        max-width: 40% !important;
    }

    .card .cs-card-col-2 {
        max-width: 45% !important;
    }

    .card .cs-card-col-3 {
        max-width: 10% !important;
    }
</style>