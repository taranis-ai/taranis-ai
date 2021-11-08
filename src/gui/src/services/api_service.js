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
    },

    upload(resource, form_data) {
        return axios.post(resource, form_data, {
            headers: {
                "Content-Type": "multipart/form-data"
            }
        });
    },

    download(resource, data, file_name) {
        axios({
            url: resource,
            method: 'POST',
            responseType: 'blob',
            data: data
        }).then((response) => {
            let fileURL = window.URL.createObjectURL(new Blob([response.data]))
            let fileLink = document.createElement('a')
            fileLink.href = fileURL
            fileLink.setAttribute('download', file_name)
            document.body.appendChild(fileLink)
            fileLink.click()
            document.body.removeChild(fileLink)
        });
    },
};

export default ApiService