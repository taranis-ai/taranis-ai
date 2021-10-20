<template>

    <v-hover v-slot:default="{hover}" close-delay="150">
        <v-card flat class="card mb-1" :elevation="hover ? 12 : 2"
                @click.stop="cardItemToolbar"
                @mouseenter.native="toolbar=true"
                @mouseleave.native="toolbar=false"
        >
            <v-layout row wrap class="pa-3 pl-0 status">
                <v-flex md1 class="obj center">
                    <div class="caption grey--text"><br/></div>
                    <div>
                        <v-icon center>{{card.tag}}</v-icon>
                    </div>
                </v-flex>
                <v-flex md5>
                    <div class="caption grey--text">{{$t('card_item.title')}}</div>
                    <span>{{card.title}}</span>
                </v-flex>
                <v-flex md5>
                    <div class="caption grey--text ">{{$t('card_item.description')}}</div>
                    <span class="font-weight-light caption">{{card.subtitle}}</span>
                </v-flex>
                <v-flex md1 class="obj center">
                    <v-speed-dial
                            v-model="toolbar"
                            direction="left"
                            transition='slide-x-reverse-transition'
                    >

                        <v-btn v-if="canDelete" fab x-small color="red" @click.stop="cardItemToolbar('delete')" :title="$t('publish.tooltip.delete_item')">
                            <v-icon color="white">mdi-trash-can-outline</v-icon>
                        </v-btn>
                    </v-speed-dial>
                </v-flex>
            </v-layout>
        </v-card>
    </v-hover>
</template>

<script>
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "CardProduct",
        props: ['card'],
        data:() => ({
            toolbar: false
        }),
        mixins: [AuthMixin],
        computed: {
            canDelete() {
               return this.checkPermission(Permissions.PUBLISH_DELETE) && this.card.modify === true
            }
        },
        methods: {
            itemClicked(data) {
                this.$root.$emit('show-product-edit', data)
            },
            deleteClicked(data) {
                this.$root.$emit('delete-product', data)
            },
            buttonClicked() {

            },
            cardItemToolbar(action) {
                switch (action) {
                    case "edit":
                        break;

                    case "delete":
                        this.deleteClicked(this.card);
                        break;

                    default:
                        this.toolbar = false;
                        this.itemClicked(this.card);
                        break;
                }
            }
        }
    }
</script>