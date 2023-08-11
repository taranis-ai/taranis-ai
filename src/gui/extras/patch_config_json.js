const fs = require('fs')
const path = require('path')

const configPath = path.join(__dirname, '../dist/config.json')
const configJson = require(configPath)
configJson.BUILD_DATE = new Date().toISOString()

const gitInfo = process.env.GIT_INFO
if (gitInfo && gitInfo.trim() !== '') {
  configJson.GIT_INFO = JSON.parse(gitInfo)
}

fs.writeFileSync(configPath, JSON.stringify(configJson, null, 2))
