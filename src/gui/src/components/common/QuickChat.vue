<template>
    <div class="chatEnv">
        <div class="taranis-chat" v-if="chat">
            <Chat
                    :participants="participants"
                    :myself="myself"
                    :messages="messages"
                    :on-type="onType"
                    :on-message-submit="onMessageSubmit"
                    :chat-title="chatTitle"
                    :placeholder="placeholder"
                    :colors="colors"
                    :border-style="borderStyle"
                    :hide-close-button="hideCloseButton"
                    :close-button-icon-size="closeButtonIconSize"
                    :on-close="onClose"
                    :submit-icon-size="submitIconSize"
                    :load-more-messages="toLoad.length > 0 ? loadMoreMessages : null"
                    :async-mode="asyncMode"
                    :scroll-bottom="scrollBottom"
                    :display-header="displayHeader"/>
        </div>
        <v-btn class="chatButton" icon  @click="onChat">
            <v-icon medium color="white">mdi-chat</v-icon>
        </v-btn>
    </div>

</template>

<script>
    // dokumentacia
    // https://github.com/MatheusrdSantos/vue-quick-chat
    import {Chat} from 'vue-quick-chat';
    import 'vue-quick-chat/dist/vue-quick-chat.css';
    //import {addChat} from "@/api/incidents";

    export default {
        components: {
            Chat
        },
        props: [],
        data() {
            return {
                chat: false,
                visible: false,
                chatTitle: 'Global Chat',
                placeholder: 'Write message',
                participants: [
                ],
                messages: [],
                myself: {
                    name: 'Test User - SK-CERT',
                    id: 3,
                },
                colors: {
                    header: {
                        bg: '#d30303',
                        text: '#fff'
                    },
                    message: {
                        myself: {
                            bg: '#fff',
                            text: '#bdb8b8'
                        },
                        others: {
                            bg: '#fb4141',
                            text: '#fff'
                        },
                        messagesDisplay: {
                            bg: '#f7f3f3'
                        }
                    },
                    submitIcon: '#b91010'
                },
                borderStyle: {
                    topLeft: "10px",
                    topRight: "10px",
                    bottomLeft: "10px",
                    bottomRight: "10px",
                },
                hideCloseButton: false,
                submitIconSize: "30px",
                closeButtonIconSize: "20px",
                asyncMode: false,
                toLoad: [],
                scrollBottom: {
                    messageSent: true,
                    messageReceived: false
                },
                displayHeader: true
            }
        },
        methods: {
            /*onType: function (event) {
                //here you can set any behavior
            },*/
            loadMoreMessages(resolve) {
                setTimeout(() => {
                    resolve(this.toLoad); //We end the loading state and add the messages
                    //Make sure the loaded messages are also added to our local messages copy or they will be lost
                    this.messages.unshift(...this.toLoad);
                    this.toLoad = [];
                }, 1000);
            },
            onMessageSubmit: function (message) {

                this.messages.push(message);
            },
            onClose() {
                this.chat = !this.chat;
            },
            onChat() {
                this.chat = !this.chat;
            }
        }
    }
</script>