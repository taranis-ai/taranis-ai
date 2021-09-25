import axios from 'axios'

const ApiService = {

    init(baseURL) {
        axios.defaults.baseURL = baseURL;
        ApiService.setHeader();
    },

    setHeader() {
        if (localStorage.ACCESS_TOKEN) {
            axios.defaults.headers.common["Authorization"] = `Bearer ${localStorage.ACCESS_TOKEN}`
        } else {
            axios.defaults.headers.common = {}
        }
    },

    get(resource) {
        return axios.get(resource)
    },

    post(resource, data) {
        return axios.post(resource, data)
    },

    put(resource, data) {
        return axios.put(resource, data)
    },

    delete(resource) {
        return axios.delete(resource)
    }
};

export default ApiService