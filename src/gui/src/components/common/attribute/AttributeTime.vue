<template>

    <!--<div>
        <v-row v-for="(value, index) in values" :key="value.index">

            <v-col>
                <span v-if="read_only || values[index].remote">{{values[index].value}}</span>
                <v-menu v-if="!read_only && !values[index].remote"
                        v-model="menu"
                        :close-on-content-click="false"
                        :nudge-right="40"
                        transition="scale-transition"
                        offset-y
                        max-width="290px"
                        min-width="290px"
                        :disabled="values[index].locked"
                >
                    <template v-slot:activator="{ on }">
                        <v-text-field
                                v-model="values[index].value"
                                :label="$t('attribute.value')"
                                prepend-icon="event"
                                readonly
                                v-on="on"
                                @click="open(index)"
                                style="width: 290px;"
                                :disabled="values[index].locked || !canModify" :class="getLockedStyle(index)"
                        ></v-text-field>

                    </template>
                    <v-card>
                        <v-time-picker
                                v-model="values[index].value"
                        ></v-time-picker>
                        <v-btn width="100%" color="info darken-1" @click="close(index)">{{$t('attribute.done')}}</v-btn>
                    </v-card>

                </v-menu>
            </v-col>
        </v-row>
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
                    <template v-slot:col_left>
                        <!--<v-icon right>mdi-clock-outline</v-icon>-->
                    </template>
                    <template v-slot:col_middle>
                        <date-picker
                                v-if="!read_only && !values[index].remote"
                                v-model="values[index].value"
                                type="time"
                                format="HH:mm"
                                value-type="format"
                                @focus="onFocus(index)"
                                @change="onEdit(index)"
                                :disabled="values[index].locked || !canModify"
                        >
                            <template v-slot:icon-calendar>
                                <v-icon class="pb-5">mdi-clock-outline</v-icon>
                            </template>
                            <template v-slot:icon-clear>
                                <v-icon small class="pb-5 pr-1">mdi-close</v-icon>
                            </template>
                            <template v-slot:input>
                                <v-text-field
                                        v-if="!read_only && !values[index].remote"
                                        :placeholder="$t('attribute.select_time')"
                                        dense
                                        v-model="values[index].value"
                                        @focus="onFocus(index)"
                                        @blur="onBlur(index)"
                                        :class="getLockedStyle(index)"
                                        :disabled="values[index].locked || !canModify"
                                ></v-text-field>
                            </template>
                        </date-picker>
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

    import DatePicker from 'vue2-datepicker';
    import 'vue2-datepicker/index.css';

    export default {
        name: "AttributeTime",
        props: {
            attribute_group: Object
        },
        components: {
            AttributeItemLayout,
            AttributeValueLayout,
            DatePicker
        },
        mixins: [AttributesMixin]
    }
</script>