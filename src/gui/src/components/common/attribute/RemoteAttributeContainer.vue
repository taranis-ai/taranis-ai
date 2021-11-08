<template>
    <v-card>
        <v-card-title style="font-size: 16px; font-weight: bold; padding-top:0; padding-bottom:0">
            {{ attribute_item.title }}
        </v-card-title>

        <v-card-text>
            <v-divider style="padding-bottom:8px"></v-divider>
            <component v-bind:is="attributeType()" :values="attribute_item.values"></component>
        </v-card-text>
    </v-card>
</template>

<script>
import RemoteAttributeString from "@/components/common/attribute/RemoteAttributeString";
import RemoteAttributeAttachment from "@/components/common/attribute/RemoteAttributeAttachment";

export default {
    name: "RemoteAttributeContainer",
    components: {
        RemoteAttributeString,
        RemoteAttributeAttachment
    },
    props: {
        attribute_item: Object,
    },
    methods: {
        attributeType: function () {
            if (this.attribute_item.attribute_group_item.attribute.type === 'ATTACHMENT') {
                return "RemoteAttributeAttachment"
            } else {
                return "RemoteAttributeString"
            }
        }
    }
}
</script>