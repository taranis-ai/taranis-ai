<template>
    <v-data-table
            :headers="headers"
            :items="recipients"
            sort-by="value"
            class="elevation-1"
    >
        <template v-slot:top>
            <v-toolbar flat color="white">
                <v-toolbar-title>{{$t('notification_template.recipients')}}</v-toolbar-title>
                <v-divider
                        class="mx-4"
                        inset
                        vertical
                ></v-divider>
                <v-spacer></v-spacer>
                <v-dialog v-model="dialog" max-width="500px">
                    <template v-slot:activator="{ on }">
                        <v-btn color="primary" dark class="mb-2" v-on="on">
                            <v-icon left>mdi-plus</v-icon>
                            <span>{{$t('notification_template.new_recipient')}}</span>
                        </v-btn>
                    </template>
                    <v-card>
                        <v-card-title>
                            <span class="headline">{{ formTitle }}</span>
                        </v-card-title>

                        <v-card-text>

                            <v-text-field v-model="edited_recipient.email"
                                          :label="$t('notification_template.email')"
                                          :spellcheck="$store.state.settings.spellcheck"></v-text-field>

                            <v-text-field v-model="edited_recipient.name"
                                          :label="$t('notification_template.name')"
                                          :spellcheck="$store.state.settings.spellcheck"></v-text-field>

                        </v-card-text>

                        <v-card-actions>
                            <v-spacer></v-spacer>
                            <v-btn color="primary" dark @click="save">{{$t('notification_template.save')}}</v-btn>
                            <v-btn color="primary" text @click="close">{{$t('notification_template.cancel')}}</v-btn>
                        </v-card-actions>
                    </v-card>
                </v-dialog>
            </v-toolbar>
        </template>
        <template v-slot:item.action="{ item }">
            <v-icon
                    small
                    class="mr-2"
                    @click="editItem(item)"
            >
                edit
            </v-icon>
            <v-icon
                    small
                    @click="deleteItem(item)"
            >
                delete
            </v-icon>
        </template>
    </v-data-table>
</template>

<script>
export default {
  name: 'RecipientTable',
  props: {
    recipients: Array
  },
  data: () => ({
    headers: [
      { text: 'Email', value: 'email', align: 'left', sortable: true },
      { text: 'Name', value: 'name', sortable: false },
      { text: 'Actions', value: 'action', align: 'right', sortable: false }
    ],
    dialog: false,
    selected_recipient: null,
    edited_index: -1,
    edited_recipient: {
      email: '',
      name: ''
    },
    default_recipient: {
      email: '',
      name: ''
    }
  }),
  computed: {
    formTitle () {
      return this.edited_index === -1 ? 'Add Recipient' : 'Edit Recipient'
    }
  },
  watch: {
    dialog (val) {
      val || this.close()
    }
  },
  methods: {
    close () {
      this.dialog = false
      setTimeout(() => {
        this.edited_recipient = Object.assign({}, this.default_recipient)
        this.edited_index = -1
      }, 300)
    },

    save () {
      if (this.edited_index > -1) {
        Object.assign(this.recipients[this.edited_index], this.edited_recipient)
      } else {
        this.recipients.push(this.edited_recipient)
      }
      this.selected_recipient = null
      this.close()
    },

    editItem (item) {
      this.edited_index = this.recipients.indexOf(item)
      this.edited_recipient = Object.assign({}, item)
      this.dialog = true
    },

    moveItemUp (item) {
      const index = this.recipients.indexOf(item)
      if (index > 0) {
        this.recipients.splice(index - 1, 0, this.recipients.splice(index, 1)[0])
      }
    },

    moveItemDown (item) {
      const index = this.recipients.indexOf(item)
      if (index < this.recipients.length - 1) {
        this.recipients.splice(index + 1, 0, this.recipients.splice(index, 1)[0])
      }
    },

    deleteItem (item) {
      const index = this.recipients.indexOf(item)
      this.recipients.splice(index, 1)
    }
  }
}
</script>
