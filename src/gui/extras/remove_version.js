const fs = require('fs')
const path = require('path')

// Path to the package.json file
const packagePath = path.join(__dirname, '..', 'package.json')

// Read the package.json file
const packageData = JSON.parse(fs.readFileSync(packagePath, 'utf8'))

// Delete the version field
delete packageData.version

// Write the updated package.json data back to the file
fs.writeFileSync(
  packagePath,
  JSON.stringify(packageData, null, 2) + '\n',
  'utf8'
)
