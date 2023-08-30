const { execSync } = require('child_process')
const fs = require('fs')
const path = require('path')

// Fetch the latest tag that matches the regex
const getLatestTag = () => {
  try {
    return execSync('git tag --list v[0-9].[0-9]*.[0-9]* | sort -V | tail -n 1')
      .toString()
      .trim()
  } catch (err) {
    return null
  }
}

// Check if current commit is the same as the latest tag
const isHeadAtLatestTag = (tag) => {
  try {
    const tagCommit = execSync(`git rev-list -n 1 ${tag}`).toString().trim()
    const headCommit = execSync('git rev-parse HEAD').toString().trim()
    return tagCommit === headCommit
  } catch (err) {
    return false
  }
}

const main = () => {
  let latestTag = getLatestTag()

  if (!latestTag) {
    console.error('Failed to get the latest tag. Using Fallback version 0.0.0')
    latestTag = 'v0.0.0'
  }

  let version = latestTag.slice(1) // remove the "v" prefix

  if (!isHeadAtLatestTag(latestTag)) {
    version += '-dev'
  }

  const packagePath = path.join(__dirname, '..', 'package.json')
  const packageData = require(packagePath)
  packageData.version = version

  fs.writeFileSync(packagePath, JSON.stringify(packageData, null, 2))
  console.log(`Updated version to ${version}`)
}

main()
