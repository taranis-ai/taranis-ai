import { getDashboardData } from '@/api/dashboard'
import { getField, updateField } from 'vuex-map-fields'
import { xor } from 'lodash'

import { faker } from '@faker-js/faker'
import moment from 'moment'

const state = {
  dummyTopics: [],
  dummySharingSets: [],
  dummyNewsItems: []
}

const actions = {

  init(context) {
    context.commit('INIT_DUMMYDATA')
  }

}

const mutations = {

  updateField,

  INIT_DUMMYDATA(state) {
    const numberOfDummyTopics = 20
    const numberOfDummySharingSets = 2
    const numberOfDummyNewsItem = 100 // 1000
    const numberOfDummyUsers = 20
    state.dummyUsers = generateUsers(numberOfDummyUsers)
    state.dummyTopics = generateTopics(numberOfDummyTopics, false, 0)
    state.dummyNewsItems = generateNewsItems(numberOfDummyNewsItem, numberOfDummyTopics)

    // Assign Items to topics
    state.dummyTopics.forEach(topic => {
      const items = faker.random.arrayElements(
        state.dummyNewsItems,
        topic.items.total
      )
      items.forEach(item => {
        item.topics.push(topic.id)
        topic.items.ids.push(item.id)
      })
    })

    state.dummySharingSets = generateTopics(numberOfDummySharingSets, true, numberOfDummyTopics)

    // Assign Items to Sharingsets
    state.dummySharingSets.forEach(sharingSet => {
      const user = faker.random.arrayElement(state.dummyUsers)
      sharingSet.relevanceScore = 0
      sharingSet.sharedBy = user.username
      sharingSet.sharedWith = faker.random.arrayElements(state.dummyUsers, Math.floor(Math.random() * (5 - 2 + 1)) + 2)
      sharingSet.originator = user.id
      sharingSet.sharingState = 'shared'
      sharingSet.sharingDirection = 'incoming'
      const items = faker.random.arrayElements(
        state.dummyNewsItems,
        sharingSet.items.total
      )
      items.forEach(item => {
        item.topics.forEach(topicId => {
          const parentTopic = state.dummyTopics.find(topic => topic.id === topicId)
          if (parentTopic) {
            //  Set has shared
            parentTopic.hasSharedItems = true
            //  append sharing set to topic
            if (!parentTopic.sharingSets.includes(sharingSet.id)) {
              parentTopic.sharingSets.push(sharingSet.id)
            }
          }
        })
        // item.topics.push(sharingSet.id)
        item.shared = true
        item.sharingSets.push(sharingSet.id)
        sharingSet.items.ids.push(item.id)
      })
    })
  }
}

const getters = {

  getField,

  getDummyUsers(state) {
    return state.dummyUsers
  },
  getDummyTopics(state) {
    return state.dummyTopics
  },
  getDummySharingSets(state) {
    return state.dummySharingSets
  },
  getDummyNewsItems(state) {
    return state.dummyNewsItems
  }

}

export const dummyData = {
  namespaced: true,
  state,
  actions,
  mutations,
  getters
}

// -------------------------------------------------------

let dummyTags = [
  { label: 'State', color: 1 },
  { label: 'Cyberwar', color: 2 },
  { label: 'Threat', color: 3 },
  { label: 'DDoS', color: 4 },
  { label: 'Vulnerability', color: 5 },
  { label: 'Java', color: 6 },
  { label: 'CVE', color: 7 },
  { label: 'OT/CPS', color: 8 },
  { label: 'Python', color: 9 },
  { label: 'Privacy', color: 10 },
  { label: 'Social', color: 11 },
  { label: 'APT', color: 12 },
  { label: 'MitM', color: 13 }
]

let dummySourceTypes = [
  'RSS',
  'MISP',
  'Web',
  'Twitter',
  'Email',
  'Slack',
  'Atom'
]

function generateUsers(numberOfDummyUsers) {
  const dummyData = []

  for (let i = 0; i < (numberOfDummyUsers + 2); i++) {
    const fname = faker.name.firstName()
    const lname = faker.name.lastName()
    const entry = {
      id: i,
      firstName: fname,
      lastName: lname,
      username: faker.internet.userName(fname, lname)
    }

    dummyData.push(entry)
  }

  return dummyData
}

function generateTopics(numberOfDummyTopics, sharingSet, offset) {
  const dummyData = []

  for (let i = 1; i < numberOfDummyTopics; i++) {
    const entry = {
      id: i + offset,
      relevanceScore: parseInt(faker.commerce.price(0, 100, 0)),
      title: Math.random() < 0.5 ? `${faker.hacker.adjective()} ${faker.hacker.noun()} ${faker.hacker.abbreviation()}` : `${faker.hacker.adjective()} ${faker.hacker.noun()} ${faker.hacker.noun()}`,
      tags: faker.random.arrayElements(
        dummyTags,
        Math.floor(Math.random() * (5 - 2 + 1)) + 2
      ),
      ai: Math.random() < 0.25,
      originator: Math.floor(Math.random() * (20 + 1)), // random user ID
      hot: Math.random() < 0.15,
      pinned: Math.random() < 0.05,
      lastActivity: new Date(String(faker.date.recent(10))),
      summary: sharingSet ? faker.lorem.paragraph(10) : faker.lorem.paragraph(20),
      items: {
        ids: [],
        total: sharingSet ? parseInt(faker.commerce.price(16, 26, 0)) : parseInt(faker.commerce.price(24, 64, 0)),
        new: parseInt(faker.commerce.price(0, 6, 0))
      },
      comments: {
        total: parseInt(faker.commerce.price(20, 40, 0)),
        new: parseInt(faker.commerce.price(0, 40, 0))
      },
      votes: {
        up: parseInt(faker.commerce.price(0, 50, 0)),
        down: parseInt(faker.commerce.price(0, 50, 0))
      },
      hasSharedItems: false,
      isSharingSet: sharingSet,
      sharingState: '',
      sharingDirection: '',
      sharedBy: '',
      sharedWith: [],
      sharingSets: [],
      relatedTopics: [],
      keywords: faker.random
        .words(Math.random() * (16 - 6 + 1) + 6)
        .split(' '),
      selected: false
    }

    if (!sharingSet) {
      // Add related topics
      for (let y = 1; y < Math.floor(Math.random() * (3)); y++) {
        const newTopicLink = Math.floor(Math.random() * (numberOfDummyTopics - 2))
        if (!entry.relatedTopics.includes(newTopicLink)) {
          entry.relatedTopics.push(newTopicLink)
        }
      }
    }

    dummyData.push(entry)
  }

  return dummyData
}

function generateNewsItems(numberOfDummyNewsItem, numberOfDummyTopics) {
  let dummyData = []

  for (let i = 1; i < numberOfDummyNewsItem; i++) {
    let sourceDomain = faker.internet.domainName()
    let entry = {
      id: i,
      relevanceScore: faker.commerce.price(0, 100, 0),
      title: faker.hacker.phrase(),
      summary: faker.lorem.paragraph(5),
      tags: faker.random.arrayElements(
        dummyTags,
        Math.floor(Math.random() * (5 - 2 + 1)) + 2
      ),
      published: new Date(String(faker.date.recent(80))),
      collected: new Date(String(faker.date.recent(20))),
      source: {
        domain: sourceDomain,
        url: `${faker.internet.protocol()}://${sourceDomain}/rss/${moment(
          new Date(String(faker.date.recent(50)))
        ).format('YYYY/MM/DD')}/${faker.internet.password(20)}`,
        type: dummySourceTypes[Math.floor(Math.random() * 7)]
      },
      addedBy: Math.floor(Math.random() * (20 + 1)), // random user ID
      topics: [],
      votes: {
        up: parseInt(faker.commerce.price(0, 50, 0)),
        down: parseInt(faker.commerce.price(0, 50, 0))
      },
      important: Math.random() < 0.2,
      read: Math.random() < 0.5,
      decorateSource: Math.random() < 0.2,
      recommended: Math.random() < 0.2,
      inAnalysis: Math.random() < 0.2,
      shared: false,
      sharingSets: [],
      restricted: Math.random() < 0.2
    }

    dummyData.push(entry)
  }

  return dummyData
}
