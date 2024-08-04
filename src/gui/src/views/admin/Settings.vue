<template>
  <v-container fluid class="pa-2">
    <v-row no-gutters>
      <v-col class="pa-2 mt-2">
        <h1>Admin Settings</h1>
      </v-col>
    </v-row>
    <v-row no-gutters>
      <v-col class="pa-1">
        <v-card
          class="admin-settings-card pa-3"
          title="Default TLP Level"
          text="Set the default TLP Level for new Sources, Roles, and Reports."
        >
          <v-spacer></v-spacer>
          <v-card-actions>
            <v-select
              v-model="tlp"
              :items="tlpLevels"
              label="TLP Level"
              variant="outlined"
              menu-icon="mdi-chevron-down"
            />
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <v-col class="pa-1 mx-4">
        <v-expansion-panels class="mt-1 pa-0">
          <v-expansion-panel class="bg-error">
            <v-expansion-panel-title
              class="my-5 admin-settings-expansion-panel-title"
            >
              <strong>
                Everything in this section is dangerous. You can break things.
                Be careful.
              </strong>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-container fluid class="pa-0 pb-4">
                <v-row no-gutters>
                  <v-col cols="12" md="4">
                    <v-card
                      class="admin-settings-card"
                      title="Clear all Worker Queues"
                      text="Delete all messages from all worker queues. This action cannot be undone."
                    >
                      <v-spacer></v-spacer>
                      <v-card-actions>
                        <v-btn
                          block
                          color="error"
                          variant="outlined"
                          text="Delete all Worker Queues"
                          @click="purgeQueues"
                        />
                      </v-card-actions>
                    </v-card>
                  </v-col>

                  <v-col cols="12" md="4">
                    <v-card
                      class="admin-settings-card"
                      title="Delete all Tags"
                      text="Delete all tags from all Stories in the system. Reverting the Action of the NER, Wordlist, and Tagging Bots. This action cannot be undone."
                    >
                      <v-spacer></v-spacer>
                      <v-card-actions>
                        <v-btn
                          block
                          color="error"
                          variant="outlined"
                          text="Delete all Tags"
                          @click="deleteTags"
                        />
                      </v-card-actions>
                    </v-card>
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-card
                      class="admin-settings-card"
                      title="Ungroup all Stories"
                      text="Ungroup all Stories in the system. Reverting the actions of the Story Clustering. This action cannot be undone."
                    >
                      <v-spacer></v-spacer>
                      <v-card-actions>
                        <v-btn
                          block
                          color="error"
                          variant="outlined"
                          text="Ungroup all Stories"
                          @click="ungroupAllStoriesAction"
                        />
                      </v-card-actions>
                    </v-card>
                  </v-col>
                </v-row>
                <v-row no-gutters class="mt-2">
                  <v-col cols="12">
                    <v-card
                      class="admin-settings-card"
                      title="Delete Everything"
                      text="This may potentially fail and completly break the system.
          Tries to delete all Report Items, Products, News Items and Stories."
                    >
                      <v-spacer></v-spacer>
                      <v-card-actions>
                        <v-btn
                          block
                          color="error"
                          variant="outlined"
                          text="Delete Everything"
                          @click="deleteEverything"
                        />
                      </v-card-actions>
                    </v-card>
                  </v-col>
                </v-row>
              </v-container>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { notifyFailure, tlpLevels, notifySuccess } from '@/utils/helpers'
import {
  getAdminSettings,
  updateAdminSettings,
  deleteAllTags,
  ungroupAllStories,
  resetDatabase,
  clearQueues
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
        updateSettings()
      }
    })

    async function purgeQueues() {
      try {
        const result = await clearQueues()
        notifySuccess(result)
      } catch (error) {
        notifyFailure(error)
      }
    }

    async function updateSettings() {
      try {
        const result = await updateAdminSettings({
          default_tlp_level: tlpLevel.value
        })
        notifySuccess(result)
      } catch (error) {
        notifyFailure(error)
      }
    }

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
    return {
      deleteTags,
      ungroupAllStoriesAction,
      deleteEverything,
      purgeQueues,
      tlpLevels,
      tlp
    }
  }
}
</script>

<style lang="scss">
.admin-settings-card {
  border: 2px solid white;
  transition: 180ms;
  box-shadow: 1px 2px 9px 0px rgba(0, 0, 0, 0.15);
  flex-grow: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  margin: 4px;
  padding: 12px;

  & a {
    color: rgb(var(--v-theme-primary));
  }
}
.admin-settings-expansion-panel-title .v-expansion-panel-title__overlay {
  display: none !important;
}
</style>
