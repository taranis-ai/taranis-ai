
var ImportCSVMixin = {

    methods: {

        csvStringToArray (strData, header) {
            //const objPattern = new RegExp(("(\\,|\\r?\\n|\\r|^)(?:\"([^\"]*(?:\"\"[^\"]*)*)\"|([^\\,\\r\\n]*))"),"gi");
            const objPattern = new RegExp(("(\\,|\\r?\\n|\\r|^)(?:\"((?:\\\\.|\"\"|[^\\\\\"])*)\"|([^\\,\"\\r\\n]*))"), "gi");
            let arrMatches = null, arrData = [[]];

            while (arrMatches == objPattern.exec(strData)) {
                if (arrMatches[1].length && arrMatches[1] !== ",") arrData.push([]);
                arrData[arrData.length - 1].push(arrMatches[2] ?
                    arrMatches[2].replace(new RegExp("[\\\\\"](.)", "g"), '$1') :
                    arrMatches[3]);
            }

            if (header) {
                var hData = arrData.shift();
                let hashData = arrData.map(row => {
                    let i = 0;
                    return hData.reduce(
                        (acc, key) => {
                            acc[key] = row[i++];
                            return acc;
                        },
                        {}
                    );
                });
                return hashData;
            } else {
                arrData = arrData.map(row => {
                    let i = 0;
                    return hData.reduce(
                        (acc, key) => {
                            acc[key] = row[i];
                            return acc;
                        },
                        {}
                    );
                });
                return arrData;
            }
        }
    }

};

export default ImportCSVMixin;