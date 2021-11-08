<template>
    <div class="dropzone-wrapper-div">
        <vue-dropzone
                ref="myVueDropzone"
                id="dropzone"
                v-on:vdropzone-file-added="fileAdded"
                v-on:vdropzone-sending="sendingEvent"
                v-on:vdropzone-success="uploadSuccess"
                :options="getOptions"
                :include-styling="false"
                :useCustomSlot="true"
        >
            <div v-if="!read_only" class="subtitle-2 text-center pt-5 grey--text">{{
                    $t('drop_zone.default_message')
                }}
            </div>
        </vue-dropzone>

        <v-dialog v-model="renameDialog" max-width="700px">
            <v-card>
                <v-card-title>
                    <span class="headline">{{ $t('drop_zone.attachment_load') }}</span>
                </v-card-title>

                <v-card-text>
                    <v-textarea v-model="description" :label="$t('drop_zone.file_description')"></v-textarea>
                </v-card-text>

                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn color="primary" dark @click="save">{{ $t('drop_zone.save') }}</v-btn>
                    <v-btn color="primary" text @click="close">{{ $t('drop_zone.cancel') }}</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <v-dialog v-model="detailDialog" max-width="700px">
            <v-card>
                <v-card-title>
                    <span class="headline">{{ $t('drop_zone.attachment_detail') }}</span>
                </v-card-title>

                <v-card-text>
                    <v-row v-if="selected_attachment.last_updated !== null">
                        <v-col style="flex-grow: 0;" cols="2">
                            <span class="text--primary">{{ $t('drop_zone.last_updated') }}:</span>
                        </v-col>
                        <v-col>
                            <div>{{ selected_attachment.last_updated }}</div>
                        </v-col>
                    </v-row>
                    <v-row>
                        <v-col style="flex-grow: 0">
                            <v-icon class="text--primary">mdi-file-document</v-icon>
                        </v-col>
                        <v-col>
                            <div>{{ selected_attachment.file_name }}</div>
                        </v-col>
                    </v-row>
                    <v-row v-if="read_only || report_item_id !== null">
                        <v-col style="flex-grow: 0;" cols="2">
                            <span class="text--primary">{{ $t('drop_zone.file_description') }}:</span>
                        </v-col>
                        <v-col>
                            <div>{{ selected_attachment.description }}</div>
                        </v-col>
                    </v-row>
                    <v-textarea v-if="!read_only && report_item_id === null" v-model="selected_attachment.description"
                                :label="$t('drop_zone.file_description')"></v-textarea>
                </v-card-text>

                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn v-if="!read_only && report_item_id === null" color="primary" dark @click="saveDetail">
                        {{ $t('drop_zone.save') }}
                    </v-btn>
                    <v-btn v-if="report_item_id !== null" color="primary" dark :href="download_link">
                        {{ $t('drop_zone.download') }}
                        <v-icon right dark>mdi-cloud-download</v-icon>
                    </v-btn>
                    <v-btn v-if="!read_only" color="primary" dark @click="removeDetail">{{ $t('drop_zone.delete') }}
                        <v-icon right dark>mdi-delete</v-icon>
                    </v-btn>
                    <v-btn color="primary" text @click="closeDetail">{{ $t('drop_zone.cancel') }}</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

    </div>
</template>

<script>
import vue2Dropzone from 'vue2-dropzone';
import 'vue2-dropzone/dist/vue2Dropzone.min.css';
import {removeAttachment} from "@/api/analyze";
import {vm} from "@/main.js";
import AttributesMixin from "@/components/common/attribute/attributes_mixin";

const getTemplate = () => `
         <div cs class="dz-preview dz-file-preview">
         <div onclick="window.dispatchEvent(new CustomEvent('attachment-click', {detail: {file_id: 'FILE_ID', attribute_id: ATTR_ID}}))">
            <div class="v-icon mdi mdi-file-document-outline theme--light"></div>
            <div class="dz-image">
                <div data-dz-thumbnail-bg></div>
            </div>
            <div class="dz-details">
                <div class="dz-filename"><span data-dz-name></span></div>
            </div>
            <div class="dz-progress"><span class="dz-upload" data-dz-uploadprogress></span></div>
            <div class="dz-error-message"><span data-dz-errormessage></span></div>
            <div class="dz-success-mark"><i class="fa fa-check"></i></div>
            <div class="dz-error-mark"><i class="fa fa-close"></i></div>
            </div>
        </div>
    `;

export default {
    name: "AttributeAttachment",
    components: {
        vueDropzone: vue2Dropzone
    },
    mixins: [AttributesMixin],
    data: () => ({
        renameDialog: false,
        detailDialog: false,
        description: "",
        last_updated: "",
        files: [],
        download_link: "",
        new_report_item: null,
        selected_attachment: {
            id: "",
            file_name: "",
            size: -1,
            mime_type: "",
            user_name: "",
            last_updated: "",
            description: ""
        },

        dropzoneOptions: {
            url: ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined")
                    ? "$VUE_APP_TARANIS_NG_CORE_API"
                    : process.env.VUE_APP_TARANIS_NG_CORE_API)
                    + '/analyze/report-items',
            thumbnailWidth: 64,
            thumbnailHeight: 96,
            previewTemplate: getTemplate(),
            addRemoveLinks: false,
            autoProcessQueue: false,
            clickable: true
        }
    }),
    computed: {
        getOptions() {
            if (this.read_only) {
                return {
                    url: ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined")
                            ? "$VUE_APP_TARANIS_NG_CORE_API"
                            : process.env.VUE_APP_TARANIS_NG_CORE_API)
                    + '/analyze/report-items/' + this.report_item_id + '/file-attributes',
                            thumbnailWidth: 64,
                            thumbnailHeight: 96,
                            previewTemplate: getTemplate(),
                            addRemoveLinks: false,
                            autoProcessQueue: false,
                            clickable: false
                }
            } else {
                return {
                    url: ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined")
                            ? "$VUE_APP_TARANIS_NG_CORE_API"
                            : process.env.VUE_APP_TARANIS_NG_CORE_API)
                        + '/analyze/report-items/' + this.report_item_id + '/file-attributes',
                    thumbnailWidth: 64,
                    thumbnailHeight: 96,
                    previewTemplate: getTemplate(),
                    addRemoveLinks: false,
                    autoProcessQueue: false,
                    clickable: true
                }
            }
        }
    },
    methods: {
        sendingEvent(file, xhr, formData) {
            xhr.setRequestHeader("Authorization", "Bearer " + localStorage.ACCESS_TOKEN)
            formData.append('attribute_group_item_id', this.attribute_group.id);
            if (this.report_item_id === null) {
                formData.append('description', file.description);
            } else {
                formData.append('description', this.description);
            }
        },
        uploadSuccess(file, response) {
            file.id = response;
            if (this.report_item_id === null) {
                if (this.$refs.myVueDropzone.getQueuedFiles().length === 0) {
                    this.$refs.myVueDropzone.removeAllFiles();
                    this.files = [];
                    this.values = [];
                    this.$root.$emit('attachments-uploaded', {});
                }
            } else {
                file.description = this.description;
                let previewHTML = file.previewTemplate.innerHTML;
                previewHTML = previewHTML.replace('FILE_ID', file.id).replace('ATTR_ID', this.attribute_group.id);
                file.previewTemplate.innerHTML = previewHTML;
            }
        },
        fileAdded(file) {
            if (this.read_only) {
                this.$refs.myVueDropzone.removeFile(file)
                return
            }

            if (this.report_item_id === null) {
                this.renameDialog = true;
                file.id = this.files.length;
                let previewHTML = file.previewTemplate.innerHTML;
                previewHTML = previewHTML.replace('FILE_ID', file.id).replace('ATTR_ID', this.attribute_group.id);
                file.previewTemplate.innerHTML = previewHTML;
                this.values.push({
                    id: file.id,
                    value: file.name
                })
            } else {
                if (typeof file.id === 'undefined') {
                    this.description = "";
                    this.renameDialog = true;
                } else {
                    let previewHTML = file.previewTemplate.innerHTML;
                    previewHTML = previewHTML.replace('FILE_ID', file.id).replace('ATTR_ID', this.attribute_group.id);
                    file.previewTemplate.innerHTML = previewHTML;
                }
            }
            this.files.push(file);
        },
        save() {
            if (this.report_item_id === null) {
                let files = this.$refs.myVueDropzone.getQueuedFiles();
                for (let i = 0; i < files.length; i++) {
                    if (typeof files[i].description === 'undefined') {
                        files[i].description = this.description
                    }
                }
                this.description = ""
            } else {
                this.$refs.myVueDropzone.processQueue()
            }
            this.renameDialog = false;
        },
        close() {
            this.description = "";
            this.renameDialog = false;
            let files = this.$refs.myVueDropzone.getQueuedFiles();
            for (let i = 0; i < files.length; i++) {
                if (this.report_item_id === null) {
                    if (typeof files[i].description === 'undefined') {
                        this.$refs.myVueDropzone.removeFile(files[i])
                    }
                } else {
                    this.$refs.myVueDropzone.removeFile(files[i])
                }
            }
        },
        saveDetail() {
            if (this.report_item_id === null) {
                this.detailDialog = false;
                this.selected_attachment.file.description = this.selected_attachment.description
            }
            this.detailDialog = false;
        },
        closeDetail() {
            this.detailDialog = false;
        },
        removeDetail() {
            if (this.report_item_id === null) {
                this.detailDialog = false;
                for (let i = 0; i < this.values.length; i++) {
                    if (this.values[i].id === this.selected_attachment.file.id) {
                        this.values.splice(i, 1);
                        break;
                    }
                }
                this.$refs.myVueDropzone.removeFile(this.selected_attachment.file);
            } else {
                removeAttachment({
                    report_item_id: this.report_item_id,
                    attribute_id: this.selected_attachment.id,
                }).then(() => {
                    this.$refs.myVueDropzone.removeFile(this.selected_attachment.file);
                    for (let i = 0; i < this.values.length; i++) {
                        if (this.values[i].id === this.selected_attachment.id) {
                            this.values.splice(i, 1);
                            break;
                        }
                    }
                    this.detailDialog = false;
                });
            }
        },
        addFile(value) {
            let file = {
                id: value.id,
                size: value.binary_size,
                name: value.value,
                type: value.binary_mime_type,
                description: value.binary_description,
                last_updated: value.last_updated + " " + value.user.name,
            };
            let url = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined")
                    ? "$VUE_APP_TARANIS_NG_CORE_API"
                    : process.env.VUE_APP_TARANIS_NG_CORE_API)
                    + '/analyze/report-items/' + this.report_item_id + '/file-attributes/'
                    + value.id + "/file?jwt=" + this.$store.getters.getJWT;
            this.$refs.myVueDropzone.manuallyAddFile(file, url);
        },
        removeFile(file_id) {
            for (let i = 0; i < this.files.length; i++) {
                if (this.files[i].id.toString() === file_id) {
                    this.$refs.myVueDropzone.removeFile(this.files[i]);
                    this.files.splice(i, 1);
                    break;
                }
            }
        },
        initDropzone() {
            this.$refs.myVueDropzone.removeAllFiles();
            this.files = [];
            for (let i = 0; i < this.values.length; i++) {
                let file = {
                    id: this.values[i].id,
                    size: this.values[i].binary_size,
                    name: this.values[i].value,
                    type: this.values[i].binary_mime_type,
                    description: this.values[i].binary_description,
                    last_updated: this.values[i].last_updated + " " + this.values[i].user.name,
                };
                let url = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined")
                        ? "$VUE_APP_TARANIS_NG_CORE_API"
                        : process.env.VUE_APP_TARANIS_NG_CORE_API)
                        + '/analyze/report-items/' + this.report_item_id + '/file-attributes/'
                        + this.values[i].id + "/file?jwt=" + this.$store.getters.getJWT;
                this.$refs.myVueDropzone.manuallyAddFile(file, url);
            }
        }
    },
    mounted() {
        this.$root.$on('attachment-clicked', (data) => {
            if (this.report_item_id === null) {
                if (this.attribute_group.id === data.attribute_id) {
                    for (let i = 0; i < this.files.length; i++) {
                        if (this.files[i].id.toString() === data.attachment_id) {
                            this.selected_attachment = {
                                id: this.files[i].id,
                                file_name: this.files[i].name,
                                description: this.files[i].description,
                                file: this.files[i],
                                last_updated: null
                            };
                            this.detailDialog = true;
                            break;
                        }
                    }
                }
            } else {
                for (let i = 0; i < this.files.length; i++) {
                    if (this.files[i].id.toString() === data.attachment_id) {
                        this.selected_attachment = {
                            id: this.files[i].id,
                            file_name: this.files[i].name,
                            mime_type: this.files[i].type,
                            file_size: this.files[i].size,
                            description: this.files[i].description,
                            last_updated: this.files[i].last_updated,
                            file: this.files[i]
                        };
                        this.download_link = ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined")
                                ? "$VUE_APP_TARANIS_NG_CORE_API"
                                : process.env.VUE_APP_TARANIS_NG_CORE_API)
                                + '/analyze/report-items/' + this.report_item_id + '/file-attributes/'
                                + this.selected_attachment.id + "/file?jwt=" + this.$store.getters.getJWT;
                        this.detailDialog = true;
                        break;
                    }
                }
            }
        });

        this.$root.$on('dropzone-new-process', (data) => {
            if (this.report_item_id === null) {
                this.$refs.myVueDropzone.setOption('url', ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined")
                        ? "$VUE_APP_TARANIS_NG_CORE_API"
                        : process.env.VUE_APP_TARANIS_NG_CORE_API)
                        + '/analyze/report-items/' + data.report_item_id + '/file-attributes')

                if (this.$refs.myVueDropzone.getQueuedFiles().length === 0) {
                    this.$root.$emit('attachments-uploaded', {});
                } else {
                    this.$refs.myVueDropzone.processQueue()
                }
            }
        });

        if (this.report_item_id !== null) {
            this.$refs.myVueDropzone.setOption('url', ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined")
                    ? "$VUE_APP_TARANIS_NG_CORE_API"
                    : process.env.VUE_APP_TARANIS_NG_CORE_API)
                    + '/analyze/report-items/' + this.report_item_id + '/file-attributes')
        }

        this.initDropzone()
    },
    created() {
        window.addEventListener('attachment-click', function (e) {
            vm.$emit("attachment-clicked", {
                attachment_id: e.detail.file_id,
                attribute_id: e.detail.attribute_id
            })

        }, false);
    },
    beforeDestroy() {
        this.$root.$off('attachment-clicked')
        this.$root.$off('dropzone-new-process')
    }
}
</script>