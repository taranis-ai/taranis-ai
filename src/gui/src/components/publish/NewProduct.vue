<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="add_button && canCreate"
               @click="addProduct">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{ $t('product.add_btn') }}</span>
        </v-btn>

        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible" new-product>
            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" :style="UI.STYLE.z10000">
                    <v-btn v-bind="UI.BUTTON.CLOSE_ICON" @click="cancel">
                        <v-icon>{{ UI.ICON.CLOSE }}</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('product.add_new') }}</span>
                        <span v-else>{{ $t('product.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>
                    <v-btn v-if="canModify" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{ $t('report_item.save') }}</span>
                    </v-btn>
                </v-toolbar>

                <v-form @submit.prevent="add" id="form" ref="form" class="px-4">
                    <v-row no-gutters>
                        <v-col cols="6" class="pr-3">
                            <v-combobox v-on:change="productSelected" :disabled="!canModify"
                                        v-model="selected_type"
                                        :items="product_types"
                                        item-text="title"
                                        :label="$t('product.report_type')"
                            />
                        </v-col>
                        <v-col cols="6" class="pr-3">
                            <v-text-field :disabled="!canModify"
                                          :label="$t('product.title')"
                                          name="title"
                                          type="text"
                                          v-model="product.title"
                                          v-validate="'required'"
                                          data-vv-name="title"
                                          :error-messages="errors.collect('title')"
                                          :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                        <v-col cols="12" class="pr-3">
                            <v-textarea :disabled="!canModify"
                                        :label="$t('product.description')"
                                        name="description"
                                        v-model="product.description"
                                        :spellcheck="$store.state.settings.spellcheck"
                            />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12" class="mb-2">
                            <v-btn v-bind="UI.BUTTON.ADD_NEW_IN" v-if="canModify" @click="$refs.report_item_selector.openSelector()">
                                <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
                                <span>{{$t('report_item.select')}}</span>
                            </v-btn>
                        </v-col>
                        <v-col cols="12">
                            <ReportItemSelector ref="report_item_selector" :values="report_items" :modify="modify"
                                                :edit="edit" />
                        </v-col>
                    </v-row>
                    <v-row no-gutters>
                        <v-col cols="12">
                            <v-checkbox v-for="preset in publisher_presets" :key="preset.id"
                                        :label="preset.name" :disabled="!canModify" v-model="preset.selected">
                            </v-checkbox>
                        </v-col>
                    </v-row>
                    <v-row no-gutters class="pt-4">
                        <v-col cols="6">
                            <v-btn :href="preview_link" style="display: none"
                                   target="_blank" ref="previewBtn">
                            </v-btn>
                            <v-btn depressed small @click="previewProduct">
                                <v-icon left>mdi-eye-outline</v-icon>
                                <span>{{ $t('product.preview') }}</span>
                            </v-btn>
                        </v-col>
                        <v-col cols="6">
                            <v-btn v-if="canPublish" depressed small @click="publishProduct">
                                <v-icon left>mdi-send-outline</v-icon>
                                <span>{{ $t('product.publish') }}</span>
                            </v-btn>
                        </v-col>
                    </v-row>

                    <v-row no-gutters class="pt-2">
                        <v-col cols="12">
                            <v-alert v-if="show_validation_error" dense type="error" text>
                                {{ $t('report_item.validation_error') }}
                            </v-alert>
                            <v-alert v-if="show_error" dense type="error" text>
                                {{ $t('report_item.error') }}
                            </v-alert>
                        </v-col>
                    </v-row>

                </v-form>
            </v-card>
        </v-dialog>
    </v-row>
</template>

<script>
import AuthMixin from "../../services/auth/auth_mixin";
import {createProduct, publishProduct, updateProduct} from "@/api/publish";
import ReportItemSelector from "@/components/publish/ReportItemSelector";
import Permissions from "@/services/auth/permissions";

export default {
    name: "NewProduct",
    components: {ReportItemSelector},
    props: {add_button: Boolean},
    data: () => ({
        visible: false,
        show_validation_error: false,
        edit: false,
        show_error: false,
        modify: false,
        access: false,
        product_types: [],
        publisher_presets: [],
        selected_type: null,
        report_items: [],
        preview_link: "",
        product: {
            id: -1,
            title: "",
            description: "",
            product_type_id: null,
            report_items: [],
        }
    }),
    mixins: [AuthMixin],
    computed: {
        canCreate() {
            return this.checkPermission(Permissions.PUBLISH_CREATE)
        },

        canModify() {
            return this.edit === false || (this.checkPermission(Permissions.PUBLISH_UPDATE) && this.modify === true)
        },

        canPublish() {
            return this.publisher_presets.length > 0 && (this.edit === false || (this.checkPermission(Permissions.PUBLISH_PRODUCT) && this.access === true))
        }
    },
    methods: {
        addProduct() {
            this.visible = true;
            this.edit = false
            this.show_error = false;
            this.modify = false
            this.access = false
            this.selected_type = null;
            this.report_items = []
            this.product.id = -1
            this.product.title = ""
            this.product.description = ""
            this.product.product_type_id = null
            this.product.report_items = []
            this.$validator.reset();
        },

        publishProduct() {

            for (let i = 0; i < this.publisher_presets.length; i++) {
                if (this.publisher_presets[i].selected) {
                    this.$validator.validateAll().then(() => {

                        if (!this.$validator.errors.any()) {

                            this.show_validation_error = false;
                            this.show_error = false;

                            this.product.product_type_id = this.selected_type.id;

                            this.product.report_items = [];
                            for (let i = 0; i < this.report_items.length; i++) {
                                this.product.report_items.push(
                                    {
                                        id: this.report_items[i].id
                                    }
                                )
                            }

                            if (this.product.id !== -1) {
                                updateProduct(this.product).then(() => {

                                    this.$validator.reset();
                                    publishProduct(this.product.id, this.publisher_presets[i].id)
                                })
                            } else {
                                createProduct(this.product).then((response) => {

                                    this.$validator.reset();
                                    this.product.id = response.data
                                    publishProduct(this.product.id, this.publisher_presets[i].id)
                                })
                            }

                        } else {

                            this.show_validation_error = true;
                        }
                    })
                }
            }
        },

        productSelected() {

        },

        cancel() {
            this.$validator.reset();
            this.visible = false
        },

        previewProduct() {
            this.$validator.validateAll().then(() => {

                if (!this.$validator.errors.any()) {

                    this.show_validation_error = false;
                    this.show_error = false;

                    this.product.product_type_id = this.selected_type.id;

                    this.product.report_items = [];
                    for (let i = 0; i < this.report_items.length; i++) {
                        this.product.report_items.push(
                            {
                                id: this.report_items[i].id
                            }
                        )
                    }

                    if (this.product.id !== -1) {
                        updateProduct(this.product).then(() => {

                            this.$validator.reset();
                            this.preview_link = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined") ? "$VUE_APP_TARANIS_NG_CORE_API" : process.env.VUE_APP_TARANIS_NG_CORE_API) + "/publish/products/" + this.product.id + "/overview?jwt=" + this.$store.getters.getJWT
                            this.$refs.previewBtn.$el.click()
                        })
                    } else {
                        createProduct(this.product).then((response) => {

                            this.product.id = response.data
                            this.$validator.reset();
                            this.preview_link = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined") ? "$VUE_APP_TARANIS_NG_CORE_API" : process.env.VUE_APP_TARANIS_NG_CORE_API) + "/publish/products/" + response.data + "/overview?jwt=" + this.$store.getters.getJWT
                            this.$refs.previewBtn.$el.click()
                        })
                    }

                } else {

                    this.show_validation_error = true;
                }
            })
        },

        add() {
            this.$validator.validateAll().then(() => {

                if (!this.$validator.errors.any()) {

                    this.show_validation_error = false;
                    this.show_error = false;

                    this.product.product_type_id = this.selected_type.id;

                    this.product.report_items = [];
                    for (let i = 0; i < this.report_items.length; i++) {
                        this.product.report_items.push(
                            {
                                id: this.report_items[i].id
                            }
                        )
                    }

                    if (this.product.id !== -1) {
                        updateProduct(this.product).then(() => {

                            this.$validator.reset();
                            this.visible = false;

                            this.$root.$emit('notification',
                                {
                                    type: 'success',
                                    loc: 'product.successful_edit'
                                }
                            )
                        }).catch(() => {

                            this.show_error = true;
                        })
                    } else {
                        createProduct(this.product).then(() => {

                            this.$validator.reset();
                            this.visible = false;

                            this.$root.$emit('notification',
                                {
                                    type: 'success',
                                    loc: 'product.successful'
                                }
                            )

                        }).catch(() => {

                            this.show_error = true;
                        })
                    }
                } else {

                    this.show_validation_error = true;
                }
            })
        }
    },
    mounted() {

        this.$root.$on('new-product', (data) => {
            this.visible = true;
            this.selected_type = null;
            this.report_items = data
        });

        this.$store.dispatch('getAllUserProductTypes', {search: ''})
            .then(() => {
                this.product_types = this.$store.getters.getProductTypes.items
            });

        this.$store.dispatch('getAllUserPublishersPresets', {search: ''})
            .then(() => {
                this.publisher_presets = this.$store.getters.getProductsPublisherPresets.items;
                for (let i = 0; i < this.publisher_presets.length; i++) {
                    this.publisher_presets.selected = false
                }
            });

        this.$root.$on('show-product-edit', (data) => {
            this.visible = true;
            this.edit = true;
            this.modify = data.modify
            this.access = data.access
            this.show_error = false;

            this.selected_type = null;
            this.report_items = data.report_items;

            this.product.id = data.id;
            this.product.title = data.title;
            this.product.description = data.description;
            this.product.product_type_id = data.product_type_id;

            for (let i = 0; i < this.product_types.length; i++) {
                if (this.product_types[i].id === this.product.product_type_id) {
                    this.selected_type = this.product_types[i];
                    break;
                }
            }

            this.preview_link = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined") ? "$VUE_APP_TARANIS_NG_CORE_API" : process.env.VUE_APP_TARANIS_NG_CORE_API) + "/publish/products/" + data.id + "/overview?jwt=" + this.$store.getters.getJWT
        });
    },
    beforeDestroy() {
        this.$root.$off('new-product')
        this.$root.$off('show-product-edit')
    },
}
</script>