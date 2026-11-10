export function frequencyMap(draws, { specialOnly = false } = {}) {
  const freq = Object.fromEntries([...Array(49)].map((_, i) => [i + 1, 0]))
  for (const d of draws) {
    const balls = specialOnly ? [d.special] : d.all
    for (const n of balls) {
      if (n >= 1 && n <= 49) freq[n] += 1
    }
  }
  return freq
}

export function topNumbers(freq, n = 10) {
  return Object.entries(freq)
    .map(([num, count]) => ({ num: parseInt(num, 10), count }))
    .sort((a, b) => b.count - a.count || a.num - b.num)
    .slice(0, n)
}

export function coldNumbers(freq, n = 10) {
  return Object.entries(freq)
    .map(([num, count]) => ({ num: parseInt(num, 10), count }))
    .sort((a, b) => a.count - b.count || a.num - b.num)
    .slice(0, n)
}

export function countMeta(draws, field) {
  const counts = {}
  for (const d of draws) {
    const items = d[field] || []
    for (const x of items) {
      if (!x) continue
      counts[x] = (counts[x] || 0) + 1
    }
  }
  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
}

export function colorFreq(draws) {
  return countMeta(draws, 'colors')
}

export function zodiacFreq(draws) {
  const items = countMeta(draws, 'zodiacs')
  return items.filter((x) => x.name !== '特' && x.name.length <= 2)
}

export function sumStats(draws) {
  const sums = draws.map((d) => d.all.reduce((a, b) => a + b, 0))
  if (!sums.length) return { min: 0, max: 0, avg: 0 }
  const min = Math.min(...sums)
  const max = Math.max(...sums)
  const avg = Math.round((sums.reduce((a, b) => a + b, 0) / sums.length) * 10) / 10
  return { min, max, avg }
}

export function oddEvenRatio(numbers) {
  const odd = numbers.filter((n) => n % 2 === 1).length
  return `${odd}:${numbers.length - odd}`
}

export function filterByYear(draws, year) {
  if (!year) return draws
  return draws.filter((d) => d.year === year)
}

export function availableYears(draws) {
  return [...new Set(draws.map((d) => d.year))].sort((a, b) => b - a)
}
