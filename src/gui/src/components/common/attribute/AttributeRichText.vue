<template>
    <AttributeItemLayout
            :add_button="addButtonVisible"
            @add-value="add()"
            :values="values"
    >
        <template v-slot:header>


        </template>
        <template v-slot:content>
            <v-row v-for="(value, index) in values" :key="value.index"
                   class="valueHolder"
            >
                <span v-if="read_only || values[index].remote">{{values[index].value}}</span>
                <AttributeValueLayout
                        v-if="!read_only && canModify && !values[index].remote"
                        :del_button="delButtonVisible"
                        @del-value="del(index)"
                        :occurrence="attribute_group.min_occurrence"
                        :values="values"
                        :val_index="index"
                        class="pb-4"
                >
                    <template v-slot:col_middle>

                        <div class="py-2">
                            <vue-editor
                                    ref="myTextEditor"
                                    v-model="values[index].value"
                                    :editorOptions="editorOptionVue2"
                                    @selection-change="onSelectionChange"
                                    @focus="onFocus(index)"
                                    @blur="onBlur(index)"
                                    @keyup="onKeyUp(index)"
                                    :disabled="values[index].locked || !canModify"
                                    :class="getLockedStyle(index)"
                            >
                                <div class="toolbar" slot="toolbar">

                                    <!--<button class="ql-bold">Bold</button>
                                    <button class="ql-italic">Italic</button>

                                    <select class="ql-size">
                                        <option value="small"></option>
                                        <option selected></option>
                                        <option value="large"></option>
                                        <option value="huge"></option>
                                    </select>
                                    <select class="ql-font">
                                        <option selected="selected"></option>
                                        <option value="serif"></option>
                                        <option value="monospace"></option>
                                    </select>

                                    <button class="ql-script" value="sub"></button>
                                    <button class="ql-script" value="super"></button>-->

                                    <!--<v-btn small text @click="selectionWrap">
                                        <v-icon>mdi-account</v-icon>
                                    </v-btn>-->

                                    <!-- Insert Template -->
                                    <v-row justify="center" no-gutters>
                                        <v-col style="width: 40%;">
                                            <v-select
                                                    v-model="select"
                                                    :items="templates"
                                                    item-text="name"
                                                    item-value="template"
                                                    return-object
                                                    label="Insert Template"
                                            ></v-select>
                                        </v-col>
                                        <v-col align-self="center" style="max-width: 10%;">
                                            <v-btn text @click="insertTemplate">
                                                <v-icon>mdi-view-grid-plus</v-icon>
                                            </v-btn>
                                        </v-col>
                                    </v-row>
                                </div>
                            </vue-editor>
                        </div>

                    </template>
                </AttributeValueLayout>
            </v-row>
        </template>

    </AttributeItemLayout>
</template>

<script>
    import AttributesMixin from "@/components/common/attribute/attributes_mixin";
    import AttributeItemLayout from "../../layouts/AttributeItemLayout";
    import AttributeValueLayout from "../../layouts/AttributeValueLayout";

    import { VueEditor, Quill } from 'vue2-editor';

    const toolbarOptions = [
        ['bold', 'italic', 'underline', 'strike'],        // toggled buttons
        ['blockquote', 'code-block'],

        [{ 'header': 1 }, { 'header': 2 }],               // custom button values
        [{ 'list': 'ordered'}, { 'list': 'bullet' }],
        [{ 'script':'sub'}, { 'script': 'super' }],      // superscript/subscript
        [{ 'indent': '-1'}, { 'indent': '+1' }],          // outdent/indent
        [{ 'direction': 'rtl' }],                         // text direction

        [{ 'size': ['small', false, 'large', 'huge'] }],  // custom dropdown
        [{ 'header': [1, 2, 3, 4, 5, 6, false] }],

        [{ 'color': [] }, { 'background': [] }],          // dropdown with defaults from theme
        [{ 'font': [] }],
        [{ 'align': [] }],

        ['clean'],                                         // remove formatting button
        ['link', 'image', 'video'],
        ['publish']
    ];

    let Inline = Quill.import('blots/inline');

    class Publish extends Inline {

        static create(){
            let node = super.create();
            //node.setAttribute('class','spanblock');
            return node;
        }
    }

    Publish.blotName = 'publish';
    Publish.tagName = 'publish';
    Quill.register(Publish);

    export default {
        name: "AttributeRichText",
        props: {
            attribute_group: Object,
        },
        components: {
            AttributeItemLayout,
            AttributeValueLayout,
            VueEditor
        },
        data: () => ({
                multi: null,
                content: null,
                selection: null,
                selectionRange: null,
                editorOptionVue2: {
                    theme: 'snow',
                    placeholder: "insert text here ...",
                    modules: {
                        toolbar: toolbarOptions
                    }
                },
                select: null,
                templates: [
                    {name:'Placeholder Text', template: "Official website of the Department of Homeland Security All information products included in https://us-cert.gov/ics are provided \"as is\" for informational purposes only. The Department of Homeland Security (DHS) does not provide any warranties of any kind regarding any information contained within. DHS does not endorse any commercial product or service, referenced in this product or otherwise. "},
                    {name:'Placeholder Text 2', template: "The impact and exploitability of the identified problem is dependent on the implementation and controls. Successful exploitation of this vulnerability in automation task programs or abuse of such powerful programming features may allow an attacker with network access and extensive knowledge of industrial robotics to exfiltrate data from, partially control the movements of, or disrupt the availability of arbitrary functions of the targeted device. "},
                    {name:'Placeholder Text 3', template: "Template Data"}
                ]
        }),
        mixins: [AttributesMixin],
        computed: {
            editor() {
                return this.$refs.myTextEditor[0].quill;
            }
        },
        mounted() {
            this.content = this.values.value;
        },
        methods: {
            onSelectionChange(range) {

                try {
                    this.selection = range;
                    this.update();
                } catch(err) {
                    //pass
                }
            },
            insertTemplate() {
                if(this.select) {
                    //let deltaTemplate = this.editor.clipboard.convert(this.select.template);

                    //let deltaContent = this.editor.getContents();
                    //window.console.debug("DC", deltaContent);
                    //let preDelta = deltaContent.retain(this.editor.getSelection().index).insert(deltaTemplate)

                    //let delta = this.editor.clipboard.convert(preDelta)
                    //window.console.debug("DELTA", delta);
                    try {
                        this.editor.insertText(this.editor.selection.lastRange, this.select.template);
                        this.update();
                    } catch(err) {
                        // pass
                    }

                    //let preContent = this.content;

                    //this.editor.setContents(delta, 'silent');

                    //let upd = this.editor.updateContents(delta);
                    //window.console.debug(upd);

                    /*this.editor.updateContents(
                        new Delta().retain(19).insert(deltaTemplate)
                    );*/

                    /*this.editor.updateContents(
                        delta.retain(this.editor.getSelection().index).insert(deltaTemplate)
                    );*/

                    //window.console.debug(deltaContent.retain(this.editor.getSelection().index).insert(deltaTemplate));
                }
            },
            update() {
                //this.values.value = this.content;
                setTimeout(()=>{
                    this.values.value = this.content;
                    this.onEdit(0);
                },200);
            }
        }
    }
</script>

<style>
    div.ck.ck-editor__main {
        max-height: 512px;
        overflow: auto;
    }
    .ql-customControl:after {
        content: 'T';
    }
    button.ql-insertTemplate,
    button.ql-textTag {
        width: auto !important;
    }
    button.ql-insertTemplate::after {
        content: 'Templates';
    }
    button.ql-textTag::after {
        content: 'Tag'
    }

    publish {
        background-color: #ffff9fa0;
        box-shadow: 0px 0px 0px 4px #ffff9fa0;
    }

    button.ql-publish {
        width: auto !important;
        background-color: rgba(0,0,0,0.2) !important;
        color: white;
        line-height: 1;
        border-radius: 16px;
        padding: 0px 12px 0px 12px !important;
        font-size: 0.9em;
        font-weight: normal;
    }
    button.ql-publish:hover {
        color: white !important;
        background-color: rgba(0,0,0,0.5) !important;
    }

    .ql-publish:after {
        content: "Publish";
    }

</style>

