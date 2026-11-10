import Papa from 'papaparse'

const REQUIRED_FIELDS = ['issue', 'year', 'seq', 'n1', 'n2', 'n3', 'n4', 'n5', 'n6', 'special']

function integer(row, field) {
  const value = String(row[field] ?? '').trim()
  const number = Number(value)
  if (!/^\d+$/.test(value) || !Number.isSafeInteger(number)) {
    throw new Error(`字段 ${field} 必须为非空整数`)
  }
  return number
}

export function parseDrawRow(row) {
  const nums = [1, 2, 3, 4, 5, 6].map((i) => integer(row, `n${i}`))
  const special = integer(row, 'special')
  const all = [...nums, special]
  const issue = integer(row, 'issue')
  const year = integer(row, 'year')
  const seq = integer(row, 'seq')
  if (year < 1 || seq < 1 || seq > 999 || issue !== year * 1000 + seq) {
    throw new Error('期号与年份/序号不一致')
  }
  if (all.some((n) => n < 1 || n > 49) || new Set(all).size !== 7) {
    throw new Error('每期必须包含 7 个互不重复的 1..49 球号')
  }
  const split = (s) => (s ? s.split(',').map((item) => item.trim()) : [])
  return {
    issue,
    year,
    seq,
    lottery: row.lottery || '',
    nums,
    special,
    all,
    colors: split(row.colors),
    zodiacs: split(row.zodiacs),
    wuxings: split(row.wuxings),
    openTime: row.open_time || row.openTime || '',
    verifyStatus: row.verify_status || '',
    verifySources: row.verify_sources || '',
  }
}

export function parseLotteryCsv(text) {
  const parsed = Papa.parse(text, { header: true, skipEmptyLines: 'greedy' })
  if (parsed.errors.length) {
    throw new Error(`CSV 格式错误：${parsed.errors[0].message}`)
  }
  const missing = REQUIRED_FIELDS.filter((field) => !parsed.meta.fields?.includes(field))
  if (missing.length) throw new Error(`CSV 缺少字段：${missing.join(', ')}`)
  const issues = new Set()
  const rows = parsed.data.map((row, index) => {
    try {
      const draw = parseDrawRow(row)
      if (issues.has(draw.issue)) throw new Error(`重复期号 ${draw.issue}`)
      issues.add(draw.issue)
      return draw
    } catch (e) {
      throw new Error(`CSV 第 ${index + 2} 条记录：${e.message}`)
    }
  })
  rows.sort((a, b) => b.issue - a.issue)
  return rows
}

export async function loadLotteryCsv(filename) {
  const url = `${import.meta.env?.BASE_URL || '/'}data/${filename}`
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`无法加载 ${url}（请先运行 scripts/sync_viz_data.py）`)
  }
  return parseLotteryCsv(await res.text())
}
