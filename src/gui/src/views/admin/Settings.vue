<template>
  <v-container fluid>
    <h3 class="text-h3 my-5">Admin Settings</h3>

    <v-row>
      <v-col cols="12">
        <v-card
          title="Default TLP Level"
          text="Set the default TLP Level for new Sources, Roles, and Reports."
        >
          <v-card-actions>
            <v-select
              v-model="tlp"
              :items="tlpLevels"
              label="TLP Level"
              outlined
            />
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-expansion-panels class="mt-5">
      <v-expansion-panel>
        <v-expansion-panel-title class="warning my-5">
          Everything in this section is dangerous. You can break things. Be
          careful.
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-row>
            <v-col cols="6">
              <v-card
                title="Delete all Tags"
                text="Delete all tags from all Stories in the system. Reverting the Action of the NER, Wordlist, and Tagging Bots. This action cannot be undone."
              >
                <v-card-actions>
                  <v-btn
                    variant="elevated"
                    block
                    color="red"
                    text="Delete all Tags"
                    @click="deleteTags"
                  />
                </v-card-actions>
              </v-card>
            </v-col>
            <v-col cols="6">
              <v-card
                title="Ungroup all Stories"
                text="Ungroup all Stories in the system. Reverting the actions of the Story Clustering. This action cannot be undone."
              >
                <v-card-actions>
                  <v-btn
                    variant="elevated"
                    block
                    color="red"
                    text="Ungroup all Stories"
                    @click="ungroupAllStoriesAction"
                  />
                </v-card-actions>
              </v-card>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12">
              <v-card
                title="Delete Everything"
                text="This may potentially fail and completly break the system.
          Tries to delete all Report Items, Products, News Items and Stories."
              >
                <v-card-actions>
                  <v-btn
                    variant="elevated"
                    block
                    color="red"
                    text="Delete Everything"
                    @click="deleteEverything"
                  />
                </v-card-actions>
              </v-card>
            </v-col>
          </v-row>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-container>
</template>

<script>
import { notifyFailure, tlpLevels, notifySuccess } from '@/utils/helpers'
import {
  getAdminSettings,
  updateAdminSettings,
  deleteAllTags,
  ungroupAllStories,
  resetDatabase
} from '@/api/admin'
import { computed, ref } from 'vue'
export default {
  name: 'AdminSettings',
  setup() {
    const tlpLevel = ref('')

    getSettings()

    const tlp = computed({
      get: () => tlpLevel.value,
      set: (value) => {
        tlpLevel.value = value
        updateAdminSettings({ default_tlp_level: value })
      }
    })

    async function getSettings() {
      try {
        const result = await getAdminSettings()
        tlpLevel.value = result.default_tlp_level
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function deleteTags() {
      try {
        const result = await deleteAllTags()
        notifySuccess(result)
      } catch (error) {
        notifyFailure(error)
      }
    }
    async function ungroupAllStoriesAction() {
      try {
        const result = await ungroupAllStories()
        notifySuccess(result)
      } catch (error) {
        notifyFailure(error)
      }
    }
    async function deleteEverything() {
      try {
        const result = await resetDatabase()
        notifySuccess(result)
      } catch (error) {
        notifyFailure(error)
      }
    }
    return { deleteTags, ungroupAllStoriesAction, deleteEverything, tlpLevels, tlp }
  }
}
</script>

<style scoped>
.warning {
  background-color: #ffff00;
}
</style>
