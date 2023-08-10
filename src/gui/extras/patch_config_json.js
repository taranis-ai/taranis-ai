const fs = require('fs');
const path = require('path');

const configPath = path.join(__dirname, '../dist/config.json');
const configJson = require(configPath);
configJson.BUILD_DATE = new Date().toISOString();
fs.writeFileSync(configPath, JSON.stringify(configJson, null, 2));
