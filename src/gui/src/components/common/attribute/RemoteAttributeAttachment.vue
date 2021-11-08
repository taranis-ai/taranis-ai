<template>
    <div class="dropzone-wrapper-div">
        <vue-dropzone
                ref="myVueDropzone"
                id="dropzone"
                :options="dropzoneOptions"
                :include-styling="false"
                :useCustomSlot="true"
        >
        </vue-dropzone>

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
                    <v-row>
                        <v-col style="flex-grow: 0;" cols="2">
                            <span class="text--primary">{{ $t('drop_zone.file_description') }}:</span>
                        </v-col>
                        <v-col>
                            <div>{{ selected_attachment.description }}</div>
                        </v-col>
                    </v-row>
                </v-card-text>

                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn v-if="report_item_id !== null" color="primary" dark :href="download_link">
                        {{ $t('drop_zone.download') }}
                        <v-icon right dark>mdi-cloud-download</v-icon>
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
import {vm} from "@/main.js";
import AttributesMixin from "@/components/common/attribute/attributes_mixin";

const getTemplate = () => `
         <div cs class="dz-preview dz-file-preview">
         <div onclick="window.dispatchEvent(new CustomEvent('attachment-click', {detail: 'FILE_ID'}))">
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
    name: "RemoteAttributeAttachment",
    components: {
        vueDropzone: vue2Dropzone
    },
    mixins: [AttributesMixin],
    data: () => ({
        detailDialog: false,
        description: "",
        last_updated: "",
        files: [],
        download_link: "",
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
                    + '/analyze/attribute/addattachment/',
            thumbnailWidth: 64,
            thumbnailHeight: 96,
            previewTemplate: getTemplate(),
            addRemoveLinks: false,
            autoProcessQueue: false,
            clickable: false
        }
    }),
    methods: {
        fileAdded(file) {
            let previewHTML = file.previewTemplate.innerHTML;
            previewHTML = previewHTML.replace('FILE_ID', file.id);
            file.previewTemplate.innerHTML = previewHTML;
            this.files.push(file);
        },
        closeDetail() {
            this.detailDialog = false;
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
                        + '/analyze/attribute/download/'
                        + this.values[i].id + "?jwt=" + this.$store.getters.getJWT;
                this.$refs.myVueDropzone.manuallyAddFile(file, url);
            }
        }
    },
    mounted() {
        this.$root.$on('attachment-clicked', (data) => {
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
                            + '/analyze/attribute/download/'
                            + this.selected_attachment.id + "?jwt=" + this.$store.getters.getJWT;
                    this.detailDialog = true;
                    break;
                }
            }
        });

        if (this.report_item_id !== null) {
            this.$refs.myVueDropzone.setOption('url', ((typeof (process.env.VUE_APP_TARANIS_NG_CORE_API) == "undefined")
                    ? "$VUE_APP_TARANIS_NG_CORE_API"
                    : process.env.VUE_APP_TARANIS_NG_CORE_API)
                    + '/analyze/attribute/addattachment/' + this.report_item_id)
        }

        this.initDropzone()
    },
    created() {
        window.addEventListener('attachment-click', function (e) {

            vm.$emit("attachment-clicked", {
                attachment_id: e.detail,
            })

        }, false);
    },
    beforeDestroy() {
        this.$root.$off('attachment-clicked')
    }
}
</script>