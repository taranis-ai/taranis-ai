import {getReportItemData, holdLockReportItem, lockReportItem, unlockReportItem, updateReportItem} from "@/api/analyze";
import AuthMixin from "@/services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";

var AttributesMixin = {

    props: {
        values: Array,
        attribute_group: Object,
        read_only: Boolean,
        report_item_id: Number,
        edit: Boolean,
        modify: Boolean
    },

    data: () => ({
        delButton: false,
        key_timeout: null
    }),

    mixins: [AuthMixin],

    computed: {
        canModify() {
            return this.edit === false || (this.checkPermission(Permissions.ANALYZE_UPDATE) && this.modify === true)
        },
        addButtonVisible() {
            return (this.values.length < this.attribute_group.max_occurrence && !this.read_only && this.canModify);
        },
        delButtonVisible() {
            return this.delButton && !(this.attribute_group.min_occurrence >= this.values.length);
        }
    },

    methods: {
        enumSelected(data) {
            this.values[data.index].value = data.value
            this.onEdit(data.index)
        },

        add() {
            if (this.edit === true) {
                let data = {}
                data.add = true
                data.report_item_id = this.report_item_id
                data.attribute_id = -1
                data.attribute_group_item_id = this.attribute_group.id

                updateReportItem(this.report_item_id, data).then((update_response) => {
                    getReportItemData(this.report_item_id, update_response.data).then((response) => {
                        let data = response.data
                        this.values.push({
                            id: data.attribute_id,
                            index: this.values.length,
                            value: "",
                            last_updated: data.attribute_last_updated,
                            user: {name: data.attribute_user}
                        })
                    })
                })
            } else {
                this.values.push({
                    id: -1,
                    index: this.values.length,
                    value: "",
                    user: null
                })
            }

            var indexRefresh = 0;
            this.values.forEach(val => {
                val.index = indexRefresh++;
            })
        },

        del(index) {
            if (this.edit === true) {
                let data = {}
                data.delete = true
                data.report_item_id = this.report_item_id
                data.attribute_group_item_id = this.attribute_group.id
                data.attribute_id = this.values[index].id

                updateReportItem(this.report_item_id, data).then(() => {
                    this.values.splice(index, 1)
                })
            } else {
                this.values.splice(index, 1)
            }

            var indexRefresh = 0;
            setTimeout(() => {
                this.values.forEach(val => {
                    val.index = indexRefresh++;
                });
            }, 100);

        },

        getLockedStyle(field_index) {
            return this.values[field_index].locked === true ? 'locked-style' : ''
        },

        onFocus(field_index) {
            if (this.edit === true) {

                lockReportItem(this.report_item_id, {'field_id': this.values[field_index].id}).then(() => {
                })
            }
            //window.console.debug("onFocus")
        },

        onBlur(field_index) {
            if (this.edit === true) {

                this.onEdit(field_index)

                unlockReportItem(this.report_item_id, {'field_id': this.values[field_index].id}).then(() => {
                })
            }
        },

        onKeyUp(field_index) {
            if (this.edit === true) {

                clearTimeout(this.key_timeout);
                let self = this;
                this.key_timeout = setTimeout(function () {
                    holdLockReportItem(self.report_item_id, {'field_id': self.values[field_index].id}).then(() => {
                    })
                }, 1000);
            }
        },

        onEdit(field_index) {
            if (this.edit === true) {

                var data = {}
                data.update = true
                data.attribute_id = this.values[field_index].id

                let value = this.values[field_index].value
                if (this.attribute_group.attribute.type === 'CPE') {
                    value = value.replace("*", "%")
                } else if (this.attribute_group.attribute.type === 'BOOLEAN') {
                    if (value === true) {
                        value = "true"
                    } else {
                        value = "false"
                    }
                }
                data.attribute_value = value

                updateReportItem(this.report_item_id, data).then((update_response) => {
                    getReportItemData(this.report_item_id, update_response.data).then((response) => {
                        this.values[field_index].last_updated = response.data.attribute_last_updated
                        this.values[field_index].user = {name: response.data.attribute_user}
                    })
                })
            }
        },

        report_item_locked(data) {
            if (this.edit === true && this.report_item_id === data.report_item_id) {
                if (data.user_id !== this.$store.getters.getUserId) {
                    for (let i = 0; i < this.values.length; i++) {
                        if (this.values[i].id === data.field_id) {
                            this.values[i].locked = true
                            break
                        }
                    }
                }
            }
        },

        report_item_unlocked(data) {
            if (this.edit === true && this.report_item_id === data.report_item_id) {
                if (data.user_id !== this.$store.getters.getUserId) {
                    for (let i = 0; i < this.values.length; i++) {
                        if (this.values[i].id === data.field_id) {
                            this.values[i].locked = false
                            break
                        }
                    }
                }
            }
        },

        report_item_updated(data_info) {
            if (this.edit === true && this.report_item_id === data_info.report_item_id) {
                if (data_info.user_id !== this.$store.getters.getUserId) {
                    if (data_info.update !== undefined) {
                        getReportItemData(this.report_item_id, data_info).then((response) => {
                            let data = response.data
                            for (let i = 0; i < this.values.length; i++) {
                                if (this.values[i].id === data.attribute_id) {
                                    let value = data.attribute_value
                                    if (this.attribute_group.attribute.type === 'CPE') {
                                        value = value.replace("%", "*")
                                    } else if (this.attribute_group.attribute.type === 'BOOLEAN') {
                                        value = value === "true";
                                    }
                                    this.values[i].value = value
                                    this.values[i].last_updated = data.attribute_last_updated
                                    this.values[i].user = {name: data.attribute_user}
                                    break
                                }
                            }
                        })
                    } else if (data_info.add !== undefined) {
                        if (data_info.attribute_group_item_id === this.attribute_group.id) {
                            getReportItemData(this.report_item_id, data_info).then((response) => {
                                let data = response.data
                                this.values.push({
                                    id: data.attribute_id,
                                    index: this.values.length,
                                    value: data.attribute_value,
                                    binary_mime_type: data.binary_mime_type,
                                    binary_size: data.binary_size,
                                    binary_description: data.binary_description,
                                    last_updated: data.attribute_last_updated,
                                    user: {name: data.attribute_user}
                                })
                                if (this.attribute_group.attribute.type === 'ATTACHMENT') {
                                    this.addFile(this.values[this.values.length-1])
                                }
                            })
                        }
                    } else if (data_info.delete !== undefined) {
                        for (let i = 0; i < this.values.length; i++) {
                            if (this.values[i].id === data_info.attribute_id) {
                                this.values.splice(i, 1)
                                if (this.attribute_group.attribute.type === 'ATTACHMENT') {
                                    this.removeFile(data_info.attribute_id)
                                }
                                break
                            }
                        }
                    }

                }
            }
        }
    },

    mounted() {
        if (this.attribute_group.min_occurrence > 0 && this.values.length === 0) {
            this.add()
        }

        this.$root.$on('report-item-locked', this.report_item_locked)
        this.$root.$on('report-item-unlocked', this.report_item_unlocked)
        this.$root.$on('report-item-updated', this.report_item_updated)
    },

    beforeDestroy() {
        this.$root.$off('report-item-locked', this.report_item_locked)
        this.$root.$off('report-item-unlocked', this.report_item_unlocked)
        this.$root.$off('report-item-updated', this.report_item_updated)
    }
};

export default AttributesMixin