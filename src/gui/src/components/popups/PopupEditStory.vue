<template>
  <v-card>
    <v-form ref="form" v-model="valid">
      <v-container>
        <v-row>
          <v-col cols="12">
            <h2 class="popup-title">Edit Story</h2>
          </v-col>
        </v-row>
        <v-row>
          <!----------->
          <!-- Title -->
          <!----------->

          <v-col class="py-2">
            <text-field v-model="newTitle" label="Title" />
          </v-col>
        </v-row>
        <v-row>
          <!------------->
          <!-- Summary -->
          <!------------->

          <v-col cols="12" class="py-0 pt-2">
            <v-textarea
              class="edit-summary"
              v-model="newSummary"
              label="Summary"
              hide-details
              outlined
            ></v-textarea>
          </v-col>
        </v-row>
      </v-container>

      <v-divider></v-divider>

      <v-card-actions class="mt-3">
        <v-spacer></v-spacer>
        <button-outlined
          label="cancel"
          icon="mdi-close"
          color="awake-red-color"
          extraClass="mr-2"
          @click="$emit('close')"
        />

        <button-outlined
          label="apply"
          icon="mdi-check"
          color="primary"
          @click="submit()"
        />
      </v-card-actions>
    </v-form>
  </v-card>
</template>

<script>
import { mapActions } from 'vuex'
import textField from '@/components/_subcomponents/textField'
import buttonOutlined from '@/components/_subcomponents/buttonOutlined'

export default {
  name: 'PopupEditStory',
  components: {
    textField,
    buttonOutlined
  },
  props: {
    dialog: Boolean,
    story: {}
  },
  data: () => ({
    valid: true,
    newTitle: '',
    newSummary: ''
  }),
  methods: {
    ...mapActions('dashboard', ['updateStory']),

    submit () {
      const updatedStory = this.story
      updatedStory.title = this.newTitle
      updatedStory.summary = this.newSummary
      updatedStory.sharingState = 'pending'
      this.updateStory(updatedStory)

      // Close Popup
      this.$emit('close')
    }
  },
  mounted () {
    this.newTitle = this.story.title
    this.newSummary = this.story.summary
  }
}
</script>
