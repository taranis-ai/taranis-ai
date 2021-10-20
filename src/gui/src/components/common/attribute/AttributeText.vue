<template>
    <AttributeItemLayout
            :add_button="addButtonVisible"
            @add-value="add()"
            :values="values"
    >
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
                >
                    <template v-slot:col_middle>
                        <v-textarea v-if="!read_only && !values[index].remote" v-model="values[index].value" :label="$t('attribute.value')"
                                    @focus="onFocus(index)" @blur="onBlur(index)" @keyup="onKeyUp(index)"
                                    :class="getLockedStyle(index)"
                                    :disabled="values[index].locked || !canModify"
                        ></v-textarea>
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

    export default {
        name: "AttributeText",
        props: {
            attribute_group: Object
        },
        components: {
            AttributeItemLayout,
            AttributeValueLayout
        },
        mixins: [AttributesMixin]
    }
</script>

<style scoped>


</style>