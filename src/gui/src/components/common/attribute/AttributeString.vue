<template>

    <!--<div>
        <v-row v-for="(value, index) in values" :key="value.index"
               class="valueHolder"
               @mouseenter="delButton=true"
               @mouseleave="delButton=false"
        >

            <v-col cols="11">
                <span v-if="read_only || values[index].remote">{{values[index].value}}</span>
                <v-text-field v-if="!read_only && !values[index].remote" v-model="values[index].value" :label="$t('attribute.value')"
                              @focus="onFocus(index)" @blur="onBlur(index)" @keyup="onKeyUp(index)"
                              :class="getLockedStyle(index)"
                              :disabled="values[index].locked || !canModify"></v-text-field>
            </v-col>

            <v-col v-if="!read_only && canModify && !values[index].remote" class="mt-6" cols="1">
                <v-btn v-if="delButton" text small @click="del(index)">
                    <v-icon>mdi-close-circle</v-icon>
                </v-btn>
            </v-col>

        </v-row>

        <v-btn v-if="values.length < attribute_group.max_occurrence && !read_only && canModify" depressed small @click="add">
            <v-icon>mdi-plus</v-icon>
        </v-btn>

    </div>-->
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
                        <v-text-field v-if="!read_only && !values[index].remote"
                                      v-model="values[index].value" dense
                                      :label="$t('attribute.value')"
                                      @focus="onFocus(index)" @blur="onBlur(index)" @keyup="onKeyUp(index)"
                                      :class="getLockedStyle(index)"
                                      :disabled="values[index].locked || !canModify"
                        ></v-text-field>
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
        name: "AttributeString",
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
