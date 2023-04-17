export function filterSearch(fields, searchString) {
  let match = false

  const regexStr = searchString
    .trim()
    .match(/\\?.|^$/g)
    .reduce(
      (previousValue, currentValue) => {
        if (currentValue === '"') {
          previousValue.quote ^= 1
        } else if (!previousValue.quote && currentValue === ' ') {
          previousValue.a.push('')
        } else {
          previousValue.a[previousValue.a.length - 1] += currentValue.replace(
            /\\(.)/,
            '$1'
          )
        }
        return previousValue
      },
      { a: [''] }
    )
    .a.join('|')

  const searchRegEx = new RegExp(regexStr, 'gi')

  for (let i = 0; i < fields.length; i++) {
    if ([...fields[i].matchAll(searchRegEx)].length > 0) {
      match = true
      break
    }
  }

  return match
}

export function filterDateRange(publishedDate, selectedType, dateRange) {
  let range = []
  const today = new Date()
  switch (selectedType) {
    case 'today':
      range = [today.setHours(0, 0, 0, 0), today.setHours(23, 59, 59, 999)]
      break
    case 'week': {
      const currentDate = new Date()
      const timediff = today.getDate() - 7
      const oneWeekAgo = currentDate.setDate(timediff)
      range = [new Date(oneWeekAgo), new Date(today.setHours(23, 59, 59, 999))]
      break
    }
    case 'range':
      range = [
        new Date(dateRange[0]).setHours(0, 0, 0, 0),
        new Date(dateRange[1]).setHours(23, 59, 59, 999)
      ]
      break
  }

  return publishedDate >= range[0] && publishedDate <= range[1]
}

export function filterTags(itemTags, selectedTags, andOperator) {
  if (!selectedTags.length) return true

  const selectedTagExists = (selectedTag) =>
    itemTags.some((itemTag) => itemTag.label === selectedTag)

  return andOperator
    ? selectedTags.every(selectedTagExists)
    : selectedTags.some(selectedTagExists)
}
