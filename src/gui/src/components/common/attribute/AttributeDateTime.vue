<template>

    <!--<div class="datetime-value">
        <v-row v-for="(value, index) in values" :key="value.index">
            <span v-if="read_only || values[index].remote">{{values[index].value}}</span>
            <v-datetime-picker
                    v-if="!read_only && !values[index].remote"
                    v-model="datetime"
                    :label="$t('attribute.value')"
                    date-format="yyyy.MM.dd"
                    time-format="HH:mm"
                    :disabled="!canModify"
            >

                <template slot="actions" slot-scope="{  }">
                    &lt;!&ndash;<v-btn color="lighten-1" @click.native="parent.clearHandler">{{$t('attribute.cancel')}}</v-btn>
                    <v-btn color="success darken-1" @click="parent.okHandler">Done</v-btn>&ndash;&gt;
                    <v-btn color="info lighten-1" @click="getDateTime(index)">{{$t('attribute.done')}}</v-btn>
                </template>

            </v-datetime-picker>
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
                        <!--<v-icon right>mdi-calendar-clock</v-icon>-->
                    </template>
                    <template v-slot:col_middle>
                        <date-picker
                                v-if="!read_only && !values[index].remote"
                                v-model="values[index].value"
                                type="datetime"
                                format="YYYY.MM.DD-HH:mm"
                                value-type="format"
                                :show-time-panel="showTimePanel"
                                @change="onEdit(index)"
                                @close="handleOpenChange"
                                :disabled="values[index].locked || !canModify"
                        >
                            <template v-slot:footer>
                                <button class="mx-btn mx-btn-text" @click="toggleTimePanel">
                                    {{ showTimePanel ? 'select date' : 'select time' }}
                                </button>
                            </template>

                            <template v-slot:icon-calendar>
                                <v-icon class="pb-5">mdi-calendar-clock</v-icon>
                            </template>
                            <template v-slot:icon-clear>
                                <v-icon small class="pb-5 pr-1">mdi-close</v-icon>
                            </template>
                            <template v-slot:input>
                                <v-text-field
                                        v-if="!read_only && !values[index].remote"
                                        :placeholder="$t('attribute.select_datetime')"
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
        name: "AttributeDateTime",
        props: {
            attribute_group: Object
        },
        components: {
            AttributeItemLayout,
            AttributeValueLayout,
            DatePicker
        },
        data: () => ({
            showTimePanel: false,
            showTimeRangePanel: false
        }),
        mixins: [AttributesMixin],
        methods: {
            toggleTimePanel() {
                this.showTimePanel = !this.showTimePanel;
            },
            toggleTimeRangePanel() {
                this.showTimeRangePanel = !this.showTimeRangePanel;
            },
            handleOpenChange() {
                this.showTimePanel = false;
            },
            handleRangeClose() {
                this.showTimeRangePanel = false;
            }
        }
    }
</script>